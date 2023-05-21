import os

import numpy as np

from replifactory.culture.chemostat import ChemostatCulture


class TurbidostatCulture(ChemostatCulture):
    """
    Implements a quasi-turbidostat culture in a multi-vial device.
    A discrete dilution is made when the OD reaches the threshold,
    allowing the pumps to sequentially maintain all 7 vials.
    The growth is more similar to a real, continuous-dilution turbidostat
    when the dilution factor is small and dilutions are made more frequently.
    """

    def __init__(
        self,
        directory: str = None,
        vial_number: int = None,
        name: str = "Species 1",
        description: str = "Strain 1",
    ):
        # Configuration parameters
        self.default_dilution_volume = 10
        self.dead_volume = 15
        self.od_max_limit = 0.3
        self.minimum_dilution_delay_mins = 5
        # Running parameters
        super().__init__(
            directory=directory,
            vial_number=vial_number,
            name=name,
            description=description,
        )
        if hasattr(self, "dilution_period_mins"):
            del self.dilution_period_mins

    def description_text(self):
        vial_volume = self.dead_volume
        added_volume = self.default_dilution_volume
        dilution_factor = (vial_volume + added_volume) / vial_volume
        generations_per_dilution = np.log2(dilution_factor)
        max_flow_rate = self.default_dilution_volume / (
            self.minimum_dilution_delay_mins / 60
        )  # mL/h

        max_dilution_rate_per_hr = np.log(dilution_factor) / (
            self.minimum_dilution_delay_mins / 60
        )
        max_td = np.log(2) / max_dilution_rate_per_hr

        t = (
            f"\nWhen OD > {self.od_max_limit:.2f}, the {self.dead_volume:.1f}mL culture "
            + f"is diluted with {self.default_dilution_volume:.1f}mL total volume "
            + f"(every {generations_per_dilution:.2f} generations),"
            + f"\nbut not more often than every {self.minimum_dilution_delay_mins:.1f} minutes"
            + f"\n          max flow rate: {max_flow_rate:.2f} mL/h"
            + f"\n      min doubling time: {max_td*60:.1f} min  (growth rate: {max_dilution_rate_per_hr:.2f}/h)"
        )
        return t

    @property
    def diluting_like_crazy(self):
        if not os.path.exists(os.path.join(self.directory, "dilutions.csv")):
            return False
        return self.minutes_since_last_dilution < self.minimum_dilution_delay_mins

    def update(self):
        """
        called every minute
        """
        if self.is_active():
            self.update_growth_rate()
            if self.od > np.float32(self.od_max_limit):
                if not self.diluting_like_crazy:
                    # self.write_log("lowering od")
                    # self.write_log()
                    self.dilute_lower_od()

    def check(self):
        assert self.device.is_connected(), "device not connected"
        assert self.vial_number in [1, 2, 3, 4, 5, 6, 7], "vial number not between 1-7"
        assert os.path.exists(self.directory), "directory does not exist"
        assert 0 < self.dead_volume <= 35, "dead volume wrong"
        assert (
            0 < self.default_dilution_volume <= 40 - self.dead_volume
        ), "default dilution volume too high"
        # assert 0 < self.od_max_limit <= 50
        assert callable(
            self.device.od_sensors[self.vial_number].calibration_function
        ), "OD calibration function missing"
        assert callable(
            self.device.pump1.calibration_function
        ), "pump1 calibration function missing"
        assert callable(
            self.device.pump4.calibration_function
        ), "pump4 calibration function missing"
        assert -0.3 < self.od_blank < 0.3, "od blank value error"
        self.device.stirrers.check_calibration(self.vial_number)

    # def flush_tubing_if_necessary(self):
    #     if not self._is_aborted:
    #         pump_volumes = {1: 0, 2: 0}
    #         tstart = self.experiment_start_time
    #         tinoc = np.float32(self._inoculation_time)
    #         for pump_number in self.active_pumps:
    #             tdil = np.float32(self._time_last_dilution[pump_number])
    #             last_pump_time = np.nanmax([tdil, tstart, tinoc])
    #             if (time.time() - last_pump_time) > self.device.drying_prevention_pump_period_hrs * 3600:
    #                 pump_volumes[pump_number] = self.device.drying_prevention_pump_volume
    #         if pump_volumes[1] > 0 or pump_volumes[2] > 0:
    #             self.dilute(pump1_volume=pump_volumes[1], pump2_volume=pump_volumes[2], pump3_volume=0)
