import os
import threading
import time

import numpy as np

from replifactory.culture.blank import CultureLogger
from replifactory.util.loading import save_object
from replifactory.util.other import write_variable


class CultureUniversal:
    logged_variables = [
        "_od",
        "_od_raw",
        "_mu",
        "_mu_error",
        "_t_doubling",
        "_t_doubling_error",
        "_medium2_concentration",
        "_log2_dilution_coefficient",
    ]
    logged_parameters = [
        "_n_dilutions",
        "_n_dilutions_last_stress_increase",
        "_n_dilutions_last_stress_decrease",
        "_last_stress_increase_time",
        "_last_stress_decrease_time",
        "_inoculation_time",
        "_is_initialized_to_starting_dose",
        "_is_initialized_to_starting_dose",
    ]

    def __init__(
        self,
        directory: str = None,
        vial_number: int = None,
        name: str = "Culture",
        description: str = "Culture description",
    ):
        # super().__init__(directory, vial_number, name, description)

        self.volume_max = 40
        self.volume_dead = 15
        self.volume_added_at_dilution = 10
        self.dilution_trigger_od_initial = 0.8

        self.subsequent_dilution_trigger = "OD"
        self.dilution_delay = 60 * 40
        self.dilution_trigger_od = 0.3

        self.stress_increase_initial_dilution_number = 5
        self.stress_increase_initial_dose = 10
        self.stress_increase_ramp_factor = 1.33
        self.stress_increase_delay_dilutions = 3
        self.stress_increase_t_doubling_threshold = 4 * 60 * 60  # 4 hours

        self.no_growth_period_max = 16 * 60 * 60
        self.no_growth_t_doubling_threshold = 24

        self.flush_dilution_delay = 48 * 60 * 60
        self.flush_dilution_volume = 2
        self.flush_concentration_max = 0.03

        self._last_tubing_flush_time = None
        self._log2_dilution_coefficient = None

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
        self.od_blank = 0
        self.disabled = True

        self._n_dilutions = 0
        self._n_dilutions_last_stress_increase = 0
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

        self._last_dilution_start_time = None

        self._mu_max_measured = 0
        self._t_doubling_min_measured = np.inf
        self._time_last_dilution = {1: None, 2: None, 3: None, 4: None}

    def __setattr__(self, name, value):
        if value in self.logged_variables:
            write_variable(culture=self, variable_name=name, value=value)
        if value in self.logged_parameters:
            self.logger.info("Setting %s to %s" % (name, value))
            self.save()
        object.__setattr__(self, name, value)

    def save(self):
        self.file_lock.acquire()  # maybe not necessary?
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)
        config_path = os.path.join(self.directory, "culture_config.yaml")

        save_object(self, filepath=config_path)
        self.file_lock.release()
        if self.logger:
            self.logger.info("Saved config")

    def update(self):
        """
        Update the culture's state - make dilutions if necessary, etc.
        dilution conditions:
        """
        if self.disabled:
            return
        if self.time_for_first_dilution():
            self.make_first_dilution()
            return
        if self.time_for_scheduled_dilution():
            self.make_scheduled_dilution()
            return

    # properties

    @property
    def age(self):
        """
        :return: seconds since the culture was inoculated
        """
        if self._inoculation_time is None:
            return 0
        return time.time() - self._inoculation_time

    @property
    def age_since_last_dilution(self):
        """
        :return: seconds since the last dilution was made
        """
        if self._last_dilution_start_time is None:
            return 0
        return time.time() - self._last_dilution_start_time

    # \properties

    def time_for_first_dilution(self):
        """
        :return: True if both:
            1) the culture OD is high enough to be diluted
            2) the culture has not already been diluted
        """
        if self._last_dilution_start_time is not None:
            return False
        return self._od > self.dilution_trigger_od_initial

    def get_default_dilution_factor(self):
        """
        :return: the dilution factor for the culture given the dead volume\
        and default dilution volume (e.g. 2 for a 1:2 dilution)
        """
        total_volume = self.volume_dead + self.volume_added_at_dilution
        working_volume = self.volume_dead
        return total_volume / working_volume

    def time_for_scheduled_dilution(self):
        """
        :return: True if the culture is old enough to be diluted
        """
        if self.subsequent_dilution_trigger == "OD":
            # if self.diluting_like_crazy():
            #     return False
            return self._od > self.dilution_trigger_od
        elif self.subsequent_dilution_trigger == "age":
            return self.age_since_last_dilution > self.dilution_period
        else:
            raise ValueError("subsequent_dilution_trigger must be 'OD' or 'age'")

    def make_scheduled_dilution(self):
        if self.time_to_increase_stress():
            self.increase_stress()
            return
        if self.time_to_decrease_stress():
            self.decrease_stress()
            return

        if self.time_to_flush_tubing():
            self.flush_tubing()
            return

    def time_to_flush_tubing(self):
        if self._last_dilution_start_time is not None:
            self._last_tubing_flush_time = self._last_dilution_start_time
        if self._last_tubing_flush_time is None:  # TODO: test behavior of this
            self._last_tubing_flush_time = (
                time.time() - 60 * 60
            )  # 1h before first call of this function
        return self.flush_dilution_delay > time.time() - self._last_tubing_flush_time

    def calculate_volumes_flush_tubing(self):
        target_concentration = self._medium2_concentration
        pump1_volume, pump2_volume = self.calculate_pump_volumes(
            target_concentration=target_concentration
        )
        if pump2_volume > 0.5 and pump1_volume > 0.5:
            return pump1_volume, pump2_volume

    def increase_stress(self):
        if (
            self._medium2_concentration == 0
            or self._n_dilutions_last_stress_increase == 0
        ):
            self.dilute_adjust_drug1(
                target_concentration=self.stress_increase_initial_dose
            )
        target_concentration = (
            self._medium2_concentration * self.stress_increase_ramp_factor
        )
        self.dilute_adjust_drug1(target_concentration=target_concentration)
        self._n_dilutions_last_stress_increase = self._n_dilutions

    def decrease_stress(self):
        self.dilute_adjust_drug1(target_concentration=0)

    def time_to_increase_stress(self):
        """
        :return: True if the culture is healthy enough to increase the stress level
                (if 4 things are true:
                A) the culture has been diluted enough times
                B) the culture is growing fast enough
                C) stress has not been increased for a long time
                D) the culture density is high enough)
        """
        has_been_diluted_enough = (
            self._n_dilutions >= self.stress_increase_initial_dilution_number
        )
        growing_fast_enough = (
            self._t_doubling < self.stress_increase_t_doubling_threshold
        )
        has_not_been_stressed_enough = (
            self._n_dilutions - self._n_dilutions_last_stress_increase - 1
            >= self.stress_increase_delay_dilutions
        )
        is_dense_enough = self._od > self.dilution_trigger_od
        return (
            has_been_diluted_enough
            and growing_fast_enough
            and has_not_been_stressed_enough
            and is_dense_enough
        )

    def time_to_decrease_stress(self):
        """
        :return: True if the culture is unhealthy enough to decrease the stress level
                (if 2 things are true:
                A) the culture is not growing anymore and
                B) has not been diluted for a long time)
        """
        if self._last_dilution_start_time is None:
            return False  # not yet diluted, so no stress to decrease
        is_not_growing = self._t_doubling > self.no_growth_t_doubling_threshold
        was_not_diluted_recently = (
            self.age_since_last_dilution > self.no_growth_period_max
        )
        return is_not_growing and was_not_diluted_recently

    def make_first_dilution(self):
        """
        Dilute the culture for the first time
        """
        self._last_dilution_start_time = time.time()
        self.dilute_adjust_drug1()
        # self._device.make_dilution(vial=self.vial_number,
        #                           pump1_volume=pump1_volume,
        #                           pump2_volume=pump2_volume,
        #                           pump3_volume=pump3_volume,
        #                           extra_vacuum=extra_vacuum)
        #
        # self.calculate_culture_concentrations_after_dilution(pump1_volume, pump2_volume, pump3_volume)

    def calculate_pump_volumes(
        self,
        dilution_factor=None,
        stress_increase_factor=None,
        target_concentration=None,
    ):
        """
        Calculate the pumped volumes to achieve a given dilution
        :param dilution_factor: dilution factor (e.g. 2 for a 1:2 dilution)
        :param stress_increase_factor: stress increase factor (e.g. 2 for a 2x increase)
        :param target_concentration: target concentration of drug1 in the culture
        :return: (pump1_volume, pump2_volume)
        """
        culture = self
        if dilution_factor is None:
            dilution_factor = (
                culture.volume_dead + culture.volume_added_at_dilution
            ) / culture.volume_dead
        total_volume = culture.volume_dead + culture.volume_added_at_dilution
        if target_concentration is None:
            if stress_increase_factor is None:
                stress_increase_factor = (dilution_factor + 1) / 2
            medium2_target_concentration = (
                culture._medium2_concentration * stress_increase_factor
            )
            if culture._medium2_concentration == 0:
                medium2_target_concentration = (
                    culture.device.pump2.stock_concentration / 50
                )
        else:
            medium2_target_concentration = target_concentration

        drug1_total_amount = total_volume * medium2_target_concentration
        drug1_current_amount = culture.volume_dead * culture._medium2_concentration
        drug1_pumped_amount = drug1_total_amount - drug1_current_amount
        drug1_pumped_volume = (
            drug1_pumped_amount / culture.device.pump2.stock_concentration
        )
        drug1_pumped_volume = round(drug1_pumped_volume, 3)
        drug1_pumped_volume = min(
            culture.volume_added_at_dilution, max(0.1, drug1_pumped_volume)
        )
        if target_concentration == 0:
            drug1_pumped_volume = 0

        drugfree_medium_volume = (
            culture.volume_added_at_dilution - drug1_pumped_volume
        )  # - drug2_pumped_volume
        drugfree_medium_volume = min(
            culture.volume_added_at_dilution, max(0, drugfree_medium_volume)
        )
        return drugfree_medium_volume, drug1_pumped_volume

    def dilute_adjust_drug1(
        self,
        dilution_factor=None,
        stress_increase_factor=None,
        target_concentration=None,
    ):
        pump1_volume, pump2_volume = self.calculate_pump_volumes(
            dilution_factor=dilution_factor,
            stress_increase_factor=stress_increase_factor,
            target_concentration=target_concentration,
        )
        self._last_dilution_start_time = time.time()
        self.dilute(pump1_volume=pump1_volume, pump2_volume=pump2_volume)

    def dilute(
        self, pump1_volume=0.0, pump2_volume=0.0, pump3_volume=0.0, extra_waste=5
    ):
        """
        Dilute the culture
        :param pump1_volume: volume of medium to add
        :param pump2_volume: volume of drug1 to add
        :param pump3_volume: volume of drug2 to add
        :param extra_waste: extra waste to pump out (to fill tubing with air)
        """
        self.device.make_dilution(
            vial=self.vial_number,
            pump1_volume=pump1_volume,
            pump2_volume=pump2_volume,
            pump3_volume=pump3_volume,
            extra_vacuum=extra_waste,
        )  # TODO: device extra_waste rename
        self.adjust_culture_concentrations_after_dilution(
            pump1_volume, pump2_volume, pump3_volume
        )

    def calculate_culture_concentrations_after_dilution(
        self, pump1_volume, pump2_volume, pump3_volume
    ):
        """
        Calculate the concentrations of the culture after a dilution
        :param pump1_volume: volume of medium to add
        :param pump2_volume: volume of drug1 to add
        :param pump3_volume: volume of drug2 to add
        """
        volume_added = sum([pump1_volume, pump2_volume, pump3_volume])
        total_volume = self.volume_dead + volume_added

        new_medium2_concentration = None
        new_medium3_concentration = None

        if pump2_volume > 0 or self._medium2_concentration > 0:
            medium2_pumped_amount = self.device.pump2.stock_concentration * pump2_volume
            medium2_vial_amount = self.volume_dead * self._medium2_concentration
            medium2_total_amount = medium2_vial_amount + medium2_pumped_amount
            new_medium2_concentration = medium2_total_amount / total_volume
        if pump3_volume > 0 or self._medium3_concentration > 0:
            medium3_pumped_amount = self.device.pump3.stock_concentration * pump3_volume
            medium3_vial_amount = self.volume_dead * self._medium3_concentration
            medium3_total_amount = medium3_vial_amount + medium3_pumped_amount
            new_medium3_concentration = medium3_total_amount / total_volume
        return new_medium2_concentration, new_medium3_concentration

    def adjust_culture_concentrations_after_dilution(
        self, pump1_volume, pump2_volume, pump3_volume
    ):
        """
        pump1_volume: Drug-free medium
        pump2_volume: Drug 1
        pump3_volume: Drug 2
        """
        volume_added = sum([pump1_volume, pump2_volume, pump3_volume])
        total_volume = self.volume_dead + volume_added
        dilution_coefficient = total_volume / self.volume_dead

        self._log2_dilution_coefficient = self._log2_dilution_coefficient + np.log2(
            dilution_coefficient
        )

        (
            new_medium2_concentration,
            new_medium3_concentration,
        ) = self.calculate_culture_concentrations_after_dilution(
            pump1_volume, pump2_volume, pump3_volume
        )

        if new_medium2_concentration is not None:
            self._medium2_concentration = new_medium2_concentration
        if new_medium3_concentration is not None:
            self._medium3_concentration = new_medium3_concentration
