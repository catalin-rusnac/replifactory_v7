from experiment.ModelBasedCulture.culture_growth_model import CultureGrowthModel, get_simulation_efficiency, culture_growth_model_default_parameters
from experiment.ModelBasedCulture.morbidostat_updater import MorbidostatUpdater, morbidostat_updater_default_parameters


def score_model(model):
    model.simulate_experiment(simulation_hours=36)
    volume_per_ic50_doubling, time_per_ic50_doubling = get_simulation_efficiency(model)
    print(f"Volume per IC50 doubling: {volume_per_ic50_doubling} ml")
    print(f"Time per IC50 doubling: {time_per_ic50_doubling} hours")
    return time_per_ic50_doubling


updater = MorbidostatUpdater(**morbidostat_updater_default_parameters)
model = CultureGrowthModel(**culture_growth_model_default_parameters)
model.updater = updater
from experiment.plot import plot_culture

model.simulate_experiment(30)
fig = plot_culture(model)
import plotly.io as pio
pio.show(fig)

# model.plot_parameters()
# score_updater(model)
