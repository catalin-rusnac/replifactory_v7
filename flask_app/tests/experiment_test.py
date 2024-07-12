from experiment.experiment import Experiment
import time
from flask import Flask

from minimal_device.base_device import BaseDevice
dev = BaseDevice()
# dev.connect()
# dev.hello()
from experiment.database_models import ExperimentModel, db
import os

def create_test_app():
    app = Flask(__name__)

    script_dir = os.path.dirname(os.getcwd())
    db_path = os.path.join(script_dir, 'replifactory_v7/db/replifactory.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    db.init_app(app)
    with app.app_context():
        db.create_all()
    return app

# Create test app and keep the context for further use
app = create_test_app()
ctx = app.app_context()
ctx.push()  # This enters the application context

experiment_model = db.session.get(ExperimentModel, 2)
print(experiment_model)
app.experiment = Experiment(dev, experiment_model, db)
#%%
app.experiment.device.hello()
#%%
experiment.cultures[6].update()
#%%
experiment.cultures[7].update()
#%%
experiment.cultures[7].get_first_od_timestamp()
#%%
experiment.start()
#%%
experiment.stop()
#%%
experiment.pause_dilution_worker()
#%%
#%%
experiment_model = db.session.get(ExperimentModel, 2)
experiment = Experiment(dev, experiment_model)


#%%
#%%
#%%

#%%
experiment.locks[1].locked()
# experiment.attempt_dilute_in_background(vial_number=7, main_pump_volume=0, drug_pump_volume=0)
# experiment_worker.start()
#%%
# experiment.attempt_dilute_in_background(vial_number=7, main_pump_volume=0, drug_pump_volume=0)
print("las")
#%%
# experiment.attempt_dilute_in_background(vial_number=7, main_pump_volume=0, drug_pump_volume=0)
# experiment.measure_od_in_background()

#%%
for v in range(1,8):
    dev.stirrers.set_speed(v, "stopped")
#%%
from minimal_device.od_sensor import measure_od_all
print(measure_od_all(device=dev))

#%%
experiment_worker.pause()
#%%
experiment_worker.stop()
#%%
# Keep the experiment worker running for a while
time.sleep(10)

# Pause the experiment worker
experiment_worker.pause()
time.sleep(5)

# Resume the experiment worker
experiment_worker.resume()
time.sleep(5)

# Stop the experiment worker
experiment_worker.stop()
