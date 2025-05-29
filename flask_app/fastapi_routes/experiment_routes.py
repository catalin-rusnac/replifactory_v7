from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from experiment.database_models import ExperimentModel
from fastapi_db import get_db
from experiment.experiment_manager import ExperimentManager
from pydantic import BaseModel

router = APIRouter()

# Singleton manager instance
global_experiment_manager = ExperimentManager()

def get_experiment_manager():
    return global_experiment_manager

class ExperimentOut(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        orm_mode = True

@router.get("/experiments", response_model=List[ExperimentOut])
def get_experiments(db: Session = Depends(get_db)):
    try:
        experiment_models = db.query(ExperimentModel).all()
    except Exception:
        raise HTTPException(status_code=500, detail="Database not initialized")
    experiments_clean = [ExperimentOut(id=0, name="---- default template ----", status="stopped")]
    for experiment_model in experiment_models:
        experiments_clean.append(ExperimentOut(id=experiment_model.id, name=experiment_model.name, status=experiment_model.status))
    return experiments_clean

@router.get("/experiments/current", response_model=Optional[ExperimentOut])
def get_current_experiment(
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment(db)
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    return ExperimentOut.from_orm(experiment)

class SetCurrentExperimentIn(BaseModel):
    experiment_id: int

@router.post("/experiments/current", status_code=status.HTTP_204_NO_CONTENT)
def set_current_experiment(
    data: SetCurrentExperimentIn,
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = db.query(ExperimentModel).get(data.experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    manager.set_current_experiment(data.experiment_id)
    return

# get current experiment
