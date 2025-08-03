from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from experiment.experiment_manager import experiment_manager
from experiment.exceptions import ExperimentNotFound
from routers.experiment_schemas import ExperimentCreate, ExperimentOut, SelectExperimentIn, ParametersUpdate
from logger.logger import logger
import traceback
import os
from fastapi import WebSocket, WebSocketDisconnect
import numpy as np
from datetime import datetime
from alternative_growth_rate import (
    analyze_growth_rate, 
    create_growth_rate_plot,
    calculate_summary_statistics,
    trim_data_by_od
)

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

@router.get("/plot/compare/{vials}/{metric}")
def get_culture_compare_plot(vials: str, metric: str, db_session: Session = Depends(get_db)):
    """Compare a specific metric across multiple vials"""
    vials = vials.split(',')
    vials = [int(vial) for vial in vials]
    
    # Validate metric
    valid_metrics = ['od', 'growth_rate', 'concentration', 'generation', 'rpm']
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Must be one of: {valid_metrics}")
    
    try:
        experiment = experiment_manager.experiment
        if experiment is None:
            raise HTTPException(status_code=404, detail="No current experiment selected")
        
        # Use the first available vial to call plot_compare
        available_vials = [v for v in vials if v in experiment.cultures]
        if not available_vials:
            raise HTTPException(status_code=404, detail="No valid vials found in current experiment")
            
        fig = experiment.cultures[available_vials[0]].plot_compare(vials, metric)
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

@router.get("/export/{vial}/{filetype}")
def export_vial_data(vial: int, filetype: str, db_session: Session = Depends(get_db)):
    """Export vial data as CSV or HTML"""
    if filetype not in ['csv', 'html']:
        raise HTTPException(status_code=400, detail="Invalid filetype. Must be 'csv' or 'html'")
    
    if vial < 1 or vial > 7:
        raise HTTPException(status_code=400, detail="Vial must be between 1 and 7")
    
    try:
        experiment = experiment_manager.experiment
        if experiment is None:
            raise HTTPException(status_code=404, detail="No current experiment selected")
        
        culture = experiment.cultures[vial]
        
        if filetype == 'csv':
            csv_path = culture.export_csv()
            if not os.path.exists(csv_path):
                raise HTTPException(status_code=500, detail="Failed to generate CSV file")
            
            logger.info(f"Exporting CSV for vial {vial}: {csv_path}")
            return FileResponse(
                path=csv_path,
                filename=f"vial_{vial}_data.csv",
                media_type="text/csv"
            )
            
        elif filetype == 'html':
            html_path = culture.export_plot_html()
            if not os.path.exists(html_path):
                raise HTTPException(status_code=500, detail="Failed to generate HTML file")
            
            logger.info(f"Exporting HTML for vial {vial}: {html_path}")
            return FileResponse(
                path=html_path,
                filename=f"vial_{vial}_plot.html",
                media_type="text/html"
            )
            
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Vial {vial} not found in current experiment")
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting {filetype} for vial {vial}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to export {filetype}: {str(e)}")

@router.get("/data/metric/{metric}")
def get_metric_data(metric: str, vials: str = None, limit: int = 1000, db_session: Session = Depends(get_db)):
    """Get specific metric data for comparison, optionally filtered by vials"""
    
    # Validate metric
    valid_metrics = ['od', 'growth_rate', 'concentration', 'generation', 'rpm']
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Must be one of: {valid_metrics}")
    
    try:
        experiment = experiment_manager.experiment
        if experiment is None:
            raise HTTPException(status_code=404, detail="No current experiment selected")
        
        # Parse vials if provided
        if vials:
            vial_list = [int(v) for v in vials.split(',')]
        else:
            vial_list = list(experiment.cultures.keys())
        
        metric_data = {}
        
        for vial in vial_list:
            if vial not in experiment.cultures:
                continue
                
            culture = experiment.cultures[vial]
            
            # Get data based on metric type
            if metric in ['od', 'growth_rate', 'rpm']:
                ods, mus, rpms = culture.get_last_ods_and_rpms(limit=limit)
                if metric == 'od':
                    data_dict = ods
                elif metric == 'growth_rate':
                    data_dict = mus
                else:  # rpm
                    data_dict = rpms
                    
            elif metric in ['concentration', 'generation']:
                gens, concs = culture.get_last_generations(limit=limit)
                if metric == 'generation':
                    data_dict = gens
                else:  # concentration
                    data_dict = concs
            
            # Convert timestamps to ISO format for JSON serialization
            serialized_data = {
                timestamp.isoformat(): value 
                for timestamp, value in data_dict.items()
            }
            
            metric_data[f'vial_{vial}'] = {
                'vial': vial,
                'data': serialized_data,
                'count': len(serialized_data)
            }
        
        return {
            'metric': metric,
            'vials': metric_data,
            'total_vials': len(metric_data)
        }
        
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting {metric} data: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/vials/available")
def get_available_vials(db_session: Session = Depends(get_db)):
    """Get list of available vials in current experiment"""
    try:
        experiment = experiment_manager.experiment
        if experiment is None:
            raise HTTPException(status_code=404, detail="No current experiment selected")
        
        available_vials = list(experiment.cultures.keys())
        vial_info = {}
        
        for vial in available_vials:
            culture = experiment.cultures[vial]
            # Get basic info about each vial
            latest_od = culture.get_latest_od()
            vial_info[vial] = {
                'vial': vial,
                'has_data': latest_od is not None,
                'last_measurement': latest_od['timestamp'].isoformat() if latest_od else None
            }
        
        return {
            'available_vials': sorted(available_vials),
            'vial_info': vial_info,
            'total_count': len(available_vials)
        }
        
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting available vials: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/growth-rate/advanced-analysis")
def advanced_growth_rate_analysis(payload: dict, db_session: Session = Depends(get_db)):
    """
    Advanced growth rate analysis with configurable parameters.
    
    Payload should contain:
    - vials: List of vial numbers to analyze
    - method: Analysis method ('adaptive', 'fixed', 'rolling')
    - window_size: Window size in hours (for fixed/rolling methods)
    - window_step: Step size in hours (for rolling method)
    - smoothing_method: Smoothing method ('median', 'moving_average', 'savgol', 'gaussian', 'none')
    - smoothing_window: Smoothing window size
    - enable_outlier_removal: Whether to remove outliers
    - enable_trimming: Whether to enable time-based data trimming
    - trim_settings: Dictionary with per-vial time trim settings
    - enable_od_trimming: Whether to enable OD-based data trimming
    - od_trim_settings: Dictionary with per-vial OD trim settings


    """
    try:
        if experiment_manager.experiment is None:
            raise HTTPException(status_code=404, detail="No current experiment selected")
        
        experiment = experiment_manager.experiment
        vials = payload.get('vials', [])
        
        if not vials:
            raise HTTPException(status_code=400, detail="No vials specified")
        
        # Extract analysis parameters
        method = payload.get('method', 'adaptive')
        model_type = payload.get('model_type', 'rolling')
        use_sliding_window = payload.get('use_sliding_window', False)
        window_size = payload.get('window_size', 3.0)
        window_step = payload.get('window_step', 0.5)
        smoothing_method = payload.get('smoothing_method', 'median')
        smoothing_window = payload.get('smoothing_window', 5)
        enable_outlier_removal = payload.get('enable_outlier_removal', False)
        outlier_threshold = payload.get('outlier_threshold', 3.0)
        outlier_window_size = payload.get('outlier_window_size', 5)
        enable_trimming = payload.get('enable_trimming', False)
        trim_settings = payload.get('trim_settings', {})
        enable_od_trimming = payload.get('enable_od_trimming', False)
        od_trim_settings = payload.get('od_trim_settings', {})
        use_real_time_simulation = payload.get('use_real_time_simulation', True)
        use_filtered_data = payload.get('use_filtered_data', False)


        
        # Validate method
        valid_methods = ['adaptive', 'fixed']
        if method not in valid_methods:
            raise HTTPException(status_code=400, detail=f"Invalid method. Must be one of: {valid_methods}")
        
        # Validate model type
        valid_model_types = ['rolling', 'logistic', 'gompertz', 'exponential']
        if model_type not in valid_model_types:
            raise HTTPException(status_code=400, detail=f"Invalid model type. Must be one of: {valid_model_types}")
        
        # Analyze each vial (sort vials to ensure consistent ordering)
        vials = sorted(vials, key=int)
        vial_results = {}
        summary_stats = {}
        
        for vial in vials:
            if vial not in experiment.cultures:
                logger.warning(f"Vial {vial} not found in current experiment")
                continue
                
            culture = experiment.cultures[vial]
            
            # Get OD data using the correct method
            od_dict, mu_dict, rpm_dict = culture.get_last_ods_and_rpms(limit=10000)
            if not od_dict or len(od_dict) < 3:
                logger.warning(f"Insufficient OD data for vial {vial}")
                continue
            
            # Extract time and OD arrays from dictionaries
            timestamps = list(od_dict.keys())
            od_values_list = list(od_dict.values())
            
            # Convert timestamps to Unix timestamps (float)
            time_data = np.array([float(ts.timestamp()) for ts in timestamps])
            od_values = np.array([float(od) for od in od_values_list])
            
            # Store original data
            original_time_data = time_data.copy()
            original_od_values = od_values.copy()
            
            # Apply filtering if use_filtered_data is True
            if use_filtered_data:
                # Apply per-vial time trimming if enabled
                if enable_trimming and str(vial) in trim_settings:
                    vial_trim = trim_settings[str(vial)]
                    start_time_str = vial_trim.get('start')
                    end_time_str = vial_trim.get('end')
                    
                    if start_time_str or end_time_str:
                        try:
                            from alternative_growth_rate import trim_data_by_time
                            time_data, od_values = trim_data_by_time(time_data, od_values, start_time_str, end_time_str)
                        except ValueError as e:
                            logger.warning(f"Time trimming failed for vial {vial}: {e}")
                
                # Apply per-vial OD trimming if enabled
                if enable_od_trimming and str(vial) in od_trim_settings:
                    vial_od_trim = od_trim_settings[str(vial)]
                    min_od_trim = vial_od_trim.get('min')
                    max_od_trim = vial_od_trim.get('max')
                    
                    if min_od_trim is not None or max_od_trim is not None:
                        try:
                            from alternative_growth_rate import trim_data_by_od
                            time_data, od_values = trim_data_by_od(time_data, od_values, min_od_trim, max_od_trim)
                        except ValueError as e:
                            logger.warning(f"OD trimming failed for vial {vial}: {e}")
                
                # Handle outliers if enabled
                if enable_outlier_removal:
                    from alternative_growth_rate import interpolate_outliers
                    time_data, od_values = interpolate_outliers(time_data, od_values, outlier_threshold, outlier_window_size)
                
                # Apply smoothing
                from alternative_growth_rate import smooth_data
                od_values = smooth_data(od_values, smoothing_method, smoothing_window)
            
            # Apply per-vial trimming parameters for analyze_growth_rate function
            start_time = None
            end_time = None
            if enable_trimming and str(vial) in trim_settings:
                vial_trim = trim_settings[str(vial)]
                start_time = vial_trim.get('start')
                end_time = vial_trim.get('end')
            
            # Apply per-vial OD trimming parameters for analyze_growth_rate function
            min_od = None
            max_od = None
            if enable_od_trimming and str(vial) in od_trim_settings:
                vial_od_trim = od_trim_settings[str(vial)]
                min_od = vial_od_trim.get('min')
                max_od = vial_od_trim.get('max')
            
            # Perform growth rate analysis
            # If use_filtered_data is True, pass 'none' for outlier handling since we already applied it
            outlier_handling = 'none' if use_filtered_data else ('interpolate' if enable_outlier_removal else 'none')
            growth_rate_results, summary = analyze_growth_rate(
                time_data=time_data,
                od_data=od_values,
                method=method,
                window_size=window_size,
                window_step=window_step,
                smoothing_method='none' if use_filtered_data else smoothing_method,  # Avoid double smoothing
                smoothing_window=smoothing_window,
                outlier_handling=outlier_handling,
                outlier_threshold=outlier_threshold,
                outlier_window_size=outlier_window_size,
                start_time=None if use_filtered_data else start_time,  # Avoid double trimming
                end_time=None if use_filtered_data else end_time,
                min_od=None if use_filtered_data else min_od,
                max_od=None if use_filtered_data else max_od,
                model_type=model_type,
                use_real_time_simulation=use_real_time_simulation,
                use_sliding_window=use_sliding_window
            )
            
            vial_results[vial] = {
                'growth_rate_results': growth_rate_results,
                'raw_time': original_time_data,
                'raw_od': original_od_values,
                'filtered_time': time_data if use_filtered_data else original_time_data,
                'filtered_od': od_values if use_filtered_data else original_od_values,
                'method_used': method,
                'parameters': {
                    'window_size': window_size,
                    'window_step': window_step,
                    'smoothing_method': smoothing_method,
                    'smoothing_window': smoothing_window,
                    'enable_outlier_removal': enable_outlier_removal,
                    'outlier_threshold': outlier_threshold,
                    'outlier_window_size': outlier_window_size,
                    'trimming_enabled': enable_trimming,
                    'start_time': start_time,
                    'end_time': end_time,
                    'od_trimming_enabled': enable_od_trimming,
                    'min_od': min_od,
                    'max_od': max_od,
                    'model_type': model_type
                }
            }
            
            summary_stats[vial] = summary
        
        if not vial_results:
            raise HTTPException(status_code=404, detail="No analyzable data found for selected vials")
        
        # Create plot
        plot_data = create_growth_rate_plot(vial_results)
        
        # Prepare response
        response_data = {
            'success': True,
            'method': method,
            'vials_analyzed': list(vial_results.keys()),
            'summary': summary_stats,
            'plot': plot_data,
            'parameters': {
                'method': method,
                'window_size': window_size,
                'window_step': window_step,
                'smoothing_method': smoothing_method,
                'smoothing_window': smoothing_window,
                'enable_outlier_removal': enable_outlier_removal,
                'outlier_threshold': outlier_threshold,
                'outlier_window_size': outlier_window_size,
                'enable_trimming': enable_trimming,
                'enable_od_trimming': enable_od_trimming,
                'model_type': model_type,
                'use_real_time_simulation': use_real_time_simulation
            }
        }
        
        # Add detailed results if requested
        if payload.get('include_detailed_results', False):
            response_data['detailed_results'] = vial_results
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in advanced growth rate analysis: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/growth-rate/filter-od-data")
def filter_od_data(payload: dict, db_session: Session = Depends(get_db)):
    """
    Filter and smooth OD data for visualization before growth rate analysis.
    
    Payload should contain:
    - vials: List of vial numbers to analyze
    - smoothing_method: Smoothing method ('median', 'moving_average', 'savgol', 'gaussian', 'none')
    - smoothing_window: Smoothing window size
    - enable_outlier_removal: Whether to enable outlier removal by interpolation
    - outlier_threshold: Z-score threshold for outlier detection (default: 3.0)
    - outlier_window_size: Rolling window size for outlier detection (default: 5)
    - enable_trimming: Whether to enable data trimming
    - trim_settings: Dictionary with per-vial trim settings
    """
    from alternative_growth_rate import (
        smooth_data, 
        remove_outliers, 
        trim_data_by_time
    )
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    try:
        if experiment_manager.experiment is None:
            raise HTTPException(status_code=404, detail="No current experiment selected")
        
        experiment = experiment_manager.experiment
        vials = payload.get('vials', [])
        
        if not vials:
            raise HTTPException(status_code=400, detail="No vials specified")
        
        # Sort vials to ensure consistent ordering
        vials = sorted(vials, key=int)
        
        # Extract filtering parameters
        smoothing_method = payload.get('smoothing_method', 'median')
        smoothing_window = payload.get('smoothing_window', 5)
        enable_outlier_removal = payload.get('enable_outlier_removal', False)
        outlier_threshold = payload.get('outlier_threshold', 3.0)
        outlier_window_size = payload.get('outlier_window_size', 5)
        enable_trimming = payload.get('enable_trimming', False)
        trim_settings = payload.get('trim_settings', {})
        enable_od_trimming = payload.get('enable_od_trimming', False)
        od_trim_settings = payload.get('od_trim_settings', {})
        
        # Process each vial
        vial_data = {}
        vial_colors = {
            1: '#1f77b4', 2: '#ff7f0e', 3: '#2ca02c', 4: '#d62728',
            5: '#9467bd', 6: '#8c564b', 7: '#e377c2'
        }
        
        for vial in vials:
            if vial not in experiment.cultures:
                logger.warning(f"Vial {vial} not found in current experiment")
                continue
                
            culture = experiment.cultures[vial]
            
            # Get OD data using the correct method
            od_dict, mu_dict, rpm_dict = culture.get_last_ods_and_rpms(limit=10000)
            if not od_dict or len(od_dict) < 3:
                logger.warning(f"Insufficient OD data for vial {vial}")
                continue
            
            # Extract time and OD arrays from dictionaries
            timestamps = list(od_dict.keys())
            od_values_list = list(od_dict.values())
            
            # Convert timestamps to Unix timestamps (float)
            time_data = np.array([float(ts.timestamp()) for ts in timestamps])
            od_values = np.array([float(od) for od in od_values_list])
            
            # Store original data
            original_time = time_data.copy()
            original_od = od_values.copy()
            
            # Apply per-vial time trimming if enabled
            if enable_trimming and str(vial) in trim_settings:
                vial_trim = trim_settings[str(vial)]
                start_time = vial_trim.get('start')
                end_time = vial_trim.get('end')
                
                if start_time or end_time:
                    try:
                        time_data, od_values = trim_data_by_time(time_data, od_values, start_time, end_time)
                    except ValueError as e:
                        logger.warning(f"Time trimming failed for vial {vial}: {e}")
                        raise HTTPException(status_code=400, detail=f"Vial {vial} time trimming failed: {str(e)}")
            
            # Apply per-vial OD trimming if enabled
            if enable_od_trimming and str(vial) in od_trim_settings:
                vial_od_trim = od_trim_settings[str(vial)]
                min_od = vial_od_trim.get('min')
                max_od = vial_od_trim.get('max')
                
                if min_od is not None or max_od is not None:
                    try:
                        time_data, od_values = trim_data_by_od(time_data, od_values, min_od, max_od)
                    except ValueError as e:
                        logger.warning(f"OD trimming failed for vial {vial}: {e}")
                        raise HTTPException(status_code=400, detail=f"Vial {vial} OD trimming failed: {str(e)}")
            
            # Store data before outlier removal for plotting
            time_data_before_outliers = time_data.copy()
            od_values_before_outliers = od_values.copy()
            
            # Handle outliers if enabled
            if enable_outlier_removal:
                from alternative_growth_rate import interpolate_outliers
                time_data, od_values = interpolate_outliers(time_data, od_values, outlier_threshold, outlier_window_size)
            
            # Check if we still have sufficient data after filtering
            if len(time_data) < 3:
                logger.warning(f"Insufficient data for vial {vial} after filtering: {len(time_data)} points")
                continue
            
            # Apply smoothing
            od_values_smooth = smooth_data(od_values, smoothing_method, smoothing_window)
            
            vial_data[vial] = {
                'original_time': original_time,
                'original_od': original_od,
                'outlier_corrected_time': time_data_before_outliers,
                'outlier_corrected_od': od_values_before_outliers,
                'after_outlier_time': time_data,
                'after_outlier_od': od_values,
                'filtered_time': time_data,
                'filtered_od': od_values_smooth,
                'color': vial_colors.get(vial, '#000000'),
                'data_points_original': len(original_time),
                'data_points_outlier_corrected': len(time_data_before_outliers),
                'data_points_after_outlier': len(time_data),
                'data_points_filtered': len(time_data)
            }
        
        if not vial_data:
            raise HTTPException(status_code=404, detail="No processable data found for selected vials")
        
        # Create plot showing original vs filtered data
        fig = go.Figure()
        
        for vial, data in vial_data.items():
            color = data['color']
            
            # Ensure we have data to plot
            if len(data['original_time']) == 0 or len(data['filtered_time']) == 0:
                continue
                
            # Convert timestamps to datetime objects for plotting
            original_datetimes = [datetime.fromtimestamp(ts) for ts in data['original_time']]
            filtered_datetimes = [datetime.fromtimestamp(ts) for ts in data['filtered_time']]
            
            # Original data (much more faint)
            if len(original_datetimes) > 0:
                fig.add_trace(go.Scatter(
                    x=original_datetimes,
                    y=data['original_od'],
                    mode='lines+markers',
                    name=f'Vial {vial} (Original)',
                    line=dict(color=color, width=1, dash='dot'),
                    marker=dict(size=2, opacity=0.3),
                    opacity=0.3
                ))
            
            # Filtered data (bold)
            if len(filtered_datetimes) > 0:
                fig.add_trace(go.Scatter(
                    x=filtered_datetimes,
                    y=data['filtered_od'],
                    mode='lines+markers',
                    name=f'Vial {vial} (Filtered)',
                    line=dict(color=color, width=3),
                    marker=dict(size=5)
                ))
        
        # Build title based on enabled filters
        title_parts = ["Original vs Processed OD Data"]
        filters_applied = []
        if enable_trimming:
            filters_applied.append("Time Trimmed")
        if enable_od_trimming:
            filters_applied.append("OD Trimmed")
        if enable_outlier_removal:
            filters_applied.append("Outliers Removed")
        if smoothing_method != 'none':
            filters_applied.append(f"{smoothing_method.title()} Smoothed")
        
        if filters_applied:
            title_parts.append(f"({', '.join(filters_applied)})")
        
        # Update layout
        fig.update_layout(
            title=' '.join(title_parts),
            xaxis_title='Date and Time',
            yaxis_title='OD',
            height=500,
            hovermode='x unified',
            template='plotly_white',
            margin=dict(l=60, r=60, t=80, b=60),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )
        
        # Configure x-axis for better datetime display
        fig.update_xaxes(
            tickformat='%b %d<br>%H:%M',  # Format: "Jun 21\n14:30"
            dtick=3600000*6,  # Tick every 6 hours
            tickangle=0
        )
        
        # Prepare response
        response_data = {
            'success': True,
            'vials_processed': list(vial_data.keys()),
            'filtering_parameters': {
                'smoothing_method': smoothing_method,
                'smoothing_window': smoothing_window,
                'enable_outlier_removal': enable_outlier_removal,
                'outlier_threshold': outlier_threshold,
                'outlier_window_size': outlier_window_size,
                'enable_trimming': enable_trimming
            },
            'data_summary': {
                vial: {
                    'original_points': data['data_points_original'],
                    'filtered_points': data['data_points_filtered'],
                    'reduction_percent': round((1 - data['data_points_filtered'] / data['data_points_original']) * 100, 1)
                }
                for vial, data in vial_data.items()
            },
            'plot': fig.to_dict()
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filtering OD data: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Filtering failed: {str(e)}")


@router.get("/growth-rate/data-time-range/{vials}")
def get_data_time_range(vials: str, db_session: Session = Depends(get_db)):
    """
    Get the time range (first and last timestamps) for the specified vials.
    
    Args:
        vials: Comma-separated list of vial numbers (e.g., "1,2,3")
    
    Returns:
        Dictionary with min/max timestamps and formatted dates for each vial
    """
    try:
        if experiment_manager.experiment is None:
            raise HTTPException(status_code=404, detail="No current experiment selected")
        
        experiment = experiment_manager.experiment
        vial_list = [int(v) for v in vials.split(',')]
        
        vial_ranges = {}
        overall_min = None
        overall_max = None
        
        for vial in vial_list:
            if vial not in experiment.cultures:
                logger.warning(f"Vial {vial} not found in current experiment")
                continue
                
            culture = experiment.cultures[vial]
            
            # Get OD data using the correct method
            od_dict, mu_dict, rpm_dict = culture.get_last_ods_and_rpms(limit=10000)
            if not od_dict or len(od_dict) < 1:
                logger.warning(f"No OD data for vial {vial}")
                continue
            
            # Get timestamps
            timestamps = list(od_dict.keys())
            unix_timestamps = [ts.timestamp() for ts in timestamps]
            
            min_time = min(unix_timestamps)
            max_time = max(unix_timestamps)
            
            # Update overall range
            if overall_min is None or min_time < overall_min:
                overall_min = min_time
            if overall_max is None or max_time > overall_max:
                overall_max = max_time
            
            # Format for display
            min_datetime = datetime.fromtimestamp(min_time)
            max_datetime = datetime.fromtimestamp(max_time)
            
            vial_ranges[vial] = {
                'min_timestamp': min_time,
                'max_timestamp': max_time,
                'min_datetime': min_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'max_datetime': max_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'min_datetime_local': min_datetime.strftime('%Y-%m-%dT%H:%M'),  # For datetime-local input
                'max_datetime_local': max_datetime.strftime('%Y-%m-%dT%H:%M'),  # For datetime-local input
                'data_points': len(timestamps)
            }
        
        if not vial_ranges:
            raise HTTPException(status_code=404, detail="No data found for any of the specified vials")
        
        # Overall range for all selected vials
        overall_range = None
        if overall_min is not None and overall_max is not None:
            overall_min_dt = datetime.fromtimestamp(overall_min)
            overall_max_dt = datetime.fromtimestamp(overall_max)
            overall_range = {
                'min_timestamp': overall_min,
                'max_timestamp': overall_max,
                'min_datetime': overall_min_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'max_datetime': overall_max_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'min_datetime_local': overall_min_dt.strftime('%Y-%m-%dT%H:%M'),
                'max_datetime_local': overall_max_dt.strftime('%Y-%m-%dT%H:%M'),
                'duration_hours': round((overall_max - overall_min) / 3600, 1)
            }
        
        return {
            'success': True,
            'vials': vial_ranges,
            'overall': overall_range,
            'vials_processed': list(vial_ranges.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data time range: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get time range: {str(e)}")


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