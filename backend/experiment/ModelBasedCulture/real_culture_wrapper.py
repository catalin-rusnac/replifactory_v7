from datetime import datetime
from pprint import pprint


class RealCultureWrapper:
    """
    Adapter class to convert the culture class to the model class.
    """
    def __init__(self, culture):
        self.culture = culture
    
    @property
    def vial(self):
        return self.culture.vial

    @property
    def population(self):
        # od_dict = {k: v for k, v in sorted(od_dict.items(), key=lambda item: item[0])}
        od_dict, mu_dict, rpm_dict = self.culture.get_last_ods_and_rpms()
        population = [(od, time) for time, od in od_dict.items()]
        return population

    @property
    def effective_growth_rates(self):
        od_dict, mu_dict, rpm_dict = self.culture.get_last_ods_and_rpms()
        effective_growth_rates = [(mu, time) for time, mu in mu_dict.items()]
        return effective_growth_rates

    @property
    def growth_rate(self):
        return self.culture.growth_rate

    @property
    def generations(self):
        generation_dict, concentration_dict = self.culture.get_last_generations()
        generations = [(generation, time) for time, generation in generation_dict.items()]
        return generations

    @property
    def doses(self):
        generation_dict, concentration_dict = self.culture.get_last_generations()
        doses = [(concentration, time) for time, concentration in concentration_dict.items()]
        return doses

    @property
    def time_current(self):
        return self.culture.time_current

    @property
    def first_od_timestamp(self):
        return self.culture.get_first_od_timestamp()

    def print_updater_status(self):
        # print time formatted as string
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Vial", self.culture.vial)
        pprint(self.culture.updater.status_dict)

    def dilute_culture(self, target_dose, dilution_factor=None):
        self.print_updater_status()
        if dilution_factor is None:
            dilution_factor = self.culture.updater.dilution_factor
        self.culture.make_culture_dilution(target_dose, dilution_factor)



# if isinstance(culture, CultureGrowthModel):
#     plotting_model = True
#     ods = {p[1]: p[0] for p in culture.population}
#     mus = {p[1]: p[0] for p in culture.effective_growth_rates}
#     concs = {p[1]: p[0] for p in culture.doses}
#     gens = {p[1]: p[0] for p in culture.generations}
#     rpms = {}
#     culture_parameters = {}
#     od_threshold = 1
#     vf = culture.updater.volume_vial
#     dilution_factor = culture.updater.dilution_factor
#     va = culture.updater.volume_vial * (dilution_factor - 1)
#     stress_decrease_delay_hrs = culture.updater.delay_stress_increase_min_generations  # TODO: Change this to hours
#     vial_number = 1
#     experiment_name = "Model"
#     culture_parameters = culture.updater.__dict__
# else:
#     # Extract data from real experiment
#     ods, mus, rpms = culture.get_last_ods_and_rpms(limit=limit)
#     gens, concs = culture.get_last_generations(limit=limit)
#     od_threshold = culture.parameters["od_threshold"]
#     vf = culture.parameters["volume_fixed"]
#     va = culture.parameters["volume_added"]
#     dilution_factor = (vf + va) / vf
#     stress_decrease_delay_hrs = culture.parameters["stress_decrease_delay_hrs"]
#     vial_number = culture.vial
#     experiment_name = culture.experiment.model.name
#     culture_parameters = culture.parameters.inner_dict


# from experiment.ModelBasedCulture.culture_growth_model import CultureGrowthModel
# from experiment.ModelBasedCulture.morbidostat_updater import MorbidostatUpdater
#
# updater = MorbidostatUpdater()
# culture_model = CultureGrowthModel()

# culture_real = Culture()
# culture_wrapped =