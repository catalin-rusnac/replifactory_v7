import time

import numpy as np

from replifactory.culture.blank import BlankCulture
from replifactory.culture.culture_functions import dilute_adjust_drug1


class ChemostatCulture(BlankCulture):
    """
    Implements a quasi-turbidostat culture in a multi-vial device.
    A discrete dilution is made when the OD reaches the threshold,
    allowing the pumps to sequentially maintain all 7 vials.
    The growth is more similar to a real, continuous-dilution turbidostat
    when the dilution factor is small and dilutions are made more frequently.
    """

    pumps = (1, 4)

    def __init__(
        self,
        directory: str = None,
        vial_number: int = None,
        name: str = "Species 1",
        description: str = "Strain 1",
        default_dilution_volume: float = 10,
        dead_volume: float = 15,
    ):
        # Configuration parameters
        self.default_dilution_volume = default_dilution_volume
        self.dead_volume = dead_volume
        #         self.od_max_limit = od_max_limit
        self.dilution_period_mins = 30
        self.initial_dilution_od = 0.3
        self.medium2_c_target = 0
        # Running parameters
        super().__init__(
            directory=directory,
            vial_number=vial_number,
            name=name,
            description=description,
        )

    def dilute_lower_od(self):
        """
        Dilute culture keeping the concentration.
        :return:
        """
        dilute_adjust_drug1(culture=self, target_concentration=self.medium2_c_target)

    def make_chemostat_dilution(self):
        self.dilute_lower_od()

    # def make_custom_schedule(self):
    #     self.scheduler = schedule.Scheduler()
    #     self.scheduler.every(self.dilution_period_min).minutes.do(self.make_chemostat_dilution)

    def update(self):
        """
        called every minute
        """
        if not self.is_active():
            return

        self.update_growth_rate()
        if self._last_dilution_start_time is not None:  # not the first dilution
            deltat_seconds = time.time() - self._last_dilution_start_time
            deltatmin_seconds = self.dilution_period_mins * 60 - 55
            if deltat_seconds >= deltatmin_seconds:
                self.make_chemostat_dilution()
                self.logger.info("Chemostat dilution complete")
                return
        if self.od > self.initial_dilution_od:
            self.make_chemostat_dilution()  # initial dilution
            self.logger.info("First dilution complete")

    def description_text(self):
        vial_volume = self.dead_volume
        added_volume = self.default_dilution_volume
        dilution_factor = (vial_volume + added_volume) / vial_volume
        generations_per_dilution = np.log2(dilution_factor)
        generations_per_l = 1000 * generations_per_dilution / added_volume
        flow_rate = self.default_dilution_volume / (
            self.dilution_period_mins / 60
        )  # mL/h
        #         dilution_rate_per_hr = flow_rate/self.dead_volume

        dilution_rate_per_hr = np.log(dilution_factor) / (
            self.dilution_period_mins / 60
        )
        td = np.log(2) / dilution_rate_per_hr

        t = f"""The {self.dead_volume:.1f}mL culture is diluted with {self.default_dilution_volume:.1f}mL every {self.dilution_period_mins:.0f} min.
dilution factor: 1/{dilution_factor:.2f} ({generations_per_dilution:.2f} generations/dilution)
     medium use: {flow_rate:.2f} mL/h  ({1000/generations_per_l:.1f} mL/generation)
  doubling time: {td*60:.1f} min (growth rate: {dilution_rate_per_hr:.2f}/h)
  """
        return t

    def status_text(self):
        if self.is_active():
            active = "ACTIVE"
        else:
            active = "NOT ACTIVE"
        print(
            "*********** Vial %d:" % self.vial_number,
            self.__class__.__name__,
            ",",
            active,
        )
        if self.is_active():
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
            print()
            print("      dead_volume:", self.dead_volume)
            if hasattr(self, "default_dilution_volume"):
                print("  dilution_volume:", self.default_dilution_volume)
            if self._inoculation_time:
                print("       inoculated:", time.ctime(self._inoculation_time))
            else:
                print("       inoculated: NO")

            print("samples_collected:", self._samples_collected)
            print("       is_aborted:", self._is_aborted)
            print("         od_blank:", self.od_blank)
            if hasattr(self, "default_dilution_volume"):
                vial_volume = self.dead_volume
                added_volume = self.default_dilution_volume
                dilution_factor = (vial_volume + added_volume) / vial_volume
                generations_per_dilution = np.log2(dilution_factor)
                generations_per_ml = generations_per_dilution / added_volume
                print("generations/Liter: %.1f" % (generations_per_ml * 1000))
            print()
