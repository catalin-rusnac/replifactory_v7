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

@router.put("/cultures/{vial}/run-simulation")
def run_simulation(vial: int, simulation_hours: int = 48, db_session: Session = Depends(get_db)):
    """Run a simulation of the current experiment"""
    # Validate simulation hours
    if simulation_hours < 1:
        raise HTTPException(status_code=400, detail="Simulation hours must be at least 1")
    if simulation_hours > 240:
        raise HTTPException(status_code=400, detail="Simulation hours cannot exceed 240 (10 days)")
    
    try:
        experiment = experiment_manager.experiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        experiment.cultures[vial].run_and_save_simulation(simulation_hours=simulation_hours)
        culture = experiment.cultures[vial]
        pump1_volume_used = sum(culture.culture_growth_model.pump1_volumes)
        pump2_volume_used = sum(culture.culture_growth_model.pump2_volumes)
        waste_medium_volume_created = sum(culture.culture_growth_model.waste_medium_created)
        summary_data = {
            "initial_population": culture.culture_growth_model.initial_population,
            "final_population": culture.culture_growth_model.population[-1] if culture.culture_growth_model.population else None,
            "final_effective_growth_rate": culture.culture_growth_model.effective_growth_rates[-1][0] if culture.culture_growth_model.effective_growth_rates else None,
            "final_dose": culture.culture_growth_model.doses[-1][0] if culture.culture_growth_model.doses else None,
            "final_generation": culture.culture_growth_model.generations[-1][0] if culture.culture_growth_model.generations else None,
            "initial_ic50": culture.culture_growth_model.ic50_initial,
            "final_ic50": culture.culture_growth_model.ic50s[-1][0] if culture.culture_growth_model.ic50s else None,
            "pump1_volume_used": pump1_volume_used,
            "pump2_volume_used": pump2_volume_used,
            "waste_medium_volume_created": waste_medium_volume_created,
        }
        return {"message": "Simulation run", "summary_data": summary_data}
    except Exception as e:
        # Format error message nicely with full traceback
        error_type = type(e).__name__
        full_traceback = traceback.format_exc()
        # Extract the relevant line from traceback
        traceback_lines = full_traceback.split('\n')
        code_line = ""
        error_line = ""
        
        for i, line in enumerate(traceback_lines):
            if "only_pump1_resulting_dose" in line and "=" in line:
                code_line = line  # Don't strip to preserve alignment
                # Get the next line if it has the caret
                if i + 1 < len(traceback_lines) and "^" in traceback_lines[i + 1]:
                    error_line = traceback_lines[i + 1]
                break
        
        if code_line and error_line:
            error_msg = f"Simulation Error ({error_type})\n\n{code_line}\n{error_line}\n{error_type}: {str(e)}\n\nPlease adjust parameters and try again."
        else:
            error_msg = f"Simulation Error ({error_type})\n\n{str(e)}\n\nPlease adjust parameters and try again."
            
        logger.error(f"Error running simulation for culture {vial}: {e}")
        logger.error(full_traceback)
        raise HTTPException(status_code=500, detail=error_msg)
@router.get("/plot/{vial}/simulation")
def get_culture_predicted_plot(vial: int, simulation_hours: int = 48, db_session: Session = Depends(get_db)):
    # Validate simulation hours
    if simulation_hours < 1:
        raise HTTPException(status_code=400, detail="Simulation hours must be at least 1")
    if simulation_hours > 240:
        raise HTTPException(status_code=400, detail="Simulation hours cannot exceed 240 (10 days)")
    
    try:
        experiment = experiment_manager.experiment
        logger.info(f"Plotting predicted plot for culture {vial}")
        fig = experiment.cultures[vial].plot_predicted(rerun=True, simulation_hours=simulation_hours)
        return fig.to_plotly_json()
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Format error message nicely with full traceback
        error_type = type(e).__name__
        full_traceback = traceback.format_exc()
        # Extract the relevant line from traceback
        traceback_lines = full_traceback.split('\n')
        code_line = ""
        error_line = ""
        
        for i, line in enumerate(traceback_lines):
            if "only_pump1_resulting_dose" in line and "=" in line:
                code_line = line  # Don't strip to preserve alignment
                # Get the next line if it has the caret
                if i + 1 < len(traceback_lines) and "^" in traceback_lines[i + 1]:
                    error_line = traceback_lines[i + 1]
                break
        
        if code_line and error_line:
            error_msg = f"Plot Error ({error_type})\n\n{code_line}\n{error_line}\n{error_type}: {str(e)}\n\nPlease adjust parameters and try again."
        else:
            error_msg = f"Plot Error ({error_type})\n\n{str(e)}\n\nPlease adjust parameters and try again."
            
        logger.error(f"Error plotting predicted plot for culture {vial}: {e}")
        logger.error(full_traceback)
        raise HTTPException(status_code=500, detail=error_msg)

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

@router.get("/experiments/current/summary")
def get_experiment_summary(db_session: Session = Depends(get_db)):
    """Get a summary of the current experiment status and recent activity"""
    try:
        if experiment_manager.experiment is None:
            raise HTTPException(status_code=404, detail="No current experiment selected")
        
        experiment = experiment_manager.experiment
        summary_data = {}
        
        # Get RPM stats for all vials efficiently in one query
        from experiment.culture import Culture
        rpm_stats_all_vials = Culture.get_all_vials_rpm_stats_1h(
            experiment.model.id, 
            db_session
        )
        
        # Calculate summary for each vial (1-7)
        for vial_id in range(1, 8):
            if vial_id not in experiment.cultures:
                # Vial not configured
                summary_data[f'vial{vial_id}'] = {
                    'last_od': None,
                    'od_timestamp': None,
                    'growth_rate': None,
                    'rpm_mean_1h': None,
                    'rpm_std_1h': None,
                    'medium_used_1h': None,
                    'medium_used_24h': None,
                    'drug_used_1h': None,
                    'drug_used_24h': None,
                    'total_dilutions': None,
                    'last_dilution': None,
                    'runtime': None,
                    'current_concentration': None
                }
                continue
                
            culture = experiment.cultures[vial_id]
            
            # Get latest data from culture
            latest_od = culture.get_latest_od()
            growth_rate = culture.get_current_growth_rate()
            dilution_count = culture.get_total_dilution_count()
            last_dilution_time = culture.get_last_dilution_time()
            runtime = culture.get_runtime()
            medium_1h, drug_1h = culture.get_volume_usage_1h()
            medium_24h, drug_24h = culture.get_volume_usage_24h()
            
            # Get RPM stats from the efficient query result
            rpm_stats = rpm_stats_all_vials.get(vial_id, {'mean': None, 'std': None})
            
            summary_data[f'vial{vial_id}'] = {
                'last_od': latest_od['value'] if latest_od else None,
                'od_timestamp': latest_od['timestamp'] if latest_od else None,
                'growth_rate': growth_rate,
                'rpm_mean_1h': rpm_stats['mean'],
                'rpm_std_1h': rpm_stats['std'],
                'medium_used_1h': medium_1h,
                'medium_used_24h': medium_24h,
                'drug_used_1h': drug_1h,
                'drug_used_24h': drug_24h,
                'total_dilutions': dilution_count,
                'last_dilution': last_dilution_time,
                'runtime': runtime,
                'current_concentration': culture.drug_concentration
            }
        
        return {"summary": summary_data}
        
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting experiment summary: {e}")
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