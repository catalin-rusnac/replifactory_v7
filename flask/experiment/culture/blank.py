import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler

import numpy as np

from replifactory.culture.culture_functions import inoculate
from replifactory.culture.plotting import plot_culture
from replifactory.device.dilution import log_dilution
from replifactory.util.growth_rate import calculate_last_growth_rate
from replifactory.util.loading import load_config, save_object
from replifactory.util.other import read_csv_tail, write_variable

log_maxBytes = 5 * 1024 * 1024


class CultureLogger(logging.Logger):
    """
    A logger that writes to a file in the culture directory.
    """

    def __init__(self, culture):
        super().__init__(name="culturelog")
        self.culture = culture
        self.log_filepath = None
        self.info("Started Logger")

    def directory_init(self):
        if self.log_filepath is not None:
            return
        if self.culture.directory is None:
            return
        if not os.path.exists(self.culture.directory):
            os.mkdir(self.culture.directory)
        log_filename = "culture.log"
        self.log_filepath = os.path.join(self.culture.directory, log_filename)
        formatter = logging.Formatter(
            "%(asctime)s %(created)f %(levelname)s %(module)s - %(funcName)s: %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        handler = RotatingFileHandler(
            self.log_filepath,
            mode="a",
            maxBytes=log_maxBytes,
            backupCount=2,
            encoding=None,
            delay=0,
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        self.addHandler(handler)

    def info(self, msg, *args, **kwargs):
        self.directory_init()
        super().info(msg, *args, **kwargs)


class BlankCulture:
    active_pumps = (1, 4)

    def __init__(
        self,
        directory: str = None,
        vial_number: int = None,
        name: str = "Blank",
        description: str = "control vial, not inoculated",
    ):
        self.vial_number = vial_number
        self.directory = None
        if directory is not None:
            self.directory = os.path.realpath(directory)
            if not self.directory[:-1].endswith("vial_"):
                self.directory = os.path.join(self.directory, "vial_%d" % vial_number)
        self.logger = CultureLogger(culture=self)
        self.name = name
        self.description = description
        self.file_lock = threading.Lock()
        self._device = None
        self.dead_volume = 15  # volume below vacuum needle
        self.od_blank = 0
        self._od = None
        self._od_raw = None

        self._class = self.__class__
        self._mu = None
        self._mu_error = None
        self._t_doubling = None
        self._t_doubling_error = None
        self._medium2_concentration = 0
        self._medium3_concentration = 0
        self._log2_dilution_coefficient = 0
        self._inoculation_time = None
        self._samples_collected = {}
        self._is_active = False
        self._last_dilution_start_time = None

        self._mu_max_measured = 0
        self._t_doubling_min_measured = np.inf
        self._time_last_dilution = {1: None, 2: None, 3: None, 4: None}

    def description_text(self):
        t = """
BLANK culture, measures OD every minute. Pumps deactivated.
        """
        return t

    def update(self):
        pass

    @property
    def parameters(self):
        return sorted([k for k in self.__dict__.keys() if not k.startswith("_")])

    @property
    def od(self):
        return np.float32(self._od)

    @od.setter
    def od(self, value):
        write_variable(culture=self, variable_name="od_plus_blank", value=value)
        self._od_raw = value
        self._od = np.float32(value - self.od_blank)
        write_variable(culture=self, variable_name="od", value=self._od)
        self.save()

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, dev):
        if dev is not None:
            if self.directory is not None:
                assert (
                    os.path.join(dev.directory, "vial_%d" % self.vial_number)
                    == self.directory
                )
        self._device = dev
        self.save()

    def load_df(self, parameter, reindex, lines):
        df = read_csv_tail(
            os.path.join(self.directory, parameter + ".csv"), lines=lines
        )
        if reindex:
            df.index = [time.ctime(i) for i in df.index]
        return df

    def get_df_dilutions(self, reindex=False, lines=1000):
        df = read_csv_tail(os.path.join(self.directory, "dilutions.csv"), lines=lines)
        if reindex:
            df.index = [time.ctime(i) for i in df.index]
        return df

    def get_df_od(self, reindex=False, lines=1440):
        df = read_csv_tail(os.path.join(self.directory, "od.csv"), lines=lines)  # 24h
        if reindex:
            df.index = [time.ctime(i) for i in df.index]
        return df

    def get_df_generations(self, reindex=False, lines=1000):
        df = read_csv_tail(
            os.path.join(self.directory, "log2_dilution_coefficient.csv"), lines=lines
        )
        if reindex:
            df.index = [time.ctime(i) for i in df.index]
        return df

    def save(self):
        """
        saves config to vial_directory/culture_config.yaml
        """
        self.file_lock.acquire()  # maybe not necessary?
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)
        config_path = os.path.join(self.directory, "culture_config.yaml")

        save_object(self, filepath=config_path)
        self.file_lock.release()
        if self.logger:
            self.logger.info("Saved config")

    def write_blank_od(self):
        od_plus_blank_filepath = os.path.join(self.directory, "od_plus_blank.csv")
        df = read_csv_tail(filepath=od_plus_blank_filepath, lines=5)
        self.od_blank = df.values.ravel().mean()
        self.save()
        self.logger.info("Blank OD: %.3f" % self.od_blank)

    # def write_log(self, msg=""):
    #     filepath = os.path.join(self.directory, "log.txt")
    #     if not os.path.exists(filepath):
    #         with open(filepath, "w+") as f:
    #             data_string = "%s: %s" % (time.ctime(), "starting log")
    #             f.write(data_string)
    #     with open(filepath, "a") as f:
    #         data_string = "%s, %s\n" % (time.ctime(), msg)
    #         f.write(data_string)

    def load(self):
        config_path = os.path.join(self.directory, "culture_config.yaml")
        self.file_lock.acquire()
        try:
            load_config(self, filepath=config_path)
        finally:
            self.file_lock.release()

    def plot(self, last_hours=24, plot_growth_rate=False):
        fig = plot_culture(
            culture=self, last_hours=last_hours, plot_growth_rate=plot_growth_rate
        )
        return fig

    def is_active(self):
        # if type(self) is BlankCulture:
        #     return False
        # else:
        return self._is_active

    # def show_parameters(self, increase_verbosity=False):
    #     if increase_verbosity:
    #         keys = [k for k in self.__dict__.keys() if not k.startswith("_")]
    #         keys = [k for k in keys if k not in ["directory", "file_lock"]]
    #         for k in sorted(keys):
    #             print("%s:" % k, self.__dict__[k])
    #     else:
    #         print("Vial %d: %d culture" % (self.vial_number, self.__class__.__name__))

    @property
    def experiment_start_time(self):
        try:
            filepath = os.path.join(self.directory, "od.csv")
            with open(filepath) as f:
                time_first_od = np.float32(f.readlines(512)[1].split(",")[0])
            return np.float32(time_first_od)
        except Exception:
            try:
                return self.device.setup_time
            except Exception:
                return None

    @property
    def log2_dilution_coefficient(self):
        return np.float32(self._log2_dilution_coefficient)

    @log2_dilution_coefficient.setter
    def log2_dilution_coefficient(self, value):
        self._log2_dilution_coefficient = value
        write_variable(
            culture=self, variable_name="log2_dilution_coefficient", value=value
        )
        self.save()

    @property
    def mu(self):
        """
        growth rate [1/h]
        :return:
        """
        return np.float32(self._mu)

    @mu.setter
    def mu(self, value):
        mu, error = value
        write_variable(culture=self, variable_name="mu", value=mu)
        write_variable(culture=self, variable_name="mu_error", value=error)
        self._mu = mu
        self._mu_error = error
        if mu != 0:
            t_doubling = np.log(2) / mu
            t_doubling_error = t_doubling * error / mu
            self.t_doubling = (t_doubling, t_doubling_error)

            if mu > self._mu_max_measured and error / mu < 0.05:
                self._mu_max_measured = mu
                self._t_doubling_min_measured = t_doubling
        self.save()

    @property
    def t_doubling(self):
        return np.float32(self._t_doubling)

    @t_doubling.setter
    def t_doubling(self, value):
        t_doubling, t_doubling_error = value
        write_variable(culture=self, variable_name="t_doubling", value=t_doubling)
        write_variable(
            culture=self, variable_name="t_doubling_error", value=t_doubling_error
        )
        self._t_doubling = t_doubling
        self._t_doubling_error = t_doubling_error
        self.save()

    def update_growth_rate(self):
        """
        reads last od values and calculates growth rate
        :return:
        """
        od_filepath = os.path.join(self.directory, "od.csv")
        df = read_csv_tail(od_filepath, lines=300)
        df = df[df.index >= df.index[-1] - 60 * 60 * 5]  # cut last 5 hours
        if np.isfinite(self.time_last_dilution):
            df = df[df.index > np.float32(self.time_last_dilution)]
        t = df.index.values
        od = df.values.ravel() - self.od_blank
        od[od <= 0] = 1e-6
        timepoint, mu, error = calculate_last_growth_rate(t, od)
        if np.isfinite(mu):
            self.mu = (mu, error)

    def flush_culture(self):
        pass
        # def queued_function():
        #     if self.device.is_lagoon_device():
        #         flush_volumes = {1: 0, 2: 0, 3: 0}  # pump: ml
        #         tstart = self.experiment_start_time
        #         for pump_number in self.active_pumps:
        #             tdil = np.float32(self.device._time_last_dilution[pump_number])
        #             last_pump_time = np.nanmax([tdil, tstart])
        #             if (time.time() - last_pump_time) > self.device.drying_prevention_pump_period_hrs * 3600:
        #                 flush_volumes[pump_number] = self.device.drying_prevention_pump_volume
        #         if flush_volumes[1] > 0 or flush_volumes[2] or flush_volumes[3] > 0:
        #             self.dilute(pump1_volume=flush_volumes[1], pump2_volume=flush_volumes[2],
        #                      pump3_volume=flush_volumes[3], extra_vacuum=3)
        #
        # self.device.dilution_worker.queue.put(queued_function)

    @property
    def time_last_dilution(self):
        pump_dilution_times = np.array(list(self._time_last_dilution.values())).astype(
            float
        )
        most_recent_dilution_time = np.nanmax(pump_dilution_times)
        if np.isnan(most_recent_dilution_time):
            return np.nan
        else:
            return int(most_recent_dilution_time)

    @property
    def medium2_concentration(self):
        return np.float32(self._medium2_concentration)

    @medium2_concentration.setter
    def medium2_concentration(self, value):
        self._medium2_concentration = value
        write_variable(culture=self, variable_name="medium2_concentration", value=value)
        self.save()

    @property
    def medium3_concentration(self):
        return np.float32(self._medium3_concentration)

    @medium3_concentration.setter
    def medium3_concentration(self, value):
        self._medium3_concentration = value
        write_variable(culture=self, variable_name="medium3_concentration", value=value)
        self.save()

    @property
    def minutes_since_last_dilution(self):
        if not np.isfinite(self.time_last_dilution):
            seconds_since_last_dilution = time.time() - self._inoculation_time
        else:
            seconds_since_last_dilution = time.time() - self.time_last_dilution
        return np.float32(seconds_since_last_dilution / 60)

    # def handle_value_change(self, change):
    #     parameter_name = change.owner.description
    #     self.__dict__[parameter_name] = change.new
    #     self.save()

    def check(self):
        assert self.device.is_connected()
        assert self.vial_number in [1, 2, 3, 4, 5, 6, 7]
        assert os.path.exists(self.directory)
        assert 0 < self.dead_volume <= 35
        assert callable(self.device.od_sensors[self.vial_number].calibration_function)
        assert callable(self.device.pump1.calibration_function)
        assert callable(self.device.pump4.calibration_function)
        assert -0.3 < self.od_blank < 0.3
        self.device.stirrers.check_calibration(self.vial_number)

    def dilute_adjust_drug1(
        self,
        dilution_factor=None,
        stress_increase_factor=None,
        target_concentration=None,
    ):
        culture = self
        if dilution_factor is None:
            dilution_factor = (
                culture.dead_volume + culture.default_dilution_volume
            ) / culture.dead_volume
        total_volume = culture.dead_volume + culture.default_dilution_volume
        if target_concentration is None:
            if stress_increase_factor is None:
                stress_increase_factor = (dilution_factor + 1) / 2
            medium2_target_concentration = (
                culture.medium2_concentration * stress_increase_factor
            )
            if culture.medium2_concentration == 0:
                medium2_target_concentration = (
                    culture.device.pump2.stock_concentration / 50
                )
        else:
            medium2_target_concentration = target_concentration

        drug1_total_amount = total_volume * medium2_target_concentration
        drug1_current_amount = culture.dead_volume * culture.medium2_concentration
        drug1_pumped_amount = drug1_total_amount - drug1_current_amount
        drug1_pumped_volume = (
            drug1_pumped_amount / culture.device.pump2.stock_concentration
        )
        drug1_pumped_volume = round(drug1_pumped_volume, 3)
        drug1_pumped_volume = min(
            culture.default_dilution_volume, max(0.1, drug1_pumped_volume)
        )
        if target_concentration == 0:
            drug1_pumped_volume = 0

        drugfree_medium_volume = (
            culture.default_dilution_volume - drug1_pumped_volume
        )  # - drug2_pumped_volume
        drugfree_medium_volume = min(
            culture.default_dilution_volume, max(0, drugfree_medium_volume)
        )
        culture._last_dilution_start_time = time.time()
        culture.dilute(
            pump1_volume=drugfree_medium_volume, pump2_volume=drug1_pumped_volume
        )

    def dilute(
        self, pump1_volume=0.0, pump2_volume=0.0, pump3_volume=0.0, extra_vacuum=5
    ):
        """
        pump_number the given volumes into the vial,
        pump_number the total volume + extra_vacuum out of the vial
        extra_vacuum has to be ~>3 to fill the waste tubing with air and prevent cross-contamination.
        """
        if pump2_volume > 0:
            assert self.medium2_concentration >= 0, "medium2 concentration unknown"
            assert (
                self.device.pump2.stock_concentration >= 0
            ), "stock medium2 concentration unknown"
        if pump3_volume > 0:
            assert self.medium3_concentration >= 0, "medium3 concentration unknown"
            assert (
                self.device.pump3.stock_concentration >= 0
            ), "stock medium3 concentration unknown"
        self.device.make_dilution(
            vial=self.vial_number,
            pump1_volume=pump1_volume,
            pump2_volume=pump2_volume,
            pump3_volume=pump3_volume,
            extra_vacuum=extra_vacuum,
        )
        self.calculate_culture_concentrations_after_dilution(
            pump1_volume, pump2_volume, pump3_volume
        )

    def calculate_culture_concentrations_after_dilution(
        self, pump1_volume, pump2_volume, pump3_volume
    ):
        """
        pump1_volume: Drug-free medium
        pump2_volume: Drug 1
        pump3_volume: Drug 2
        """

        dilution_volume = sum([pump1_volume, pump2_volume, pump3_volume])
        total_volume = self.dead_volume + dilution_volume
        dilution_coefficient = total_volume / self.dead_volume
        self.log2_dilution_coefficient = self.log2_dilution_coefficient + np.log2(
            dilution_coefficient
        )

        if pump2_volume > 0 or self.medium2_concentration > 0:
            medium2_pumped_amount = self.device.pump2.stock_concentration * pump2_volume
            medium2_vial_amount = self.dead_volume * self.medium2_concentration
            medium2_total_amount = medium2_vial_amount + medium2_pumped_amount
            self.medium2_concentration = medium2_total_amount / total_volume

        if pump3_volume > 0 or self.medium3_concentration > 0:
            medium3_pumped_amount = self.device.pump3.stock_concentration * pump3_volume
            medium3_vial_amount = self.dead_volume * self.medium3_concentration
            medium3_total_amount = medium3_vial_amount + medium3_pumped_amount
            self.medium3_concentration = medium3_total_amount / total_volume
        self.save()

    def collect_sample(self, sample_id, sample_volume=1):
        # TODO preserve drug concentrations while sampling
        device = self.device
        vial = self.vial_number
        assert device.locks_vials[vial].acquire(timeout=60)
        assert device.lock_pumps.acquire(timeout=60)
        q = input("ready to collect %d ml sample? [y/n]" % sample_volume)
        if q == "y":
            # must have been checked before releasing the pump_number lock
            assert not device.is_pumping(), "pumping in progress"
            device.stirrers.set_speed(vial=vial, speed=1)
            device.valves.open(
                vial
            )  # valve number might be different for e.g. a lagoon setup
            device.pump1.pump(sample_volume)
            device.pump1.stock_volume -= sample_volume
            log_dilution(device=device, vial_number=vial, pump1_volume=sample_volume)
            while device.is_pumping():
                time.sleep(0.5)
            q = input("Is vial volume at vacuum needle level? [y/n]")
            if q != "y":
                vacuum_volume = sample_volume + 5
                device.pump4.pump(vacuum_volume)
                while device.is_pumping():
                    time.sleep(0.5)
                log_dilution(
                    device=device, vial_number=vial, pump4_volume=vacuum_volume
                )
            self._samples_collected[time.time()] = sample_id
            device.stirrers.set_speed(vial=vial, speed=2)
            assert (
                not device.is_pumping()
            ), "pumping in progress"  # make sure before closing valves
            time.sleep(1)
            device.valves.close(valve=vial)
        device.locks_vials[vial].release()
        device.lock_pumps.release()

    def show_parameters(self, increase_verbosity=False):
        if self.is_active():
            active = "ACTIVE"
        else:
            active = "NOT ACTIVE"
        print(time.ctime())
        print(
            "*********** Vial %d:" % self.vial_number,
            self.__class__.__name__,
            ",",
            active,
        )
        if self.is_active() or increase_verbosity:
            print("             name:", self.name)
            print("      description:", self.description)
            print("               od:", np.round(self.od, 4))
            print("   medium 2 conc.:", np.round(self.medium2_concentration, 4))

            # print("     od_max_limit:", self.od_max_limit)
            print(
                "    last dilution: %.2f minutes ago"
                % np.float32((time.time() - self.time_last_dilution) / 60)
            )
            print(
                "               mu: %.5f ± %.5f [1/h];        max: %.5f"
                % tuple(
                    [
                        np.float32(x)
                        for x in (self.mu, self._mu_error, self._mu_max_measured)
                    ]
                )
            )
            print(
                "       t_doubling: %.2f ± %.2f [h];          min: %.2f"
                % tuple(
                    [
                        np.float32(x)
                        for x in (
                            self.t_doubling,
                            self._t_doubling_error,
                            self._t_doubling_min_measured,
                        )
                    ]
                )
            )
            print(
                "    Generation nr: %.2f" % np.float32(self.log2_dilution_coefficient)
            )
            if increase_verbosity:
                print()
                print("      dead_volume:", self.dead_volume)
                if hasattr(self, "default_dilution_volume"):
                    print("  dilution_volume:", self.default_dilution_volume)
                if self._inoculation_time:
                    print("       inoculated:", time.ctime(self._inoculation_time))
                else:
                    print("       inoculated: NO")

                print("samples_collected:", self._samples_collected)
                print("       is_active:", self.is_active())
                print("         od_blank:", self.od_blank)
                if hasattr(self, "default_dilution_volume"):
                    vial_volume = self.dead_volume
                    added_volume = self.default_dilution_volume
                    dilution_factor = (vial_volume + added_volume) / vial_volume
                    generations_per_dilution = np.log2(dilution_factor)
                    generations_per_ml = generations_per_dilution / added_volume
                    print("generations/Liter: %.1f" % (generations_per_ml * 1000))
            print()

    def inoculate(self, name=None, description=None):
        inoculate(culture=self, name=name, description=description)
        self._mu_max_measured = 0
        self._t_doubling_min_measured = np.inf
        # self._is_active = True
        self.save()

    # @property
    # def widget(self):
    #     user_parameters = [k for k in self.__dict__.keys() if not k.startswith("_") and
    #                        k not in ["name", "description", "directory", "file_lock", "vial_number", "pumps"]]
    #     parameter_style = {'description_width': '230px'}
    #     parameter_widgets = [widgets.FloatText(value=self.__dict__[par], description=par, style=parameter_style,
    #                                            continuous_update=True) for par in user_parameters]
    #     for w in parameter_widgets:
    #         w.observe(self.handle_value_change, names="value")
    #     parameter_box = widgets.VBox(parameter_widgets)
    #
    #     # description_style = {}
    #     # description_widgets = [widgets.HTML('<b>Vial %d:</b>' % self.vial_number, layout=Layout(width="40px")),
    #     #                        widgets.Text(value=self.name, description="name", style=description_style, continuous_update=True),
    #     #                        widgets.Textarea(value=self.description, description="description",
    #     #                                         style=description_style, continuous_update=True)]
    #     # for w in description_widgets:
    #     #     w.observe(self.handle_value_change, names="value")
    #     # description_box = widgets.VBox(description_widgets)
    #     # widgets.HBox([description_box, parameter_box])
    #     return parameter_box
