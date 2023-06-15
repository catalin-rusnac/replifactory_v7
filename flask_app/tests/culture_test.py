from datetime import datetime, timedelta

from experiment.experiment import Experiment
import time

from flask import Flask

from minimal_device.base_device import BaseDevice

dev = None

# dev = BaseDevice()
# dev.connect()

from experiment.models import ExperimentModel, db
import os

from flask_app.server import create_app
app = create_app()
ctx = app.app_context()
ctx.push()

def create_test_app():
    app = Flask(__name__)

    script_dir = os.path.dirname(__file__)
    print(os.path.abspath(script_dir),"script_dir")
    db_path = os.path.join(os.path.abspath(script_dir), './db/replifactory.db')
    print(os.path.abspath(db_path),"db_path")
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    db.init_app(app)
    with app.app_context():
        db.create_all()
    return app

experiment_model = db.session.get(ExperimentModel, 2)
if experiment_model is None:
    experiment_model = ExperimentModel(name="test_experiment")
    db.session.add(experiment_model)
    db.session.commit()
experiment = Experiment(dev, experiment_model, db)
c = experiment.cultures[2]
#%%
# print(c.is_time_to_dilute())

# c.increase_stress()
#%%
#%%

#%%
# c.get_latest_data_from_db()
print(c.parameters)
#%%
with experiment.app.app_context():
    print(db.session.get(ExperimentModel, c.experiment.model.id).parameters)
#%%

experiment.start()
#%%
experiment.stop()
#%%
print([experiment.cultures[v].drug_concentration for v in range(1,8)])
#%%
db.session.commit()
#%%
#%%

#%%
experiment.start()
#%%
# experiment._delete_all_data()
for c in experiment.cultures.values():
    c.parameters["volume_added"] = 0.2
#%%
experiment.stop()
#%%
from pprint import pprint
pprint(c.parameters.__dict__)
pprint(str(c.experiment.get_info()).replace("'", '').replace('"', ''))
#%%
import random

for i in range(3):
    c.od = random.choice([None,0.1, 1])
    c.growth_rate = random.choice([None,0.1, 25])
    c.drug_concentration = random.choice([0, 12])
    c.generation = random.choice([0, 1, 12])
    c.last_stress_increase_generation = random.choice([None, 0.1, 12])
    c.last_dilution_time = random.choice([None, datetime.now(), datetime.now() - timedelta(hours=1), datetime.now() - timedelta(hours=2), datetime.now() - timedelta(hours=30)])
    c.is_time_to_dilute(verbose=True)
    c.is_time_to_increase_stress(verbose=True)
    c.is_time_to_rescue(verbose=True)
    c.calculate_generation_concentration_after_dil(1,9)
    c.calculate_pump_volumes(19)
    c.calculate_pump_volumes(0)
    c.calculate_pump_volumes(110)
print("done")
