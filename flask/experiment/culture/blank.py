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

    # def check(self):
    #     assert self.device.is_connected()
    #     assert self.vial_number in [1, 2, 3, 4, 5, 6, 7]
    #     assert os.path.exists(self.directory)
    #     assert 0 < self.dead_volume <= 35
    #     assert callable(self.device.od_sensors[self.vial_number].calibration_function)
    #     assert callable(self.device.pump1.calibration_function)
    #     assert callable(self.device.pump4.calibration_function)
    #     assert -0.3 < self.od_blank < 0.3
    #     self.device.stirrers.check_calibration(self.vial_number)

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