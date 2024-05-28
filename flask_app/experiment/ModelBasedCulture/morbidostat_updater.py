from datetime import timedelta

morbidostat_updater_default_parameters = {
    'od_dilution_threshold': 0.3,  # OD at which dilution occurs
    'dilution_factor': 1.6,  # Factor by which the population is reduced during dilution
    'dilution_number_initial_dose': 1,  # Number of dilutions before adding the drug
    'dose_initial_added': 10,  # Initial dose added to the culture
    'dose_increase_factor': 2,  # Factor by which the dose is increased at stress increases after the initial one
    'threshold_growth_rate_increase_stress': 0.15,  # Min growth rate threshold for stress increase
    'threshold_growth_rate_decrease_stress': -0.1,  # Max growth rate threshold for stress decrease
    'delay_dilution_max_hours': 2,  # Maximum time between dilutions
    'delay_stress_increase_min_generations': 3,  # Minimum generations between stress increases
    'volume_vial': 12,  # Volume of the vial in mL
    'pump1_stock_drug_concentration': 0,  # Concentration of the drug in the pump 1 stock
    'pump2_stock_drug_concentration': 300  # Concentration of the drug in the pump 2 stock
}


class MorbidostatUpdater:
    """
    Class to update the culture based on the morbidostat algorithm.
    The update function will dilute the culture at a specified population size (OD) threshold.
    If the growth rate is too high, the drug dose will be increased.
    If the growth rate is too low, the culture will be rescued by diluting it to reduce the drug concentration,
    irrespective of the population size.
    """
    def rescue_condition_is_met(self, model):
        """
        Check that the conditions for a rescue dilution are met positively.:
        - The last dilution was long enough ago (no need to rescue if the last dilution was recent)
        - The growth rate is low enough (no need to rescue if the culture is growing well)
        - The first dilution has already occurred (no need to rescue before the first dilution)

        Used to rescue the culture by diluting it to reduce the drug concentration towards 0, in cases where
        the culture is not growing for a long time and is not adapting to the stress.
        """
        if len(model.doses) < 1:
            # First dilution has not occurred yet, no need to rescue
            return False
        if model.doses[-1][1] > model.time_current - timedelta(hours=self.delay_dilution_max_hours):
            # Last dilution was too recent
            return False
        if model.growth_rate > self.threshold_growth_rate_decrease_stress:
            # Growth rate is too high,
            return False
        print(model.growth_rate, self.threshold_growth_rate_decrease_stress,"Rescue condition met")
        return True

    def __init__(self, **kwargs):
        defaults = morbidostat_updater_default_parameters.copy()
        defaults.update(kwargs)
        for key, value in defaults.items():
            setattr(self, key, value)

    def dilute_to_wash_if_necessary(self, model):
        """
        Perform a washing dilution to keep the tubing wet and prevent clogging.
        """
        if not model.population:
            return
        target_dose = self.pump2_stock_drug_concentration * 0.02
        if model.doses:
            target_dose = max(target_dose, model.doses[-1][0])
            last_pump_time = model.doses[-1][1]
        else:
            last_pump_time = model.population[0][1]
        if model.time_current - last_pump_time > timedelta(hours=self.delay_dilution_max_hours):
            # print("Washing dilution, target dose", target_dose, "time_current", model.time_current)
            model.dilute_culture(target_dose=target_dose, dilution_factor=1.2)

    def update(self, model):
        if len(model.population) == 0:
            return
        if model.population[-1][0] >= self.od_dilution_threshold:
            target_dose = 0
            if len(model.doses) == self.dilution_number_initial_dose:
                target_dose = self.dose_initial_added
            elif len(model.doses) > self.dilution_number_initial_dose:
                target_dose = model.doses[-1][0]
                if len(set([d[0] for d in model.doses])) == 1:
                    last_dose_change_time = model.doses[0][1]
                else:
                     last_dose_change_time = [dose[1] for dose in model.doses if dose[0] != model.doses[-1][0]][-1]


                generation_at_last_dose_change = \
                [gen[0] for gen in model.generations if gen[1] >= last_dose_change_time][0]
                generations_since_last_dose_change = model.generations[-1][0] - generation_at_last_dose_change
                if model.growth_rate > self.threshold_growth_rate_increase_stress and \
                    generations_since_last_dose_change > self.delay_stress_increase_min_generations:
                    target_dose = model.doses[-1][0] * self.dose_increase_factor
                    target_dose = round(target_dose, 3)
            # print("Dilution to target dose", target_dose, "time_current", model.time_current)
            model.dilute_culture(target_dose)

        elif self.rescue_condition_is_met(model):
            print("Rescue dilution")
            model.dilute_culture(target_dose=0)
        self.dilute_to_wash_if_necessary(model)


