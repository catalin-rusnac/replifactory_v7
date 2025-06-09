from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from experiment.experiment_manager import experiment_manager
from experiment.exceptions import ExperimentNotFound
from routers.experiment_schemas import ExperimentCreate, ExperimentOut, SelectExperimentIn, ParametersUpdate
from logger.logger import logger
import traceback
from fastapi import WebSocket, WebSocketDisconnect

router = APIRouter()
get_db = experiment_manager.get_db

@router.get("/experiments", response_model=List[ExperimentOut])
def get_experiments(db_session: Session = Depends(get_db)):
    """Get all experiments"""
    experiments = experiment_manager.get_all_experiments(db_session=db_session)
    return [ExperimentOut.model_validate(exp) for exp in experiments]

@router.post("/experiments", response_model=ExperimentOut)
def create_experiment(data: ExperimentCreate, db_session: Session = Depends(get_db)):
    """Create a new experiment"""
    try:
        experiment = experiment_manager.create_experiment(name=data.name, db_session=db_session)
        response = ExperimentOut.model_validate(experiment.model)
        return response
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/experiments", response_model=Optional[ExperimentOut])
def select_experiment(data: SelectExperimentIn, db_session: Session = Depends(get_db)):
    """Select an experiment"""
    try:
        experiment_manager.select_experiment(data.experiment_id, db_session)
        experiment = experiment_manager.experiment
        if experiment is None:
            return None        
        return ExperimentOut.model_validate(experiment.model)
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experiments/current", response_model=Optional[ExperimentOut])
def get_current_experiment(db_session: Session = Depends(get_db)):
    """Get the current experiment"""
    if experiment_manager.experiment is None:
        return None
    try:
        experiment = experiment_manager.experiment
        return ExperimentOut.model_validate(experiment.model)
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/experiments/current/status")
def update_experiment_status(payload: dict, db_session: Session = Depends(get_db)):
    """Update the status of the current experiment (start/stop)"""
    status = payload['status']
    try:
        result = experiment_manager.update_experiment_status(status, db_session=db_session)
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        return result
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/experiments/{experiment_id}/parameters")
def get_experiment_parameters(experiment_id: int, db_session: Session = Depends(get_db)):
    """Get the parameters of an experiment"""
    experiment = experiment_manager.get_experiment_by_id(experiment_id, db_session=db_session)
    return experiment.model.parameters

@router.put("/experiments/current/parameters")
def update_parameters(payload: ParametersUpdate, db_session: Session = Depends(get_db)):
    """Update the control parameters of the current experiment"""
    try:
        params = experiment_manager.update_current_experiment_parameters(payload.parameters, db_session=db_session)
        return {"message": "Control parameters updated", "parameters": params}
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experiments/current/growth_parameters")
def get_current_experiment_growth_parameters(db_session: Session = Depends(get_db)):
    """Get the growth parameters of the current experiment"""
    try:
        params = experiment_manager.get_current_experiment_growth_parameters(db_session=db_session)
        return {"message": "Growth parameters fetched", "growth_parameters": params}
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/experiments/current/growth_parameters")
def update_current_experiment_growth_parameters(growth_parameters: dict = Body(...), db_session: Session = Depends(get_db)):
    """Update the growth parameters of the current experiment"""
    try:
        params = experiment_manager.update_current_experiment_growth_parameters(growth_parameters, db_session=db_session)
        return {"message": "Growth parameters updated", "growth_parameters": params}
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/plot/{vial}/simulation")
def get_culture_predicted_plot(vial: int, db_session: Session = Depends(get_db)):
    try:
        experiment = experiment_manager.experiment
        logger.info(f"Plotting predicted plot for culture {vial}")
        fig = experiment.cultures[vial].plot_predicted()
        return fig.to_plotly_json()
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error plotting predicted plot for culture {vial}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plot/{vial}")
def get_culture_plot(vial: int, db_session: Session = Depends(get_db)):
    try:
        experiment = experiment_manager.experiment
        fig = experiment.cultures[vial].plot_data()
        return fig.to_plotly_json()
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    experiment_manager.active_sockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        experiment_manager.active_sockets.discard(websocket)