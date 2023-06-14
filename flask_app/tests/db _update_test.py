from datetime import datetime, timedelta

import numpy as np

from experiment.experiment import Experiment
from experiment.models import ExperimentModel, db
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
experiment_model.parameters["cultures"]["1"]["name"] = "test"
experiment_model.parameters

db.session.commit()

experiment_model.parameters

#%%
from copy import deepcopy
params = deepcopy(experiment_model.parameters)

# Update the field
params["cultures"]["1"]["name"] = "test"

# Assign the updated parameters back to the model
experiment_model.parameters = params
# Commit the session
db.session.commit()
#%%
experiment_model.parameters
