from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from experiment.database_models import ExperimentModel
from fastapi_db import get_db
from experiment.experiment_manager import ExperimentManager
from pydantic import BaseModel
from threading import Lock
from fastapi.middleware.cors import CORSMiddleware
import copy

router = APIRouter()

# Singleton manager instance
global_experiment_manager = ExperimentManager()

def get_experiment_manager():
    return global_experiment_manager

class ExperimentCreate(BaseModel):
    name: str
    parameters: dict = {}

class ExperimentOut(BaseModel):
    id: int
    name: str
    status: str
    parameters: dict

    class Config:
        from_attributes = True

class SelectExperimentIn(BaseModel):
    experiment_id: int

class SelectExperimentOut(BaseModel):
    success: bool
    selected_experiment_id: int

@router.post("/experiments", response_model=ExperimentOut)
def create_experiment(data: ExperimentCreate, db: Session = Depends(get_db)):
    experiment = ExperimentModel(name=data.name, parameters=data.parameters)
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return ExperimentOut.from_orm(experiment)

@router.put("/experiments/select", response_model=SelectExperimentOut)
def select_experiment(
    data: SelectExperimentIn,
    db: Session = Depends(get_db)
):
    manager = ExperimentManager.get_instance()
    experiment_model = db.query(ExperimentModel).get(data.experiment_id)
    if not experiment_model:
        raise HTTPException(status_code=404, detail="Experiment not found")
    already_selected = manager.get_current_experiment_id() == data.experiment_id
    if not already_selected:
        manager.set_current_experiment(data.experiment_id)
    return SelectExperimentOut(success=True, selected_experiment_id=data.experiment_id)

@router.get("/experiments", response_model=List[ExperimentOut])
def get_experiments(db: Session = Depends(get_db)):
    try:
        experiment_models = db.query(ExperimentModel).all()
    except Exception:
        raise HTTPException(status_code=500, detail="Database not initialized")
    experiments_clean = [ExperimentOut(id=0, name="---- default template ----", status="stopped", parameters={})]
    for experiment_model in experiment_models:
        experiments_clean.append(ExperimentOut(id=experiment_model.id, name=experiment_model.name, status=experiment_model.status, parameters=experiment_model.parameters or {}))
    return experiments_clean

@router.get("/experiments/current", response_model=Optional[ExperimentOut])
def get_current_experiment(
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment()
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
    experiment_model = db.query(ExperimentModel).get(data.experiment_id)
    if experiment_model is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    manager.set_current_experiment(data.experiment_id)
    return

@router.get("/experiment/current", response_model=Optional[ExperimentOut])
def get_current_experiment_singular(
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    return ExperimentOut.from_orm(experiment)

class UpdateExperimentStatusIn(BaseModel):
    status: str

@router.put("/experiments/current/status")
def update_experiment_status(
    data: UpdateExperimentStatusIn,
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if data.status not in {"running", "paused", "stopped"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    # Only one experiment can be running or paused at a time
    if data.status == "running":
        running_experiment = db.query(ExperimentModel).filter(ExperimentModel.status == "running").first()
        if running_experiment and running_experiment.id != experiment.id:
            raise HTTPException(status_code=400, detail=f"Cannot start experiment, another experiment is already running (id={running_experiment.id})")
        paused_experiment = db.query(ExperimentModel).filter(ExperimentModel.status == "paused").first()
        if paused_experiment and paused_experiment.id != experiment.id:
            raise HTTPException(status_code=400, detail=f"Cannot start experiment, another experiment is paused (id={paused_experiment.id})")
    # Update status
    experiment.status = data.status
    db.commit()
    return {"message": f"Experiment status updated to {data.status}"}


@router.get("/experiments/selected", response_model=Optional[int])
def get_selected_experiment_id(manager: ExperimentManager = Depends(get_experiment_manager)):
    return manager.get_current_experiment_id()

@router.get("/experiments/{id}", response_model=ExperimentOut)
def get_experiment_by_id(id: int, db: Session = Depends(get_db)):
    experiment_model = db.query(ExperimentModel).get(id)
    if not experiment_model:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentOut.from_orm(experiment_model)

@router.get("/experiments/current/parameters")
def get_current_experiment_parameters(
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    return experiment.parameters or {}

@router.put("/experiments/current/parameters")
def update_current_experiment_parameters(
    parameters: dict = Body(...),
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    if "parameters" in parameters and len(parameters) == 1:
        parameters = parameters["parameters"]
    experiment.parameters = parameters
    return {"message": "Parameters updated", "parameters": experiment.parameters}

@router.get("/experiments/current/growth_parameters")
def get_current_experiment_growth_parameters(
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    return experiment.parameters.get("growth_parameters", {})

@router.put("/experiments/current/growth_parameters")
def update_current_experiment_growth_parameters(
    growth_parameters: dict = Body(...),
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    new_parameters = copy.deepcopy(experiment.parameters)
    new_parameters["growth_parameters"] = growth_parameters
    experiment.parameters = new_parameters
    return {"message": "Growth parameters updated", "growth_parameters": experiment.parameters["growth_parameters"]}


@router.get("/plot/{vial}/simulation")
def get_culture_predicted_plot(
    vial: int,
    db: Session = Depends(get_db),
    manager: ExperimentManager = Depends(get_experiment_manager)
):
    experiment = manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    try:
        fig = experiment.cultures[vial].plot_predicted()
        return fig.to_plotly_json()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

