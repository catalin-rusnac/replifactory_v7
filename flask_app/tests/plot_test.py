import time
from datetime import datetime, timedelta

import experiment.plot
from experiment.experiment import Experiment

dev = None

from experiment.database_models import ExperimentModel, db
import os

from flask_app.server import create_app
app = create_app()
ctx = app.app_context()
ctx.push()

experiment_model = db.session.get(ExperimentModel, 2)
exp = Experiment(dev, experiment_model, db)
c = exp.cultures[2]
#%%
import pandas as pd
df=pd.read_csv(r"C:\Users\crusnac\Dropbox\IST\replifactory_v5\data\Cobalt_300922\vial_1\od.csv")
dosedf=pd.read_csv(r"C:\Users\crusnac\Dropbox\IST\replifactory_v5\data\Cobalt_300922\vial_1\medium2_concentration.csv")
gendf = pd.read_csv(r"C:\Users\crusnac\Dropbox\IST\replifactory_v5\data\Cobalt_300922\vial_1\log2_dilution_coefficient.csv")
print(df.od[0])
#%%
# c._delete_all_records()
t0=time.time()
for i in range(df.shape[0]):
    t = datetime.fromtimestamp(df.time[i])
    od = df.od[i]
    c._log_testing_od(od, timestamp=t)
    if i%10==0:
        print(i,time.time()-t0,end="\r")
# ods=c.get_last_ods()
# print(ods)
#%%
for i in range(dosedf.shape[0]):
    t = datetime.fromtimestamp(gendf.time[i])
    c._log_testing_generation(generation=gendf.log2_dilution_coefficient[i],
                              concentration=dosedf.medium2_concentration[i],
                              timestamp=t)
#%%

import experiment.plot
import importlib
#%%
importlib.reload(experiment)
importlib.reload(experiment.plot)
from experiment.plot import plot_culture

t0=time.time()
plot_culture(c).show()
# print(plot_culture(c).to_json())
# print(time.time()-t0)
#%%
culture = c
limit = 100
gens, concs = culture.get_last_generations(limit=limit)
print(gens)

# c.calculate_generation_concentration_after_dil(1,9)
#%%
c.is_time_to_dilute()
#%%
from pprint import pprint
pprint(c.__dict__)
