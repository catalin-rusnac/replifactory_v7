from experiment.ModelBasedCulture.culture_growth_model import CultureGrowthModel, get_simulation_efficiency, culture_growth_model_default_parameters
from experiment.ModelBasedCulture.morbidostat_updater import MorbidostatUpdater, morbidostat_updater_default_parameters

updater = MorbidostatUpdater(**morbidostat_updater_default_parameters)
model = CultureGrowthModel(**culture_growth_model_default_parameters)
model.updater = updater
from experiment.plot import plot_culture

model.simulate_experiment(24)
fig = plot_culture(model)
import plotly.io as pio
pio.show(fig)
print(model.updater.get_status())
print(model.updater.status_dict)
# model.plot_parameters()
# score_updater(model)
