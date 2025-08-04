"""
Performance optimization module for growth rate analysis.
Provides parallel processing capabilities for multiple vials.
"""

import numpy as np
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
import multiprocessing
import logging
from typing import Dict, List, Tuple, Optional
import time
import gc

logger = logging.getLogger(__name__)

def process_single_vial(vial_data_tuple):
    """
    Process a single vial's growth rate analysis.
    This function is designed to be called in parallel.
    
    Args:
        vial_data_tuple: Tuple containing (vial_number, analysis_parameters)
    
    Returns:
        Tuple of (vial_number, vial_results, summary_stats)
    """
    try:
        (vial, time_data, od_values, original_time_data, original_od_values, 
         method, window_size, window_step, smoothing_method, smoothing_window,
         outlier_handling, outlier_threshold, outlier_window_size, start_time,
         end_time, min_od, max_od, model_type, use_real_time_simulation, 
         use_sliding_window, use_filtered_data) = vial_data_tuple
        
        # Debug logging for parameter validation
        logger.info(f"Processing vial {vial}: method={method}, window_size={window_size}, model_type={model_type}")
        
        # Validate window_size for method compatibility
        if method == 'fixed' and window_size is None:
            logger.warning(f"Vial {vial}: window_size is None for fixed method, using default 3.0")
            window_size = 3.0
        elif method == 'adaptive' and window_size is not None:
            logger.info(f"Vial {vial}: window_size={window_size} will be ignored for adaptive method")
        
        # Import here to avoid issues with multiprocessing
        from alternative_growth_rate import analyze_growth_rate
        
        # Perform growth rate analysis
        growth_rate_results, summary = analyze_growth_rate(
            time_data=time_data,
            od_data=od_values,
            method=method,
            window_size=window_size,
            window_step=window_step,
            smoothing_method=smoothing_method,
            smoothing_window=smoothing_window,
            outlier_handling=outlier_handling,
            outlier_threshold=outlier_threshold,
            outlier_window_size=outlier_window_size,
            start_time=start_time,
            end_time=end_time,
            min_od=min_od,
            max_od=max_od,
            model_type=model_type,
            use_real_time_simulation=use_real_time_simulation,
            use_sliding_window=use_sliding_window
        )
        
        vial_result = {
            'growth_rate_results': growth_rate_results,
            'raw_time': original_time_data,
            'raw_od': original_od_values,
            'filtered_time': time_data,
            'filtered_od': od_values,
            'method_used': method,
            'parameters': {
                'window_size': window_size,
                'window_step': window_step,
                'smoothing_method': smoothing_method,
                'smoothing_window': smoothing_window,
                'outlier_handling': outlier_handling,
                'outlier_threshold': outlier_threshold,
                'outlier_window_size': outlier_window_size,
                'start_time': start_time,
                'end_time': end_time,
                'min_od': min_od,
                'max_od': max_od,
                'model_type': model_type
            }
        }
        
        # Force garbage collection to prevent memory leaks
        gc.collect()
        
        return (vial, vial_result, summary)
        
    except Exception as e:
        logger.error(f"Error processing vial {vial}: {str(e)}")
        return (vial, None, None)


def analyze_vials_parallel(vial_data_list: List[Tuple], max_workers: Optional[int] = None) -> Tuple[Dict, Dict]:
    """
    Analyze multiple vials in parallel using multiprocessing.
    
    Args:
        vial_data_list: List of tuples containing vial data and parameters
        max_workers: Maximum number of worker processes (default: CPU count)
    
    Returns:
        Tuple of (vial_results, summary_stats)
    """
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), len(vial_data_list))
    
    vial_results = {}
    summary_stats = {}
    
    start_time = time.time()
    logger.info(f"Starting parallel analysis of {len(vial_data_list)} vials with {max_workers} workers")
    
    # Use ThreadPoolExecutor instead of ProcessPoolExecutor to avoid serialization issues
    # and because most of the computation is in NumPy (which releases GIL)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all vial processing tasks
        future_to_vial = {
            executor.submit(process_single_vial, vial_data): vial_data[0] 
            for vial_data in vial_data_list
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_vial):
            vial = future_to_vial[future]
            try:
                vial_num, vial_result, summary = future.result()
                if vial_result is not None:
                    vial_results[vial_num] = vial_result
                    summary_stats[vial_num] = summary
                    logger.info(f"Completed analysis for vial {vial_num}")
                else:
                    logger.warning(f"Failed to analyze vial {vial_num}")
            except Exception as e:
                logger.error(f"Exception in vial {vial} analysis: {str(e)}")
    
    end_time = time.time()
    logger.info(f"Parallel analysis completed in {end_time - start_time:.2f} seconds")
    
    # Force garbage collection after all processing
    gc.collect()
    
    return vial_results, summary_stats


def optimize_memory_usage():
    """
    Optimize memory usage by forcing garbage collection and clearing caches.
    """
    import sys
    
    # Force garbage collection
    collected = gc.collect()
    logger.info(f"Garbage collection freed {collected} objects")
    
    # Clear NumPy memory pool if available
    try:
        # Clear any numpy memory pools
        import numpy as np
        if hasattr(np, '_cleanup'):
            np._cleanup()
    except:
        pass
    
    # Log memory usage
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        logger.info(f"Memory usage: RSS={memory_info.rss / 1024 / 1024:.1f}MB, VMS={memory_info.vms / 1024 / 1024:.1f}MB")
    except ImportError:
        logger.debug("psutil not available for memory monitoring")


def get_optimal_worker_count(num_vials: int) -> int:
    """
    Determine optimal number of worker processes based on system resources and vial count.
    
    Args:
        num_vials: Number of vials to process
    
    Returns:
        Optimal number of workers
    """
    cpu_count = multiprocessing.cpu_count()
    
    # For small numbers of vials, don't use more workers than vials
    if num_vials <= 2:
        return 1
    elif num_vials <= 4:
        return min(2, cpu_count)
    else:
        # Use up to 75% of CPU cores, but cap at number of vials
        return min(max(1, int(cpu_count * 0.75)), num_vials)