from datetime import datetime, timedelta

from experiment.experiment import Experiment
import time

from flask import Flask

from minimal_device.base_device import BaseDevice

dev = None

dev = BaseDevice()
dev.connect()

from experiment.database_models import ExperimentModel, db
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

experiment_model = db.session.get(ExperimentModel, 5)
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

# experiment.start()
#%%
# experiment.stop()
#%%
print([experiment.cultures[v].drug_concentration for v in range(1,8)])
#%%
db.session.commit()
#%%
#%%

#%%
# experiment.start()
#%%
# experiment._delete_all_data()
for c in experiment.cultures.values():
    c.parameters["volume_added"] = 0.2
#%%
# experiment.stop()
#%%
from pprint import pprint
pprint(c.parameters.__dict__)
pprint(str(c.experiment.get_status()).replace("'", '').replace('"', ''))

#%%
with app.app_context():
    c.get_latest_data_from_db()
    print(c.parameters)
    print(c.parameters)
    c.update()
pprint(c.__dict__)
pprint(c.get_status())
[c.experiment.device.stirrers.set_speed(v,"stopped") for v in range(1, 8)]

c.update()