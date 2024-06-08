# Objective: Optimize the parameters of the MorbidostatUpdater class to minimize the time per IC50 doubling
# The optimization finds the best experiment parameters to maximize adaptation rate.
# Current growth model does not include effects induced by stationary phase.

from experiment.ModelBasedCulture.morbidostat_updater import MorbidostatUpdater, morbidostat_updater_default_parameters
from experiment.ModelBasedCulture.culture_growth_model import CultureGrowthModel, get_simulation_efficiency, culture_growth_model_default_parameters
from test_model import score_model
from scipy.optimize import minimize

updater = MorbidostatUpdater(
    od_dilution_threshold=0.3,  # OD at which dilution occurs
    dilution_factor=1.5,  # Factor by which the population is reduced during dilution
    dilution_number_initial_dose=1,  # Number of dilutions before adding the drug
    dose_initial_added=5,  # Initial dose added to the culture
    dose_increase_factor=1.3,  # Factor by which the dose is increased at stress increases after the initial one
    threshold_growth_rate_increase_stress=0.15,  # Min growth rate threshold for stress increase
    threshold_growth_rate_decrease_stress=0.005,  # Max growth rate threshold for stress decrease
    delay_dilution_max_hours=6,  # Maximum time between dilutions
    delay_stress_increase_min_generations=3,  # Minimum generations between stress increases
    volume_vial=12,  # Volume of the vial
    pump1_stock_drug_concentration=0,  # Concentration of the drug in the pump 1 stock
    pump2_stock_drug_concentration=300)

updater = MorbidostatUpdater(**morbidostat_updater_default_parameters)
model = CultureGrowthModel(**culture_growth_model_default_parameters)
model.updater = updater

model.plot_simulation(simulation_hours=30)
model.plot_parameters()
# score_updater(model)

def objective(x):
    # Map the continuous parameters directly and convert discrete ones
    params = {
        'od_dilution_threshold': x[0],
        'dilution_factor': x[1],
        'initial_added_dose': x[2],
        'dose_increase_factor': x[3],
        'threshold_growth_rate_increase_stress': x[4],
        'threshold_growth_rate_decrease_stress': x[5],
        'delay_stress_increase_min_generations': int(x[6]),  # Discrete parameter
        'volume_vial': 12,  # Fixed parameter
        'pump1_stock_drug_concentration': 0,  # Fixed parameter
        'pump2_stock_drug_concentration': 300,  # Fixed parameter
        'dilutions_before_adding_drug': 1,  # Fixed parameter
        'delay_dilution_max_hours': 6  # Fixed parameter
    }
    model.updater = MorbidostatUpdater(**params)
    return score_model(model)

# Bounds for the parameters: ((min1, max1), (min2, max2), ...)
bounds = [
    (0.3, 0.9),  # od_dilution_threshold
    (1.2, 1.3),  # dilution_factor
    (5, 5),     # initial_added_dose
    (1.1, 1.4),  # dose_increase_factor
    (0.1, 0.12),  # threshold_growth_rate_increase_stress
    (0.001, 0.002),  # threshold_growth_rate_decrease_stress
    (2, 3)  # delay_stress_increase_min_generations, needs to be discrete but handled as continuous
]

# Initial guess
initial_guess = [0.6, 1.8, 5, 1.1, 0.15, 0.005, 3]

result = minimize(objective, initial_guess, method='L-BFGS-B', bounds=bounds, options={'disp': True, 'maxiter': 100})
print("Optimization Result:", result)

result_params = { 'od_dilution_threshold': result.x[0],
                    'dilution_factor': result.x[1],
                    'initial_added_dose': result.x[2],
                    'dose_increase_factor': result.x[3],
                    'threshold_growth_rate_increase_stress': result.x[4],
                    'threshold_growth_rate_decrease_stress': result.x[5],
                    'delay_stress_increase_min_generations': int(result.x[6]),
                    'volume_vial': 12,
                    'pump1_stock_drug_concentration': 0,
                    'pump2_stock_drug_concentration': 300,
                    'dilutions_before_adding_drug': 1,
                    'delay_dilution_max_hours': 6
                    }
print("Optimized Parameters:", result_params)
model.plot_simulation(simulation_hours=30)
