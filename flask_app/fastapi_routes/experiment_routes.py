from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from experiment.database_models import ExperimentModel
from fastapi_db import get_db
from experiment.experiment_manager import experiment_manager
from pydantic import BaseModel
import copy
from experiment.database_models import ExperimentModel
from fastapi import Request

router = APIRouter()

class ExperimentCreate(BaseModel):
    name: str
    parameters: dict = {}

class ExperimentOut(BaseModel):
    id: int
    name: str
    status: str
    parameters: dict

    model_config = {"from_attributes": True}

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
    return ExperimentOut.model_validate(experiment)

@router.put("/experiments/select", response_model=SelectExperimentOut)
def select_experiment(
    data: SelectExperimentIn,
    db: Session = Depends(get_db)
):
    experiment_model = db.query(ExperimentModel).get(data.experiment_id)
    if not experiment_model:
        raise HTTPException(status_code=404, detail="Experiment not found")
    already_selected = experiment_manager.get_current_experiment_id() == data.experiment_id
    if not already_selected:
        experiment_manager.set_current_experiment(data.experiment_id)
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
):
    experiment = experiment_manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    return ExperimentOut.model_validate(experiment)

class SetCurrentExperimentIn(BaseModel):
    experiment_id: int

@router.post("/experiments/current", status_code=status.HTTP_204_NO_CONTENT)
def set_current_experiment(
    data: SetCurrentExperimentIn,
    db: Session = Depends(get_db),
):
    experiment_model = db.query(ExperimentModel).get(data.experiment_id)
    if experiment_model is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    experiment_manager.set_current_experiment(data.experiment_id)
    return

@router.get("/experiment/current", response_model=Optional[ExperimentOut])
def get_current_experiment_singular(
    db: Session = Depends(get_db),
):
    experiment = experiment_manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    return ExperimentOut.model_validate(experiment)

@router.put("/experiments/current/status")
def update_experiment_status(
    payload: dict,
    db: Session = Depends(get_db),
):
    status = payload['status']
    print("Updating experiment status to", status)
    if status == 'running':
        print("Checking if another experiment is running or paused")
        running_experiment = db.query(ExperimentModel).filter(ExperimentModel.status == 'running').first()
        if running_experiment:
            print("Another experiment is running, with id", running_experiment.id, "To start new experiment, stop the other one first")
            return {"error": "Cannot start experiment, another experiment is running", "experiment_id": running_experiment.id}
    experiment = experiment_manager.get_current_experiment()
    if experiment:
        if status == 'stopped':
            experiment.stop()
            return {"message": "Experiment stopped"}
        device = experiment_manager.get_device()
        if device is None or not device.is_connected():
            try:
                experiment_manager.connect_device()
            except Exception as e:
                return {"error": "device not connected"}, 400

        if status == 'running':
            print("Starting experiment")
            experiment.start()
            return {"message": "Experiment started"}
        
    else:
        return {"error": "Experiment not found"}, 404

@router.get("/experiments/selected", response_model=Optional[int])
def get_selected_experiment_id():
    return experiment_manager.get_current_experiment_id()

@router.get("/experiments/{id}", response_model=ExperimentOut)
def get_experiment_by_id(id: int, db: Session = Depends(get_db)):
    experiment_model = db.query(ExperimentModel).get(id)
    if not experiment_model:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentOut.model_validate(experiment_model)

@router.get("/experiments/current/parameters")
def get_current_experiment_parameters(
    db: Session = Depends(get_db),
):
    experiment = experiment_manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    return experiment.parameters or {}

@router.put("/experiments/current/parameters")
def update_current_experiment_parameters(
    parameters: dict = Body(...),
    db: Session = Depends(get_db),
):
    experiment = experiment_manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    if "parameters" in parameters and len(parameters) == 1:
        parameters = parameters["parameters"]
    experiment.parameters = parameters
    return {"message": "Parameters updated", "parameters": experiment.parameters}

@router.get("/experiments/current/growth_parameters")
def get_current_experiment_growth_parameters(
    db: Session = Depends(get_db),
):
    experiment = experiment_manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    return experiment.parameters.get("growth_parameters", {})

@router.put("/experiments/current/growth_parameters")
def update_current_experiment_growth_parameters(
    growth_parameters: dict = Body(...),
    db: Session = Depends(get_db),
):
    experiment = experiment_manager.get_current_experiment()
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
):
    experiment = experiment_manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    try:
        fig = experiment.cultures[vial].plot_predicted()
        return fig.to_plotly_json()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plot/{vial}")
def get_culture_plot(
    vial: int,
    db: Session = Depends(get_db),
):
    experiment = experiment_manager.get_current_experiment()
    if experiment is None:
        raise HTTPException(status_code=404, detail="No current experiment set")
    try:
        fig = experiment.cultures[vial].plot_data()
        return fig.to_plotly_json()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
