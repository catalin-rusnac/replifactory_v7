from datetime import datetime, timedelta

import numpy as np

from experiment.experiment import Experiment
from experiment.database_models import ExperimentModel, db
from flask_app.server import create_app
app = create_app()
ctx = app.app_context()
ctx.push()

experiment_model = db.session.get(ExperimentModel, 1)
dev = None
if hasattr(ctx.app, 'dev'):
    dev = ctx.app.dev
exp = Experiment(dev, experiment_model, db)
c = exp.cultures[1]
#%%
c = exp.cultures[2]
c.get_latest_data_from_db()
def test_is_time_to_rescue():
    # Test case 1: last_dilution_time is None
    c.last_dilution_time = None
    assert not c.is_time_to_rescue(verbose=True), "Expected False when last_dilution_time is None"

    # Test case 2: growth_rate is None
    c.last_dilution_time = datetime.now()
    c.growth_rate = None
    assert not c.is_time_to_rescue(verbose=True), "Expected False when growth_rate is None"

    # Test case 3: last_dilution_time is too recent
    c.last_dilution_time = datetime.now() - timedelta(hours=1)
    c.growth_rate = 0.1
    c.parameters["stress_decrease_delay_hrs"] = 99
    assert not c.is_time_to_rescue(verbose=True), "Expected False when last dilution is too recent"

    # Test case 4: latest_t_doubling is positive and below threshold
    c.last_dilution_time = datetime.now() - timedelta(hours=100)
    c.growth_rate = 0.1
    c.parameters["stress_decrease_delay_hrs"] = 99
    c.parameters["stress_decrease_tdoubling_min_hrs"] = 10
    assert not c.is_time_to_rescue(verbose=True), "Expected False when latest_t_doubling is positive and below threshold"

    # Test case 5: latest_t_doubling is negative or above threshold
    c.last_dilution_time = datetime.now() - timedelta(hours=100)
    c.growth_rate = 0.1
    c.parameters["stress_decrease_delay_hrs"] = 99
    c.parameters["stress_decrease_tdoubling_min_hrs"] = 5
    assert c.is_time_to_rescue(verbose=True), "Expected True when latest_t_doubling is negative or above threshold"

    print("All tests passed!")
# test_is_time_to_rescue()
#%%
def test_is_time_to_increase_stress():
    # Test Case 1: last_dilution_time is None
    c.last_dilution_time = None
    c.growth_rate = 0.1
    c.last_stress_increase_generation = 2
    assert not c.is_time_to_increase_stress(verbose=True)

    # Test Case 2: growth_rate is None
    c.last_dilution_time = datetime.now() - timedelta(hours=1)
    c.growth_rate = None
    c.last_stress_increase_generation = 2
    assert not c.is_time_to_increase_stress(verbose=True)

    # Test Case 3: last_stress_increase_generation is None
    c.last_dilution_time = datetime.now() - timedelta(hours=1)
    c.growth_rate = 0.1
    c.last_stress_increase_generation = None
    assert not c.is_time_to_increase_stress(verbose=True)

    # Test Case 4: generation is not greater than stress_increase_delay_generations
    c.generation = 1
    c.parameters["stress_increase_delay_generations"] = 2
    assert not c.is_time_to_increase_stress(verbose=True)

    # Test Case 5: growth_rate is not positive
    c.generation = 3
    c.growth_rate = -0.1
    assert not c.is_time_to_increase_stress(verbose=True)

    # Test Case 6: generation - last_stress_increase_generation is not greater than stress_increase_delay_generations
    c.growth_rate = 0.1
    c.last_stress_increase_generation = 1
    assert not c.is_time_to_increase_stress(verbose=True)

    # Test Case 7: latest_t_doubling is not above threshold
    c.last_stress_increase_generation = 0
    c.growth_rate = np.log(2) / c.parameters["stress_increase_tdoubling_max_hrs"]
    assert not c.is_time_to_increase_stress(verbose=True)

    # Test Case 8: all conditions met
    c.growth_rate = np.log(2) / (c.parameters["stress_increase_tdoubling_max_hrs"] - 1)
    assert c.is_time_to_increase_stress(verbose=True)

    print("All tests passed!")
# test_is_time_to_increase_stress()
#%%
# c.generation
for v in range(1,8):
    c = exp.cultures[v]
#%%
def object_to_dict(obj):
    if not hasattr(obj, "__dict__"):
        return repr(obj)
    result = {}

    for key, value in obj.__dict__.items():
        if isinstance(value, dict):
            # if the value is a dictionary, we represent it as a multi-line string
            value = '\n'.join([f'{k}: {v}' for k, v in value.items()])
        else:
            value = repr(value)  # Otherwise, we use repr to get a string representation of the attribute value
        result[key] = value
    return result


from pprint import pprint, pformat
pprint(object_to_dict(c.experiment))
#%%
exp.model.parameters["cultures"]["1"]["description"] = "lalala"
db.session.commit()
#%%
exp.model.parameters
#%%
db.session.get(ExperimentModel, id)
