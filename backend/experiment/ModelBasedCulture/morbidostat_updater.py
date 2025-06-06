from datetime import timedelta
from pprint import pprint
import numpy as np

morbidostat_updater_default_parameters = {
    'volume_vial': 12,  # Volume of the vial in mL (liquid volume under waste needle)
    'pump1_stock_drug_concentration': 0,  # Concentration of the drug in the pump 1 stock bottle
    'pump2_stock_drug_concentration': 100,  # Concentration of the drug in the pump 2 stock bottle
    'dose_initialization': 3,  # Initial dose added to the culture immediately when the experiment starts. -1 to disable

    'dilution_factor': 1.6,  # Factor by which the population is reduced during dilution
    'od_dilution_threshold': 0.3,  # OD at which dilution occurs, -1 to disable OD triggered dilution. -1 to disable OD triggered dilution
    'delay_dilution_max_hours': 4,    # Maximum time between dilutions. Exact time if there are no other dilution triggers. -1 to disable time triggered dilution

    'dilution_number_first_drug_addition': 2,  # Dilution number at which dose_first_drug_addition is added. -1 to disable drug addition
    'dose_first_drug_addition': 1,  # Initial drug dose resulting in the vial at the first dilution triggered by OD or time
    'dose_increase_factor': 2,  # Factor by which the dose is increased at stress increases (new_dose = old_dose * factor + amount)
    'dose_increase_amount': 0,  # Amount by which the dose is increased at stress increases (new_dose = old_dose * factor + amount)

    'threshold_od_min_increase_stress': 0.1,  # Minimum OD for stress increase (increase dose if OD is higher)
    'threshold_growth_rate_increase_stress': 0.15,  # Minimum growth rate for stress increase (increase dose if growth rate is higher)
    'threshold_growth_rate_decrease_stress': -0.1,  # Maximum growth rate for rescue dilution (rescue if growth rate is lower)
    'delay_stress_increase_min_generations': 2,  # Minimum number of generations between stress increases.
    'postfill': 0, # Whether to add media before pumping waste (1) or pump waste before adding media (0)
}


class MorbidostatUpdater:
    """
    Class to update the culture based on the morbidostat algorithm.
    The update function will dilute the culture at a specified population size (OD) threshold.
    If the growth rate is too high, the drug dose will be increased.
    If the growth rate is too low, the culture will be rescued by diluting it to reduce the drug concentration,
    irrespective of the population size.
    """

    def __init__(self, **kwargs):
        defaults = morbidostat_updater_default_parameters.copy()
        defaults.update(kwargs)
        for key, value in defaults.items():
            setattr(self, key, value)
        self.status_dict = {}

    def is_time_to_increase_stress(self, model):
        """
        Check if it is time to increase stress. Conditions:
        - OD is above threshold
        - Growth rate is above threshold
        - Sufficient generations have passed since last dose change
        - Stress increase is not disabled
        - At least one dilution has been made
        """
        if -1 in [self.threshold_growth_rate_increase_stress, self.delay_stress_increase_min_generations]:
            self.status_dict["time_to_increase_stress"] = "Stress increase disabled"
            return False
        if len(model.doses)<1:
            self.status_dict["time_to_increase_stress"] = "No dilutions yet. Not increasing stress"
            return False
        last_dose_change_time = model.doses[0][1]
        current_dose = round(model.doses[-1][0], 3)
        for dose in model.doses:
            if round(dose[0], 3) != current_dose:
                last_dose_change_time = dose[1]
        # last_dose_change_time = [dose[1] for dose in model.doses if dose[0] != model.doses[-1][0]][-1]

        generations_at_last_dose_change = [gen[0] for gen in model.generations if gen[1] >= last_dose_change_time][0]
        generations_at_next_dilution = model.generations[-1][0] + np.log2(self.dilution_factor)
        generations_since_last_dose_change = generations_at_next_dilution - generations_at_last_dose_change
        enough_generations_have_passed = generations_since_last_dose_change > self.delay_stress_increase_min_generations
        if model.growth_rate is None:
            self.status_dict["time_to_increase_stress"] = "Growth rate is None. Not increasing stress"
            return False
        growing_fast_enough = model.growth_rate > self.threshold_growth_rate_increase_stress
        od_above_stress_increase_threshold = model.population[-1][0] > self.threshold_od_min_increase_stress

        if not od_above_stress_increase_threshold:
            self.status_dict["time_to_increase_stress"] = "OD %3f < threshold %3f for stress increase" % (model.population[-1][0], self.threshold_od_min_increase_stress)
            return False
        if not enough_generations_have_passed:
            self.status_dict["time_to_increase_stress"] = "%.2f generations since last dose change < %.2f threshold. Not increasing stress" % (generations_since_last_dose_change, self.delay_stress_increase_min_generations)
            return False
        if not growing_fast_enough:
            self.status_dict["time_to_increase_stress"] = "Growth rate %.3f < threshold %.3f. Not increasing stress" % (model.growth_rate, self.threshold_growth_rate_increase_stress)
            return False
        self.status_dict["time_to_increase_stress"] = "Growing fast enough and enough generations have passed since last stress increase. Increasing stress"
        return True

    def is_time_to_decrease_stress(self, model):
        """
        Check if it is time to decrease stress.
        """
        if -1 in [self.threshold_growth_rate_decrease_stress, self.delay_stress_increase_min_generations, self.dose_increase_factor]:
            self.status_dict["time_to_decrease_stress"] = "Stress decrease disabled"
            return False
        if model.growth_rate is None:
            self.status_dict["time_to_decrease_stress"] = "Growth rate is None. Not decreasing stress"
            return False
        if model.growth_rate > self.threshold_growth_rate_decrease_stress:
            self.status_dict["time_to_decrease_stress"] = "Growth rate %.3f > threshold %.3f. Not decreasing stress" % (model.growth_rate, self.threshold_growth_rate_decrease_stress)
            return False
        self.status_dict["time_to_decrease_stress"] = "Growth rate %.3f < threshold %.3f. Decreasing stress" % (model.growth_rate, self.threshold_growth_rate_decrease_stress)
        return True

    def dilute_and_adjust_dose(self, model):
        """
        Dilute the culture to the target dose and adjust the dose if necessary.
        """
        # check if time to initialize culture
        next_dilution_number = len(model.doses) + 1
        if next_dilution_number < self.dilution_number_first_drug_addition:
            if model.doses:
                target_dose = model.doses[-1][0]
                self.status_dict["dilution_message"] = "Dilution %d to dose %3f. Drug addition at dilution %d" % (next_dilution_number, target_dose, self.dilution_number_first_drug_addition)
            else:
                target_dose = self.pump1_stock_drug_concentration
                self.status_dict["dilution_message"] = "Dilution %d to dose %3f. Drug addition at dilution %d" % (next_dilution_number, target_dose, self.dilution_number_first_drug_addition)
            model.dilute_culture(target_dose)
            return

        # Check if time to add first drug dose
        if next_dilution_number == self.dilution_number_first_drug_addition:
            target_dose = self.dose_first_drug_addition
            self.status_dict["dilution_message"] = "First drug addition at dilution %d with dose %3f" % (next_dilution_number, target_dose)
            model.dilute_culture(target_dose)
            return

        if self.is_time_to_increase_stress(model):
            target_dose = self.calculate_increased_dose(model.doses[-1][0])
            self.status_dict["dilution_message"] = "Increasing dose to target %3f" % target_dose
            model.dilute_culture(target_dose)
            return

        if self.is_time_to_decrease_stress(model):
            self.status_dict["dilution_message"] = "Decreasing stress to pump1_stock_drug_concentration"
            model.dilute_culture(target_dose=self.pump1_stock_drug_concentration)
            return

        if len(model.doses) == 0:
            target_dose = self.dose_initialization
            self.status_dict["dilution_message"] = "Initializing culture to %3f" % target_dose
            model.dilute_culture(target_dose)
            return
        self.status_dict["dilution_message"] = "Diluting to last dose %3f" % model.doses[-1][0]
        model.dilute_culture(target_dose=model.doses[-1][0])

    def calculate_increased_dose(self, current_dose):
        """
        Calculate the new dose based on the current dose, dose increase factor, and dose increase amount.
        """
        new_dose = current_dose * self.dose_increase_factor + self.dose_increase_amount
        return round(new_dose, 3)

    def make_initialization_dilution_if_necessary(self, model):
        if self.dose_initialization < 0:
            self.status_dict["initialization_dilution"] = "Initialization disabled"
            return
        if len(model.doses) > 0:
            self.status_dict["initialization_dilution"] = "Initialization already done!"
            return

        self.status_dict["initialization_dilution"] = "Initialization enabled and no dilutions have been made yet - time to initialize!"
        target_dose = self.dose_initialization
        self.status_dict["dilution_message"] = "Initializing culture to %3f" % target_dose
        model.dilute_culture(target_dose)
        return True

    def make_time_triggered_dilution_if_necessary(self, model):
        if self.delay_dilution_max_hours < 0:
            self.status_dict["time_triggered_dilution"] = "Time triggered dilution disabled"
            return
        if len(model.doses) == 0:
            self.status_dict["time_triggered_dilution"] = "No dilutions made yet"
            return
        last_dilution_timestamp = model.doses[-1][1]
        hours_since_last_dilution = (model.time_current - last_dilution_timestamp).total_seconds() / 3600
        if hours_since_last_dilution < self.delay_dilution_max_hours:
            self.status_dict["time_triggered_dilution"] = "Hours since last dilution %.2f < max %.2f, not diluting" % (hours_since_last_dilution, self.delay_dilution_max_hours)
            return
        self.status_dict["time_triggered_dilution"] = "Hours since last dilution %.2f > max %.2f, diluting" % (hours_since_last_dilution, self.delay_dilution_max_hours)
        self.dilute_and_adjust_dose(model)
        return True

    def make_od_triggered_dilution_if_necessary(self, model):
        if self.od_dilution_threshold < 0:
            self.status_dict["od_triggered_dilution"] = "OD triggered dilution disabled"
            return
        if len(model.population) == 0:
            self.status_dict["od_triggered_dilution"] = "No OD measurements yet"
            return
        if model.population[-1][0] < self.od_dilution_threshold:
            self.status_dict["od_triggered_dilution"] = "OD %3f < threshold %3f" % (model.population[-1][0], self.od_dilution_threshold)
            return
        self.status_dict["od_triggered_dilution"] = "OD %3f >= threshold %3f, diluting" % (model.population[-1][0], self.od_dilution_threshold)
        self.dilute_and_adjust_dose(model)
        return True

    def must_wait_since_last_dilution(self, model):
        minutes_since_last_dilution = 4
        if len(model.doses) > 0:
            od_timestamp = model.population[-1][1]
            doses_timestamp = model.doses[-1][1]
            if od_timestamp < doses_timestamp + timedelta(minutes=minutes_since_last_dilution):
                self.status_dict["must_wait_since_last_dilution"] = "%d minutes have not passed since last dilution" % minutes_since_last_dilution
                return True
        self.status_dict["must_wait_since_last_dilution"] = "No, last OD data more than %d minutes since last dilution" % minutes_since_last_dilution
        return False

    def update(self, model):
        if self.must_wait_since_last_dilution(model):
            return
        if self.make_initialization_dilution_if_necessary(model):
            return
        if self.make_time_triggered_dilution_if_necessary(model):
            return
        self.make_od_triggered_dilution_if_necessary(model)
