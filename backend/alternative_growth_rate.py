"""
Advanced growth rate analysis module with configurable methods, smoothing, and filtering.
Provides multiple approaches for calculating growth rates with adaptive windowing,
data trimming, and statistical analysis.
"""

import numpy as np
from scipy import stats
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
import warnings
from typing import Dict, List, Tuple, Optional, Union
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging

warnings.filterwarnings('ignore', category=RuntimeWarning)

logger = logging.getLogger(__name__)


def clean_nan_values(data):
    """
    Recursively clean NaN values from nested dictionaries/lists to prevent JSON serialization errors.
    Converts NaN to None, inf to large numbers.
    """
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, (np.ndarray, np.generic)):
        # Convert numpy arrays/scalars to Python types
        if data.ndim == 0:  # scalar
            value = float(data)
            if np.isnan(value):
                return None
            elif np.isinf(value):
                return 1e10 if value > 0 else -1e10
            else:
                return value
        else:
            # For arrays, convert to list and clean recursively
            return clean_nan_values(data.tolist())
    elif isinstance(data, float):
        if np.isnan(data):
            return None
        elif np.isinf(data):
            return 1e10 if data > 0 else -1e10
        else:
            return data
    else:
        return data


def growth_function(t, N0, growth_rate):
    """Exponential growth function for curve fitting."""
    return N0 * np.exp(growth_rate * t)


def _rolling_median_numpy(data: np.ndarray, window_size: int) -> np.ndarray:
    """
    Fast numpy-based rolling median calculation with center=True.
    
    Args:
        data: Input data array
        window_size: Rolling window size
    
    Returns:
        Rolling median array
    """
    n = len(data)
    if window_size >= n:
        return np.full(n, np.median(data))
    
    result = np.zeros(n)
    half_window = window_size // 2
    
    for i in range(n):
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)
        result[i] = np.median(data[start:end])
    
    return result


def smooth_data(data: np.ndarray, method: str = 'median', window: int = 5) -> np.ndarray:
    """
    Apply smoothing to data using various methods with optimized numpy operations.
    
    Args:
        data: Input data array
        method: Smoothing method ('median', 'moving_average', 'savgol', 'gaussian', 'none')
        window: Window size for smoothing
    
    Returns:
        Smoothed data array
    """
    if method == 'none' or len(data) < window:
        return data
    
    if method == 'median':
        return _rolling_median_numpy(data, window)
    
    elif method == 'moving_average':
        # Use our optimized rolling mean function
        rolling_mean, _ = _rolling_stats_numpy(data, window)
        
        # Fix the end points that don't have enough future data for proper centering
        # For a window of N points, replace the last N//2 points with original values
        # to avoid artificial flattening at the end of an upward trend
        trim_points = window // 2
        if trim_points > 0 and len(rolling_mean) > trim_points:
            # Replace the problematic end points with original data
            rolling_mean[-trim_points:] = data[-trim_points:]
        
        return rolling_mean
    
    elif method == 'savgol':
        if len(data) < window or window < 3:
            return data
        # Ensure window is odd
        if window % 2 == 0:
            window += 1
        poly_order = min(3, window - 1)
        return savgol_filter(data, window, poly_order)
    
    elif method == 'gaussian':
        sigma = window / 4.0  # Standard deviation based on window size
        return gaussian_filter1d(data, sigma)
    
    return data


def _rolling_stats_numpy(data: np.ndarray, window_size: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Ultra-fast numpy-based rolling mean and std calculation with center=True.
    Uses optimized sliding window operations for maximum performance.
    
    Args:
        data: Input data array
        window_size: Rolling window size
    
    Returns:
        Tuple of (rolling_mean, rolling_std) arrays
    """
    n = len(data)
    
    if window_size >= n:
        # If window is larger than data, use entire array for all points
        mean_val = np.mean(data)
        std_val = np.std(data, ddof=0) if n > 1 else 0.0
        return np.full(n, mean_val), np.full(n, std_val)
    
    # Pre-allocate output arrays
    rolling_mean = np.zeros(n, dtype=np.float64)
    rolling_std = np.zeros(n, dtype=np.float64)
    
    half_window = window_size // 2
    
    # Optimized loop with minimal operations
    for i in range(n):
        # Calculate window bounds (centered, clamped to array bounds)
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)
        
        # Direct slice operations (most efficient in numpy)
        window_data = data[start:end]
        window_len = end - start
        
        # Fast mean calculation
        rolling_mean[i] = np.sum(window_data) / window_len
        
        # Fast std calculation using optimized formula
        if window_len > 1:
            # Use efficient variance calculation: Var(X) = E[X²] - E[X]²
            mean_val = rolling_mean[i]
            variance = np.sum((window_data - mean_val) ** 2) / window_len
            rolling_std[i] = np.sqrt(variance)
        else:
            rolling_std[i] = 0.0
    
    return rolling_mean, rolling_std


def remove_outliers(time_data: np.ndarray, od_data: np.ndarray, 
                   z_threshold: float = 3.0, window_size: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """
    Remove outliers using rolling window z-score method.
    
    This function removes entire time points where OD values are statistical outliers
    within a rolling window. Note: This can create gaps in your time series.
    
    Args:
        time_data: Time points
        od_data: OD measurements
        z_threshold: Z-score threshold for outlier detection (default: 3.0)
        window_size: Rolling window size for outlier detection (default: 5)
    
    Returns:
        Filtered time and OD data (may have fewer points than input)
    """
    if len(od_data) < window_size:
        return time_data, od_data
    
    # Calculate rolling mean and std using fast numpy implementation
    rolling_mean, rolling_std = _rolling_stats_numpy(od_data, window_size)
    
    # Calculate z-scores using rolling statistics
    # Avoid division by zero
    rolling_std = np.where(rolling_std == 0, 1e-10, rolling_std)
    z_scores = np.abs((od_data - rolling_mean) / rolling_std)
    
    # Create mask for values within threshold
    mask = z_scores < z_threshold
    
    # Log how many outliers were removed
    n_outliers = np.sum(~mask)
    if n_outliers > 0:
        print(f"Debug: Removed {n_outliers} outliers ({n_outliers/len(od_data)*100:.1f}% of data) using window size {window_size}")
        print(f"Debug: Time range before outlier removal: {len(time_data)} points")
        print(f"Debug: Time range after outlier removal: {np.sum(mask)} points")
    
    return time_data[mask], od_data[mask]


def interpolate_outliers(time_data: np.ndarray, od_data: np.ndarray, 
                        z_threshold: float = 3.0, window_size: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """
    Replace outliers with interpolated values using rolling window detection.
    This preserves the time series structure while fixing bad data points.
    
    Args:
        time_data: Time points
        od_data: OD measurements
        z_threshold: Z-score threshold for outlier detection (default: 3.0)
        window_size: Rolling window size for outlier detection (default: 5)
    
    Returns:
        Time data (unchanged) and OD data with outliers interpolated
    """
    if len(od_data) < window_size:
        return time_data, od_data
    
    od_data_clean = od_data.copy()
    
    # Calculate rolling mean and std using fast numpy implementation
    rolling_mean, rolling_std = _rolling_stats_numpy(od_data, window_size)
    
    # Calculate z-scores using rolling statistics
    # Avoid division by zero
    rolling_std = np.where(rolling_std == 0, 1e-10, rolling_std)
    z_scores = np.abs((od_data - rolling_mean) / rolling_std)
    
    # Find outliers
    outlier_mask = z_scores >= z_threshold
    
    if np.any(outlier_mask):
        n_outliers = np.sum(outlier_mask)
        logger.debug(f"Interpolating {n_outliers} outliers ({n_outliers/len(od_data)*100:.1f}% of data) using window size {window_size}")
        
        # Interpolate outliers using linear interpolation
        good_indices = np.where(~outlier_mask)[0]
        outlier_indices = np.where(outlier_mask)[0]
        
        if len(good_indices) >= 2:
            od_data_clean[outlier_indices] = np.interp(
                outlier_indices, 
                good_indices, 
                od_data[good_indices]
            )
    
    return time_data, od_data_clean


def calculate_doubling_time(growth_rate: float) -> float:
    """Calculate doubling time from growth rate."""
    if growth_rate <= 0:
        return np.inf
    return np.log(2) / growth_rate


def adaptive_window_growth_rate(time_data: np.ndarray, od_data: np.ndarray,
                               min_window: float = 1.0, max_window: float = 12.0,
                               initial_guess: float = 0.5) -> List[Dict]:
    """
    Calculate growth rate using adaptive window size based on doubling time.
    Exactly matches the main experiment's real-time algorithm from experiment/growth_rate.py
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements
        min_window: Minimum window size in hours
        max_window: Maximum window size in hours  
        initial_guess: Initial growth rate guess
    
    Returns:
        List of growth rate calculations with timestamps
    """
    results = []
    
    # Work with Unix timestamps like main experiment (no pre-smoothing!)
    t = time_data.copy()
    od = od_data.copy()
    
    # Simulate real-time calculation: only look at PAST data up to each time point
    # Start when we have enough data for meaningful calculation
    for i in range(10, len(od)):  # Start at index 10 (need some history)
        # Only use data UP TO the current time point (no future data!)
        past_t = t[:i+1]  # All data up to and including current point
        past_od = od[:i+1]
        
        # Use calculate_last_growth_rate on this past-only data
        # This applies smoothing and trimming exactly like real-time calculation
        timepoint, growth_rate, error = calculate_main_experiment_growth_rate(past_t, past_od)
        
        if np.isfinite(growth_rate):
            # Debug logging for adaptive window (log only first few results)
            if len(results) < 5:
                logger.warning(f"Real-time sim #{len(results)}: i={i}, past_data_points={len(past_t)}")
                logger.warning(f"  time range: {past_t[0]:.0f} to {past_t[-1]:.0f} ({(past_t[-1]-past_t[0])/3600:.2f}h)")
                logger.warning(f"  growth_rate={growth_rate:.4f} /hr, current_time={t[i]:.0f}")
            
            results.append({
                'timestamp': t[i],  # Current time point (like real-time calculation)
                'time_hours': (t[i] - time_data[0]) / 3600,
                'growth_rate': growth_rate,
                'growth_rate_error': error,
                'window_size': (past_t[-1] - past_t[0]) / 3600,  # Total past data span in hours
                'data_points': len(past_t)
            })
    
    return results


def calculate_rolling_window_growth_rates(time_data: np.ndarray, od_data: np.ndarray,
                                        method: str, window_size: float, 
                                        use_real_time_simulation: bool) -> List[Dict]:
    """
    Unified dispatch function for rolling window growth rate calculations.
    Supports both real-time simulation and retrospective analysis modes.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements
        method: Analysis method ('adaptive' or 'fixed')
        window_size: Window size in hours (used for fixed method)
        use_real_time_simulation: If True, use only past data. If False, use past + future data.
    
    Returns:
        List of growth rate calculations with timestamps
    """
    if method == 'adaptive':
        if use_real_time_simulation:
            return adaptive_window_growth_rate_realtime(time_data, od_data)
        else:
            return adaptive_window_growth_rate_retrospective(time_data, od_data)
    elif method == 'fixed':
        if window_size is None:
            logger.warning("window_size is None for fixed method, using default of 3.0 hours")
            window_size = 3.0
        if use_real_time_simulation:
            return fixed_window_growth_rate_realtime(time_data, od_data, window_size)
        else:
            return fixed_window_growth_rate_retrospective(time_data, od_data, window_size)
    else:
        raise ValueError(f"Unknown method: {method}")


def adaptive_window_growth_rate_realtime(time_data: np.ndarray, od_data: np.ndarray) -> List[Dict]:
    """
    Real-time adaptive window growth rate calculation.
    Exactly matches the main experiment's algorithm - only uses past data.
    """
    # This is the existing real-time implementation
    return adaptive_window_growth_rate(time_data, od_data)


def adaptive_window_growth_rate_retrospective(time_data: np.ndarray, od_data: np.ndarray,
                                         min_window: float = 1.0, max_window: float = 12.0,
                                         initial_guess: float = 0.5) -> List[Dict]:
    """
    Calculate growth rate using adaptive window size but with retrospective analysis.
    Applies smoothing to the entire dataset first, then uses both past and future data.
    This creates smoother curves but differs from real-time calculation.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements
        min_window: Minimum window size in hours
        max_window: Maximum window size in hours  
        initial_guess: Initial growth rate guess
    
    Returns:
        List of growth rate calculations with timestamps
    """
    results = []
    
    # Work with Unix timestamps
    t = time_data.copy()
    od = od_data.copy()
    
    # Apply smoothing to the ENTIRE dataset first (retrospective approach)
    if len(od) >= 10:
        median_window = int(len(od) / 8) + 1
        import pandas as pd
        od_smooth = pd.Series(od).rolling(median_window * 2, center=True).median()
        # Trim time and od exactly like main experiment
        t = t[median_window : -(median_window - 1)]
        od = od_smooth[median_window : -(median_window - 1)].values
    
    # Calculate growth rates using sliding window with both past and future data
    for i in range(10, len(od) - 10):  # Leave buffer at both ends
        center_time = t[i]
        
        # Use a centered window that includes both past and future data
        # Start with the same adaptive logic but allow future data
        window_half_size = 30  # Start with 30 points on each side
        window_start = max(0, i - window_half_size)
        window_end = min(len(t), i + window_half_size)
        
        # Extract window data (this includes both past and future relative to center point)
        window_t = t[window_start:window_end]
        window_od = od[window_start:window_end]
        
        # Calculate growth rate for this centered window
        timepoint, growth_rate, error = calculate_main_experiment_growth_rate(window_t, window_od)
        
        if np.isfinite(growth_rate):
            results.append({
                'timestamp': center_time,
                'time_hours': (center_time - time_data[0]) / 3600,
                'growth_rate': growth_rate,
                'growth_rate_error': error,
                'window_size': (window_t[-1] - window_t[0]) / 3600,  # Actual window size used
                'r_squared': np.nan,
                'data_points': len(window_t)
            })
    
    return results


def calculate_main_experiment_growth_rate(t, od):
    """
    Replicate the calculate_last_growth_rate function from main experiment.
    Uses iterative convergence to find optimal window size (~t_doubling/2).
    
    Args:
        t: Time array (Unix timestamps)
        od: OD array
    """
    if len(od) == 0:
        return np.nan, np.nan, np.nan
    
    od = od.copy()
    od[od <= 0] = 1e-6
    od_delta = abs(od.max() - od.min())
    min_window_size = 10  # minutes
    max_window_size = 60 if od_delta >= 0.1 else 300  # minutes
    
    timepoint, growth_rate, error = np.nan, np.nan, np.nan
    window_size = min(60, (t[-1] - t[0]) / 60)  # Initial guess in minutes
    guessed_td = np.nan
    tmax = t[-1]
    
    # Iterative convergence (up to 4 iterations like main experiment)
    for _ in range(4):
        tmin = tmax - window_size * 60  # Convert minutes to seconds
        imin = np.where(t >= tmin)[0]
        if len(imin) == 0:
            break
        imin = imin[0]
        
        tw = t[imin:]
        odw = od[imin:]
        
        # Calculate growth rate for this window (using main's calculate_growth_rate logic)
        timepoint, growth_rate, error = calculate_window_growth_rate(tw, odw)
        
        if not np.isfinite(growth_rate):
            break
            
        td = np.log(2) / growth_rate  # Doubling time in hours
        if not np.isfinite(td):
            break
            
        guess_error = abs((td - guessed_td) / td) if np.isfinite(guessed_td) else 1.0
        guessed_td = td
        
        # Calculate new window size (half doubling time, like main experiment)
        new_window_size = int(abs(td) * 60 * 0.5)  # Half doubling time in minutes
        new_window_size = max(new_window_size, min_window_size)
        new_window_size = min(new_window_size, max_window_size)
        
        # Convergence criteria like main experiment
        if guess_error < 0.05:
            break
        if t[0] > tmin:
            break  
        if new_window_size == window_size:
            break
        else:
            window_size = new_window_size
    
    return timepoint, growth_rate, error


def calculate_window_growth_rate(time_values, od_values):
    """
    Replicate the calculate_growth_rate function from main experiment exactly.
    Includes the same smoothing and trimming logic.
    """
    assert (
        1 < time_values[-1] < 1e10
    ), "time must be time in seconds since 1970-01-01 00:00:00"

    if (
        len(time_values) < 6
    ):  # at least 6 data points required for reasonable measurement.
        return np.nan, np.nan, np.nan

    if (
        np.diff(time_values).max() > 30 * 60
    ):  # half an hour gap in the data, major problem.
        return np.nan, np.nan, np.nan

    # denoise, trim - EXACT same logic as main experiment
    if len(time_values) >= 10:
        median_window = int(len(time_values) / 8) + 1
        import pandas as pd
        od_values = (
            pd.Series(od_values).rolling(median_window * 2, center=True).median()
        )
        time_values = time_values[median_window : -(median_window - 1)]
        od_values = od_values[median_window : -(median_window - 1)]

    # convert to hrs
    hours = np.array(time_values) / 3600
    hours = hours - min(hours)

    try:
        popt, pcov = curve_fit(growth_function, hours, od_values, p0=(1e-3, 0.3))
    except Exception:
        return np.nan, np.nan, np.nan
    
    timepoint = (float(time_values[0]) + time_values[-1]) / 2
    growth_rate = popt[1]
    growth_rate_error = np.sqrt(np.diag(pcov))[1]
    
    return timepoint, growth_rate, growth_rate_error



def fixed_window_growth_rate(time_data: np.ndarray, od_data: np.ndarray,
                           window_size: float = 3.0) -> List[Dict]:
    """
    Calculate growth rate using fixed window size.
    
    Args:
        time_data: Time points
        od_data: OD measurements  
        window_size: Window size in hours
    
    Returns:
        List of growth rate calculations
    """
    results = []
    
    # Convert to hours if needed
    if np.mean(time_data) > 1e6:  # Likely Unix timestamp
        time_hours = (time_data - time_data[0]) / 3600
    else:
        time_hours = time_data
    
    for i in range(len(time_hours)):
        # Define window around current point
        window_start = time_hours[i] - window_size / 2
        window_end = time_hours[i] + window_size / 2
        
        window_mask = (time_hours >= window_start) & (time_hours <= window_end)
        
        if np.sum(window_mask) < 3:
            continue
            
        window_time = time_hours[window_mask]
        window_od = od_data[window_mask]
        
        try:
            popt, pcov = curve_fit(growth_function, 
                                 window_time - window_time[0], 
                                 window_od, 
                                 p0=[window_od[0], 0.5])
            
            growth_rate = popt[1]
            growth_rate_error = np.sqrt(np.diag(pcov))[1] if len(pcov) > 1 else np.nan
            
            results.append({
                'timestamp': time_data[i],
                'time_hours': time_hours[i],
                'growth_rate': growth_rate,
                'growth_rate_error': growth_rate_error,
                'window_size': window_size,
                'r_squared': calculate_r_squared(window_time - window_time[0], window_od, popt),
                'data_points': len(window_time)
            })
            
        except Exception:
            continue
    
    return results


def fixed_window_growth_rate_realtime(time_data: np.ndarray, od_data: np.ndarray,
                                     window_size: float = 3.0) -> List[Dict]:
    """
    Real-time fixed window growth rate calculation.
    Only uses past data available up to each timepoint, simulating real experiment conditions.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements  
        window_size: Window size in hours
    
    Returns:
        List of growth rate calculations
    """
    results = []
    t = time_data.copy()
    od = od_data.copy()
    
    # Simulate real-time calculation: only look at PAST data up to each time point
    for i in range(10, len(od)):  # Start when we have enough history
        # Only use data UP TO the current time point (no future data!)
        past_t = t[:i+1]
        past_od = od[:i+1]
        
        # Convert to relative hours for window calculation
        past_hours = (past_t - past_t[0]) / 3600
        current_time_hours = past_hours[-1]
        
        # Define window ending at current time (only looking back)
        window_start_hours = max(0, current_time_hours - window_size)
        window_end_hours = current_time_hours
        
        # Find data within the past window
        window_mask = (past_hours >= window_start_hours) & (past_hours <= window_end_hours)
        
        if np.sum(window_mask) < 6:  # Need at least 6 points like main experiment
            continue
            
        window_time = past_hours[window_mask]
        window_od = past_od[window_mask]
        
        try:
            # Use the same calculation as main experiment
            timepoint, growth_rate, error = calculate_window_growth_rate(
                past_t[window_mask], window_od
            )
            
            if np.isfinite(growth_rate):
                results.append({
                    'timestamp': t[i],
                    'time_hours': (t[i] - time_data[0]) / 3600,
                    'growth_rate': growth_rate,
                    'growth_rate_error': error,
                    'window_size': window_size,
                    'data_points': len(window_time)
                })
                
        except Exception:
            continue
    
    return results


def fixed_window_growth_rate_retrospective(time_data: np.ndarray, od_data: np.ndarray,
                                          window_size: float = 3.0) -> List[Dict]:
    """
    Retrospective fixed window growth rate calculation.
    Uses both past and future data around each timepoint for smoother curves.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements  
        window_size: Window size in hours
    
    Returns:
        List of growth rate calculations
    """
    results = []
    
    # Apply smoothing to the ENTIRE dataset first (retrospective approach)
    t = time_data.copy()
    od = od_data.copy()
    
    # Apply smoothing (if data is already smoothed, this won't hurt much)
    if len(od) >= 10:
        median_window = int(len(od) / 8) + 1
        import pandas as pd
        od_smooth = pd.Series(od).rolling(median_window * 2, center=True).median()
        t = t[median_window : -(median_window - 1)]
        od = od_smooth[median_window : -(median_window - 1)].values
    
    # Convert to hours
    time_hours = (t - t[0]) / 3600
    
    # Calculate growth rates using centered windows (past + future data)
    for i in range(len(time_hours)):
        # Define centered window around current point
        window_start = time_hours[i] - window_size / 2
        window_end = time_hours[i] + window_size / 2
        
        window_mask = (time_hours >= window_start) & (time_hours <= window_end)
        
        if np.sum(window_mask) < 6:
            continue
            
        window_time = time_hours[window_mask]
        window_od = od[window_mask]
        
        try:
            popt, pcov = curve_fit(growth_function, 
                                 window_time - window_time[0], 
                                 window_od, 
                                 p0=[window_od[0], 0.5])
            
            growth_rate = popt[1]
            growth_rate_error = np.sqrt(np.diag(pcov))[1] if len(pcov) > 1 else np.nan
            
            results.append({
                'timestamp': t[i],
                'time_hours': time_hours[i],
                'growth_rate': growth_rate,
                'growth_rate_error': growth_rate_error,
                'window_size': window_size,
                'r_squared': calculate_r_squared(window_time - window_time[0], window_od, popt),
                'data_points': len(window_time)
            })
            
        except Exception:
            continue
    
    return results


def rolling_window_growth_rate(time_data: np.ndarray, od_data: np.ndarray,
                             window_size: float = 3.0, step_size: float = 0.5) -> List[Dict]:
    """
    Calculate growth rate using rolling window analysis.
    
    Args:
        time_data: Time points
        od_data: OD measurements
        window_size: Window size in hours
        step_size: Step size between windows in hours
    
    Returns:
        List of growth rate calculations
    """
    results = []
    
    # Convert to hours if needed
    if np.mean(time_data) > 1e6:  # Likely Unix timestamp
        time_hours = (time_data - time_data[0]) / 3600
    else:
        time_hours = time_data
    
    # Start from the first possible window center
    start_time = time_hours[0] + window_size / 2
    end_time = time_hours[-1] - window_size / 2
    
    current_time = start_time
    while current_time <= end_time:
        window_start = current_time - window_size / 2
        window_end = current_time + window_size / 2
        
        window_mask = (time_hours >= window_start) & (time_hours <= window_end)
        
        if np.sum(window_mask) >= 3:
            window_time = time_hours[window_mask]
            window_od = od_data[window_mask]
            
            try:
                popt, pcov = curve_fit(growth_function, 
                                     window_time - window_time[0], 
                                     window_od, 
                                     p0=[window_od[0], 0.5])
                
                growth_rate = popt[1]
                growth_rate_error = np.sqrt(np.diag(pcov))[1] if len(pcov) > 1 else np.nan
                
                # Find closest timestamp
                closest_idx = np.argmin(np.abs(time_hours - current_time))
                
                results.append({
                    'timestamp': time_data[closest_idx],
                    'time_hours': current_time,
                    'growth_rate': growth_rate,
                    'growth_rate_error': growth_rate_error,
                    'window_size': window_size,
                    'r_squared': calculate_r_squared(window_time - window_time[0], window_od, popt),
                    'data_points': len(window_time)
                })
                
            except Exception:
                pass
        
        current_time += step_size
    
    return results


def calculate_r_squared(x: np.ndarray, y: np.ndarray, params: np.ndarray) -> float:
    """Calculate R-squared for growth function fit."""
    try:
        y_pred = growth_function(x, *params)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    except:
        return 0


def parse_datetime_flexible(time_str: str) -> float:
    """
    Parse datetime string flexibly, trying multiple approaches for timezone handling.
    Returns Unix timestamp.
    """
    from datetime import timezone
    
    if not time_str:
        return None
        
    # Clean the input
    clean_time = time_str.replace('Z', '').strip()
    
    try:
        # First try: Parse as-is (assumes local timezone)
        parsed = datetime.fromisoformat(clean_time)
        return parsed.timestamp()
    except ValueError:
        pass
    
    try:
        # Second try: Parse with explicit UTC assumption
        parsed = datetime.fromisoformat(clean_time)
        if parsed.tzinfo is None:
            # Assume UTC if no timezone info
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        pass
    
    try:
        # Third try: Parse manually for common formats
        if 'T' in clean_time:
            date_part, time_part = clean_time.split('T')
            year, month, day = map(int, date_part.split('-'))
            hour, minute = map(int, time_part.split(':')[:2])
            parsed = datetime(year, month, day, hour, minute)
            return parsed.timestamp()
    except (ValueError, IndexError):
        pass
    
    raise ValueError(f"Could not parse datetime: {time_str}")


def trim_data_by_od(time_data: np.ndarray, od_data: np.ndarray,
                   min_od: Optional[float] = None, max_od: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Trim data to a specific OD range.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements
        min_od: Minimum OD value (inclusive)
        max_od: Maximum OD value (inclusive)
    
    Returns:
        Filtered time and OD data within the specified OD range
    """
    if len(time_data) == 0 or len(od_data) == 0:
        raise ValueError("Input data arrays are empty")
    
    if len(time_data) != len(od_data):
        raise ValueError("Time and OD data arrays must have the same length")
    
    # Create mask for OD range
    mask = np.ones(len(od_data), dtype=bool)
    
    if min_od is not None:
        mask &= (od_data > min_od)
    
    if max_od is not None:
        mask &= (od_data <= max_od)
    
    # Check if any data remains after filtering
    if not np.any(mask):
        available_range = f"{np.min(od_data):.4f} to {np.max(od_data):.4f}"
        requested_range = f"{min_od or 'none'} to {max_od or 'none'}"
        raise ValueError(f"No data points remain after OD trimming. Available OD range: {available_range}, requested range: {requested_range}")
    
    return time_data[mask], od_data[mask]


def trim_data_by_time(time_data: np.ndarray, od_data: np.ndarray,
                     start_time: Optional[str] = None, 
                     end_time: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Trim data based on start and end times.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements
        start_time: Start time string (ISO format)
        end_time: End time string (ISO format)
    
    Returns:
        Trimmed time and OD data
        
    Raises:
        ValueError: If trimming results in no data points
    """
    if len(time_data) == 0:
        raise ValueError("Input data is empty")
        
    mask = np.ones(len(time_data), dtype=bool)
    
    if start_time:
        try:
            start_timestamp = parse_datetime_flexible(start_time)
            print(f"Debug: Parsed start_time '{start_time}' to timestamp {start_timestamp}")
            print(f"Debug: Data range: {time_data.min()} to {time_data.max()}")
            print(f"Debug: Data start as datetime: {datetime.fromtimestamp(time_data.min())}")
            print(f"Debug: Data end as datetime: {datetime.fromtimestamp(time_data.max())}")
            
            mask = mask & (time_data >= start_timestamp)
            print(f"Debug: Points after start filter: {np.sum(mask)}")
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse start_time '{start_time}': {e}")
    
    if end_time:
        try:
            end_timestamp = parse_datetime_flexible(end_time)
            print(f"Debug: Parsed end_time '{end_time}' to timestamp {end_timestamp}")
            
            mask = mask & (time_data <= end_timestamp)
            print(f"Debug: Points after end filter: {np.sum(mask)}")
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse end_time '{end_time}': {e}")
    
    # Check if any data points remain after filtering
    if not np.any(mask):
        # Convert timestamps to readable format for error message
        if len(time_data) > 0:
            data_start = datetime.fromtimestamp(time_data.min()).strftime('%Y-%m-%d %H:%M:%S')
            data_end = datetime.fromtimestamp(time_data.max()).strftime('%Y-%m-%d %H:%M:%S')
            
            # Show what was requested vs what's available
            requested_info = ""
            if start_time:
                try:
                    clean_start = start_time.replace('Z', '')
                    parsed_start = datetime.fromisoformat(clean_start)
                    requested_info += f"Requested start: {parsed_start.strftime('%Y-%m-%d %H:%M:%S')} "
                except:
                    requested_info += f"Requested start: {start_time} (parsing failed) "
            if end_time:
                try:
                    clean_end = end_time.replace('Z', '')
                    parsed_end = datetime.fromisoformat(clean_end)
                    requested_info += f"Requested end: {parsed_end.strftime('%Y-%m-%d %H:%M:%S')}"
                except:
                    requested_info += f"Requested end: {end_time} (parsing failed)"
            
            raise ValueError(f"No data points found in the specified time range. "
                           f"Available data: {data_start} to {data_end}. "
                           f"{requested_info}. "
                           f"Note: Times should be in your local timezone.")
        else:
            raise ValueError("No data points found in the specified time range")
    
    trimmed_time = time_data[mask]
    trimmed_od = od_data[mask]
    
    if len(trimmed_time) == 0:
        raise ValueError("Trimming resulted in no data points")
    
    return trimmed_time, trimmed_od


def logistic_growth(t: np.ndarray, N0: float, K: float, r: float) -> np.ndarray:
    """
    Logistic growth model: N(t) = K / (1 + ((K-N0)/N0) * exp(-r*t))
    
    Args:
        t: Time points
        N0: Initial population
        K: Carrying capacity
        r: Growth rate
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Prevent division by zero and extreme values with more robust handling
        epsilon = 1e-12
        N0 = max(N0, epsilon)  # Ensure N0 is positive
        K = max(K, epsilon)    # Ensure K is positive
        
        if N0 <= 0 or K <= 0:
            return np.full_like(t, np.nan)
        
        # Clip exponential argument to prevent overflow/underflow
        exp_arg = -r * t
        exp_arg = np.clip(exp_arg, -700, 700)  # Prevent exp overflow
        
        denominator = 1 + ((K - N0) / N0) * np.exp(exp_arg)
        
        # Prevent division by zero
        denominator = np.maximum(denominator, 1e-15)
        
        result = K / denominator
        
        # Ensure result is finite and within reasonable bounds
        result = np.where(np.isfinite(result), result, np.nan)
        
        return result


def gompertz_growth(t: np.ndarray, N0: float, A: float, B: float, C: float) -> np.ndarray:
    """
    Gompertz growth model using standard parameterization.
    Standard form: A * exp(-exp(-C * (t - B)))
    
    Args:
        t: Time points
        N0: Initial population (not used in calculation but kept for consistency)
        A: Carrying capacity (asymptotic value)
        B: Displacement along x-axis (inflection time)
        C: Growth rate coefficient
    
    Max growth rate = C (occurs at t = B)
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Prevent division by zero and extreme values with more robust handling
        epsilon = 1e-12
        A = max(A, epsilon)  # Ensure A is positive
        
        if A <= 0 or C <= 0:
            return np.full_like(t, np.nan)
        
        # Standard formula: A * exp(-exp(-C * (t - B)))
        inner = -C * (t - B)
        inner = np.clip(inner, -700, 700)  # Prevent overflow
        
        outer = -np.exp(inner)
        outer = np.clip(outer, -700, 700)  # Prevent overflow
        
        result = A * np.exp(outer)
        
        # Ensure result is finite and within reasonable bounds
        result = np.where(np.isfinite(result), result, np.nan)
        
        return result


def exponential_growth(t: np.ndarray, N0: float, r: float) -> np.ndarray:
    """
    Simple exponential growth model: N(t) = N0 * exp(r*t)
    
    Args:
        t: Time points
        N0: Initial population
        r: Growth rate
    """
    # Prevent extreme values with robust handling
    epsilon = 1e-12
    N0 = max(N0, epsilon)  # Ensure N0 is positive
    
    if N0 <= 0:
        return np.full_like(t, np.nan)
    
    # Clip exponential argument to prevent overflow/underflow
    exp_arg = r * t
    exp_arg = np.clip(exp_arg, -700, 700)  # Prevent exp overflow
    
    result = N0 * np.exp(exp_arg)
    
    # Ensure result is finite
    result = np.where(np.isfinite(result), result, np.nan)
    
    return result


def calculate_goodness_of_fit(y_true: np.ndarray, y_pred: np.ndarray, n_params: int) -> Dict:
    """
    Calculate various goodness of fit metrics.
    
    Args:
        y_true: Actual values
        y_pred: Predicted values
        n_params: Number of parameters in the model
    
    Returns:
        Dictionary with fit metrics
    """
    # Ensure arrays are numpy arrays and same length
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    n = len(y_true)
    
    if len(y_true) != len(y_pred):
        logger.error(f"Array length mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}")
        return {'r_squared': np.nan, 'adj_r_squared': np.nan, 'rmse': np.nan, 'aic': np.nan, 'bic': np.nan}
    
    # Check for invalid values
    if np.any(np.isnan(y_true)) or np.any(np.isnan(y_pred)):
        logger.warning("NaN values detected in goodness of fit calculation")
        return {'r_squared': np.nan, 'adj_r_squared': np.nan, 'rmse': np.nan, 'aic': np.nan, 'bic': np.nan}
    
    y_mean = np.mean(y_true)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_mean) ** 2)
    
    if ss_tot != 0:
        r_squared = 1 - (ss_res / ss_tot)
        # Log unusual values for debugging but don't cap them
        if r_squared < -1.0:
            logger.warning(f"Poor R-squared value: {r_squared:.3f}, ss_res: {ss_res:.6f}, ss_tot: {ss_tot:.6f}")
            logger.debug(f"y_true range: [{np.min(y_true):.4f}, {np.max(y_true):.4f}], y_pred range: [{np.min(y_pred):.4f}, {np.max(y_pred):.4f}]")
            logger.debug(f"Mean of y_true: {np.mean(y_true):.4f}")
    else:
        r_squared = 0.0
        logger.warning("R-squared calculation: ss_tot is zero (no variance in true values)")
    
    # Adjusted R-squared (with protection against extreme values)
    if n > n_params + 1:
        denominator = n - n_params - 1
        if denominator > 0:
            adj_r_squared = 1 - (1 - r_squared) * (n - 1) / denominator
        else:
            adj_r_squared = r_squared  # Fallback to regular R-squared
    else:
        adj_r_squared = r_squared  # Not enough data for adjusted R-squared
    
    # Root Mean Square Error
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    # Akaike Information Criterion (AIC)
    if ss_res > 0:
        aic = n * np.log(ss_res / n) + 2 * n_params
    else:
        aic = np.nan
    
    # Bayesian Information Criterion (BIC)
    if ss_res > 0:
        bic = n * np.log(ss_res / n) + n_params * np.log(n)
    else:
        bic = np.nan
    
    return {
        'r_squared': r_squared,
        'adj_r_squared': adj_r_squared,
        'rmse': rmse,
        'aic': aic,
        'bic': bic
    }


def estimate_growth_parameters(time_hours: np.ndarray, od_data: np.ndarray) -> Dict:
    """
    Estimate initial parameters for growth models based on data characteristics.
    """
    # Basic statistics
    # Ensure N0 is positive and reasonable
    N0 = max(od_data[0], 1e-6)  # Use epsilon if first value is zero/negative
    N_max = np.max(od_data)
    N_final = od_data[-1]
    
    # Estimate exponential growth rate from early data (first 1/3)
    early_idx = max(3, len(od_data) // 3)
    early_time = time_hours[:early_idx]
    early_od = od_data[:early_idx]
    
    # Fit exponential to early data for growth rate estimate
    try:
        log_od = np.log(early_od + 1e-10)  # Avoid log(0)
        coeffs = np.polyfit(early_time, log_od, 1)
        r_estimate = coeffs[0]
    except:
        r_estimate = 0.5
        
    # Improved carrying capacity estimation
    # For trimmed data, be more conservative about K estimation
    growth_ratio = N_final / N0
    final_fraction = N_final / N_max
    
    # Check if data shows signs of saturation (flat end)
    if len(time_hours) > 5:
        last_30pct = int(len(od_data) * 0.3)  # Use more data for slope calculation
        end_slope = (od_data[-1] - od_data[-last_30pct]) / (time_hours[-1] - time_hours[-last_30pct])
        relative_slope = end_slope / N_max
        
        if relative_slope < 0.005:  # Very flat at the end, likely at saturation
            K_estimate = N_max * 1.02  # K just above observed max
        elif relative_slope < 0.02:  # Moderately flat
            K_estimate = N_max * 1.1   # K slightly above max
        elif final_fraction > 0.95:  # Final value very close to max
            K_estimate = N_max * 1.15  # K slightly above max
        else:  # Still growing
            K_estimate = N_max * 1.5   # K moderately above observed
    else:
        K_estimate = N_max * 1.3  # Default for short datasets
    
    # Estimate lag time (time when growth becomes significant)
    lag_estimate = 0.0
    threshold = N0 * 1.5  # 50% increase from initial
    lag_idx = np.where(od_data > threshold)[0]
    if len(lag_idx) > 0:
        lag_estimate = time_hours[lag_idx[0]]
    
    return {
        'N0': N0,
        'r': max(0.1, min(r_estimate, 3.0)),  # Clamp reasonable range
        'K': K_estimate,
        'A': K_estimate,  # Carrying capacity 
        'B': max(0.0, min(lag_estimate, time_hours[-1] * 0.5)),  # Inflection time (displacement along x-axis)
        'C': max(0.1, min(r_estimate, 3.0)),  # Growth rate coefficient
        'mu': max(0.1, min(r_estimate, 3.0)),
        'lag': max(0.0, min(lag_estimate, time_hours[-1] * 0.5))
    }


def fit_growth_model(time_data: np.ndarray, od_data: np.ndarray, model_type: str = 'exponential') -> Dict:
    """
    Fit different growth models to the data and return parameters with fit statistics.
    Uses multiple attempts with different initial guesses for robustness.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements
        model_type: Type of model ('exponential', 'logistic', 'gompertz')
    
    Returns:
        Dictionary with fitted parameters and statistics
    """
    if len(time_data) < 4:
        return {
            'success': False,
            'error': 'Insufficient data points for model fitting',
            'model_type': model_type
        }
    
    # Handle non-positive values by filtering or replacing with small epsilon
    epsilon = 1e-6  # Small positive value
    
    if np.any(od_data <= 0):
        num_negative = np.sum(od_data <= 0)
        logger.warning(f"Found {num_negative} non-positive OD values (min: {np.min(od_data):.6f}), replacing with epsilon={epsilon}")
        
        # Replace non-positive values with small epsilon
        od_data = np.where(od_data <= 0, epsilon, od_data)
        
        # If too many values were replaced (>50%), it might indicate bad data quality
        if num_negative > len(od_data) * 0.5:
            return {
                'success': False,
                'error': f'Too many non-positive OD values ({num_negative}/{len(od_data)}), likely bad data quality',
                'model_type': model_type
            }
        
        logger.info(f"Successfully replaced {num_negative} non-positive values. Data range: {np.min(od_data):.6f} to {np.max(od_data):.6f}")
    
    # More relaxed growth validation for trimmed data
    growth_ratio = np.max(od_data) / np.min(od_data)
    if growth_ratio < 1.2:  # Relaxed from 1.5 to 1.2 (20% growth minimum)
        return {
            'success': False,
            'error': f'Insufficient growth observed for model fitting (growth ratio: {growth_ratio:.2f}, minimum: 1.2)',
            'model_type': model_type
        }
    
    # Convert time to hours from start
    time_hours = (time_data - time_data[0]) / 3600.0
    
    # Estimate initial parameters from data
    estimates = estimate_growth_parameters(time_hours, od_data)
    
    try:
        if model_type == 'logistic':
            # Improved logistic model initialization with better parameter estimates
            # Use robust initial value estimation
            initial_points = min(10, len(od_data) // 3)
            N0 = np.mean(od_data[:initial_points])
            N0 = max(N0, epsilon * 10)  # Ensure N0 is sufficiently above epsilon
            N_max = np.max(od_data)
            N_final = od_data[-1]
            
            # Better growth rate estimation from exponential phase
            # Use the steepest part of the growth curve
            if len(od_data) > 10:
                # Find the steepest slope in the middle section
                slopes = []
                for i in range(2, len(od_data) - 2):
                    slope = (od_data[i+1] - od_data[i-1]) / (time_hours[i+1] - time_hours[i-1])
                    slopes.append(slope)
                max_slope_idx = np.argmax(slopes) + 2
                r_estimate = slopes[max_slope_idx - 2] / od_data[max_slope_idx]
            else:
                r_estimate = estimates['r']
            
            # Better carrying capacity estimation
            # Check if data shows clear saturation
            if len(time_hours) > 5:
                last_30pct = int(len(od_data) * 0.3)
                end_slope = (od_data[-1] - od_data[-last_30pct]) / (time_hours[-1] - time_hours[-last_30pct])
                relative_slope = end_slope / N_max
                
                if relative_slope < 0.005:  # Very flat at the end
                    K_estimate = N_max * 1.02  # K just above observed max
                elif relative_slope < 0.02:  # Moderately flat
                    K_estimate = N_max * 1.1   # K slightly above max
                else:  # Still growing significantly
                    K_estimate = N_max * 1.5   # K moderately above max
            else:
                K_estimate = N_max * 1.3  # Default for short datasets
            
            # Multiple attempts with improved parameter combinations
            attempts = [
                [N0, K_estimate, r_estimate],  # Best estimate
                [N0, N_max * 1.02, 0.5],      # K very close to max (stationary data)
                [N0, N_max * 1.1, 0.8],       # K slightly above max
                [N0, N_max * 1.3, 0.6],       # K moderately above max
                [N0, N_max * 1.8, 1.0],       # K well above max (exponential data)
                [N0, N_max * 2.5, 0.4],       # K high (early growth data)
                [N0, N_max * 1.05, 0.3],      # Conservative estimate
            ]
            
            # More flexible bounds for better convergence
            min_K = np.max(od_data) * 0.95  # Allow K to be slightly below max
            max_K = np.max(od_data) * 10.0   # Reasonable upper bound
            min_N0 = min(epsilon * 0.1, np.min(od_data) * 0.1)  # Allow N0 to be very small
            bounds = ([min_N0, min_K, 0.01], [20.0, max_K, 5.0])
            
            best_result = None
            best_error = float('inf')
            
            for attempt in attempts:
                try:
                    popt, pcov = curve_fit(logistic_growth, time_hours, od_data,
                                         p0=attempt, bounds=bounds, maxfev=5000)
                    N0_fit, K_fit, r_fit = popt
                    y_pred = logistic_growth(time_hours, N0_fit, K_fit, r_fit)
                    error = np.sum((od_data - y_pred) ** 2)
                    
                    if error < best_error:
                        best_error = error
                        # Calculate inflection point time (when growth rate is maximum)
                        lag_time = np.log((K_fit - N0_fit) / N0_fit) / r_fit if r_fit > 0 and K_fit > N0_fit else None
                        
                        # Calculate doubling time
                        doubling_time = np.log(2) / r_fit if r_fit > 0 else None
                        
                        # Calculate max growth rate time (t0 + lag_time = inflection point)
                        start_time = float(time_data[0])
                        if lag_time is not None and lag_time > 0:
                            max_growth_rate_time = start_time + lag_time * 3600  # Convert hours to seconds
                        else:
                            max_growth_rate_time = start_time  # Max growth rate at start (no lag)
                        
                        # Debug: Print fitted parameters
                        logger.info(f"Logistic fit successful: N0={N0_fit:.6f}, K={K_fit:.4f}, r={r_fit:.4f}, error={error:.6f}")
                        logger.info(f"Data range: {np.min(od_data):.6f} to {np.max(od_data):.6f}")
                        
                        best_result = {
                            'success': True,
                            'model_type': 'logistic',
                            'parameters': {
                                'N0': N0_fit,
                                'r': r_fit,
                                'K': K_fit,
                                'mu': r_fit,  # Maximum growth rate occurs at inflection
                                'lag_time': lag_time,
                                'doubling_time': doubling_time,
                                'max_growth_rate_time': max_growth_rate_time  # Inflection point time
                            },
                            'fit_quality': calculate_goodness_of_fit(od_data, y_pred, 3),
                            'predictions': y_pred
                        }
                except Exception as e:
                    logger.warning(f"Logistic fit attempt failed with p0={attempt}: {str(e)}")
                    continue
            
            if best_result is None:
                logger.error(f"All logistic fitting attempts failed. Data range: {np.min(od_data):.6f} to {np.max(od_data):.6f}, N attempts: {len(attempts)}")
                raise ValueError("All logistic fitting attempts failed")
            result = best_result
            
        elif model_type == 'gompertz':
            # Multiple attempts with different parameter combinations
            # Include more conservative K estimates for trimmed data
            attempts = [
                [estimates['N0'], estimates['A'], estimates['B'], estimates['C']],
                [od_data[0], np.max(od_data) * 1.05, 1.0, 0.5],  # A close to max, B=1hr inflection, C=0.5/hr growth
                [od_data[0], np.max(od_data) * 1.2, 0.5, 0.8],   # A slightly above max
                [od_data[0], np.max(od_data) * 1.5, 1.0, 0.5],   # A moderately above max
                [od_data[0], np.max(od_data) * 2.0, 0.5, 1.0],   # A well above max
                [od_data[0], np.max(od_data) * 3.0, 2.0, 0.3],   # A very high (early growth data)
                [od_data[0], np.max(od_data) * 2.5, 0.0, 0.8]    # No lag (B=0)
            ]
            
            # Bounds for Gompertz parameters: [N0, A, B, C]
            min_A = np.max(od_data) * 0.99  # Allow A to be slightly below max (for trimmed stationary data)
            max_A = np.max(od_data) * 15.0  # More permissive upper bound
            min_N0 = min(epsilon * 0.1, np.min(od_data) * 0.1)  # Allow N0 to be very small
            bounds = ([min_N0, min_A, 0, 0.01], [20.0, max_A, time_hours[-1], 8.0])
            
            best_result = None
            best_error = float('inf')
            
            for attempt in attempts:
                try:
                    popt, pcov = curve_fit(gompertz_growth, time_hours, od_data,
                                         p0=attempt, bounds=bounds, maxfev=5000)
                    N0_fit, A_fit, B_fit, C_fit = popt
                    y_pred = gompertz_growth(time_hours, N0_fit, A_fit, B_fit, C_fit)
                    error = np.sum((od_data - y_pred) ** 2)
                    
                    if error < best_error:
                        best_error = error
                        
                        # Calculate max specific growth rate = C (growth rate coefficient)
                        max_growth_rate = C_fit  # Growth rate coefficient (like sliding window)
                        doubling_time = np.log(2) / max_growth_rate if max_growth_rate > 0 else None
                        
                        # Debug logging
                        logger.warning(f"Gompertz fit: A={A_fit:.4f}, B={B_fit:.4f}, C={C_fit:.4f}")
                        logger.warning(f"Gompertz max growth rate: {max_growth_rate:.4f} /hr")
                        
                        # Calculate max growth rate time (inflection point at B)
                        start_time = float(time_data[0])
                        max_growth_rate_time = start_time + B_fit * 3600  # Convert hours to seconds
                        
                        best_result = {
                            'success': True,
                            'model_type': 'gompertz',
                            'parameters': {
                                'N0': N0_fit,
                                'r': C_fit,  # Growth rate coefficient (comparable to sliding window)
                                'A': A_fit,  # Carrying capacity
                                'B': B_fit,  # Inflection time (displacement along x-axis)
                                'C': C_fit,  # Growth rate coefficient
                                'doubling_time': doubling_time,
                                'max_growth_rate_time': max_growth_rate_time  # Inflection point time
                            },
                            'fit_quality': calculate_goodness_of_fit(od_data, y_pred, 4),
                            'predictions': y_pred
                        }
                except:
                    continue
            
            if best_result is None:
                raise ValueError("All Gompertz fitting attempts failed")
            result = best_result

        elif model_type == 'exponential':
            # Exponential growth: N(t) = N0 * exp(r * t)
            # More diverse initial guesses for robustness
            attempts = [
                [estimates['N0'], max(0.01, estimates['r'])],  # Estimated parameters
                [od_data[0], 0.1],   # Slow growth
                [od_data[0], 0.3],   # Moderate growth
                [od_data[0], 0.5],   # Medium growth
                [od_data[0], 0.8],   # Fast growth
                [od_data[0], 1.0],   # Very fast growth
                [od_data[0], 1.5],   # Extremely fast growth
                [od_data[0] * 0.8, 0.4],  # Slightly lower N0
                [od_data[0] * 1.2, 0.6],  # Slightly higher N0
            ]
            
            # Set bounds for exponential parameters
            # More flexible bounds for better fitting
            min_N0 = min(epsilon * 0.1, od_data[0] * 0.1)  # Allow very small initial OD values
            max_N0 = max(od_data[0] * 5.0, epsilon * 1000)  # Allow higher initial estimates
            bounds = ([min_N0, 0.001],   # Lower bounds: N0, r (r > 0 for growth)
                     [max_N0, 10.0])     # Upper bounds: N0, r
            
            best_result = None
            best_error = float('inf')
            
            for attempt in attempts:
                try:
                    popt, pcov = curve_fit(exponential_growth, time_hours, od_data,
                                         p0=attempt, bounds=bounds, maxfev=5000)
                    N0_fit, r_fit = popt
                    y_pred = exponential_growth(time_hours, N0_fit, r_fit)
                    error = np.sum((od_data - y_pred) ** 2)
                    
                    if error < best_error:
                        best_error = error
                        
                        # For exponential model, max growth rate = r (constant)
                        max_growth_rate = r_fit
                        doubling_time = np.log(2) / max_growth_rate if max_growth_rate > 0 else None
                        
                        # For exponential model, growth rate is constant, so max occurs at midpoint
                        start_time = float(time_data[0])
                        mid_time = float(time_data[len(time_data)//2])
                        max_growth_rate_time = mid_time
                        
                        best_result = {
                            'success': True,
                            'model_type': 'exponential',
                            'parameters': {
                                'N0': N0_fit,
                                'r': r_fit,
                                'doubling_time': doubling_time,
                                'max_growth_rate_time': max_growth_rate_time
                            },
                            'fit_quality': calculate_goodness_of_fit(od_data, y_pred, 2),
                            'predictions': y_pred
                        }
                        
                        logger.warning(f"Exponential fit: N0={N0_fit:.4f}, r={r_fit:.4f}, error={error:.4f}")
                        logger.warning(f"Exponential max growth rate: {max_growth_rate:.4f} /hr")
                        
                except Exception as e:
                    logger.warning(f"Exponential fit attempt failed with p0={attempt}: {str(e)}")
                    continue
            
            if best_result is None:
                raise ValueError("All exponential fitting attempts failed")
            result = best_result
            
        else:
            return {
                'success': False,
                'error': f'Unknown model type: {model_type}',
                'model_type': model_type
            }
            
        # Add parameter errors from covariance matrix if available
        try:
            if 'predictions' in result:
                # Try to get covariance from last successful fit
                # This is approximate since we don't store pcov from best fit
                result['parameter_errors'] = None
        except:
            result['parameter_errors'] = None
            
        # Clean any NaN values before returning
        return clean_nan_values(result)
        
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Growth model fitting failed for {model_type}: {error_msg}")
        logger.debug(f"Data characteristics - Length: {len(od_data)}, OD range: {np.min(od_data):.3f}-{np.max(od_data):.3f}, Growth ratio: {np.max(od_data)/np.min(od_data):.2f}")
        
        # Provide more specific error messages
        if "failed" in error_msg.lower():
            if model_type == 'logistic':
                error_msg = "Logistic model fitting failed. Data may not show saturation behavior or lacks sufficient S-curve characteristics."
            elif model_type == 'gompertz':
                error_msg = "Gompertz model fitting failed. Data may not show clear lag phase or asymmetric growth characteristics."
            
        return {
            'success': False,
            'error': error_msg,
            'model_type': model_type
        }


def calculate_summary_statistics(growth_rate_data: List[Dict]) -> Dict:
    """Calculate summary statistics for growth rate data."""
    if not growth_rate_data:
        return {
            'max_growth_rate': None,
            'avg_growth_rate': None,
            'avg_growth_rate_ci': None,
            'std_growth_rate': None,
            'max_growth_time': None,
            'data_points': 0
        }
    
    # Safe extraction of growth rates, handling potential NaN values
    growth_rates = []
    for d in growth_rate_data:
        try:
            gr = d.get('growth_rate')
            if gr is not None and isinstance(gr, (int, float)) and not np.isnan(gr):
                growth_rates.append(gr)
        except (TypeError, ValueError):
            # Skip any problematic values
            continue
    
    if not growth_rates:
        return {
            'max_growth_rate': None,
            'avg_growth_rate': None,
            'avg_growth_rate_ci': None,
            'std_growth_rate': None,
            'max_growth_time': None,
            'data_points': 0
        }
    
    growth_rates_array = np.array(growth_rates)
    mean_gr = np.mean(growth_rates_array)
    std_gr = np.std(growth_rates_array, ddof=1)  # Sample standard deviation
    n = len(growth_rates_array)
    
    # Calculate 95% confidence interval for the mean
    # Using t-distribution for small samples, normal for large samples
    if n > 30:
        # Use normal distribution (z-score = 1.96 for 95% CI)
        ci_multiplier = 1.96
    else:
        # Use t-distribution
        from scipy import stats
        ci_multiplier = stats.t.ppf(0.975, n-1)  # 95% CI, two-tailed
    
    standard_error = std_gr / np.sqrt(n)
    confidence_interval = ci_multiplier * standard_error
    
    max_idx = np.argmax(growth_rates)
    max_growth_data = growth_rate_data[max_idx]
    
    # Calculate doubling times
    growth_rates_array = np.array(growth_rates)
    # Filter out very small growth rates that cause unrealistic doubling times
    # Only include growth rates > 0.001 /hr (doubling time < 693 hours = ~29 days)
    valid_growth_rates = growth_rates_array[growth_rates_array > 0.001]
    
    if len(valid_growth_rates) > 0:
        doubling_times = np.log(2) / valid_growth_rates  # hours
        min_doubling_time = np.min(doubling_times)
        avg_doubling_time = np.mean(doubling_times)
        
        # Debug logging
        logger.warning(f"Doubling time calculation debug:")
        logger.warning(f"  Total growth rates: {len(growth_rates_array)}")
        logger.warning(f"  Valid growth rates (>0.001): {len(valid_growth_rates)}")
        logger.warning(f"  Growth rates (first 5): {valid_growth_rates[:5]}")
        logger.warning(f"  Doubling times (first 5): {doubling_times[:5]}")
        logger.warning(f"  Min doubling time: {min_doubling_time:.4f}h")
        logger.warning(f"  Avg doubling time: {avg_doubling_time:.4f}h")
    else:
        min_doubling_time = np.nan
        avg_doubling_time = np.nan

    # Calculate doubling times for max and average growth rates
    max_growth_rate = max(growth_rates)
    max_growth_doubling_time = np.log(2) / max_growth_rate if max_growth_rate > 0.001 else np.nan
    avg_growth_doubling_time = np.log(2) / mean_gr if mean_gr > 0.001 else np.nan

    result = {
        'max_growth_rate': max_growth_rate,
        'avg_growth_rate': mean_gr,
        'avg_growth_rate_ci': confidence_interval,
        'std_growth_rate': std_gr,
        'max_growth_time': max_growth_data['timestamp'],
        'data_points': len(growth_rate_data),
        'max_growth_doubling_time': max_growth_doubling_time,
        'avg_growth_doubling_time': avg_growth_doubling_time
    }
    
    # Debug logging for rolling window summary
    logger.warning(f"Rolling window summary: max_growth_rate={max(growth_rates):.4f} /hr, avg_growth_rate={mean_gr:.4f} /hr")
    
    # Clean any potential NaN values
    return clean_nan_values(result)


def create_growth_rate_plot(vial_data: Dict) -> Dict:
    """
    Create Plotly figure for growth rate analysis results.
    
    Args:
        vial_data: Dictionary with vial data and growth rate results
    
    Returns:
        Plotly figure as dictionary
    """
    fig = go.Figure()
    
    vial_colors = {
        1: '#1f77b4', 2: '#ff7f0e', 3: '#2ca02c', 4: '#d62728',
        5: '#9467bd', 6: '#8c564b', 7: '#e377c2'
    }
    
    # Determine plot type from the data (check if any vials have fitted curves)
    has_fitted_curves = False
    for vial, data in vial_data.items():
        if (data['growth_rate_results'] and 
            len(data['growth_rate_results']) > 0 and
            data['growth_rate_results'][0].get('fitted_curve', False)):
            has_fitted_curves = True
            break
    
    for vial, data in vial_data.items():
        if not data['growth_rate_results']:
            continue
            
        color = vial_colors.get(vial, '#000000')
        
        # Check if this specific vial has fitted curve data
        is_fitted_curve = (len(data['growth_rate_results']) > 0 and
                          data['growth_rate_results'][0].get('fitted_curve', False))
        
        if is_fitted_curve:
            # Plot fitted curve (for logistic/Gompertz models)
            curve_data = data['growth_rate_results'][0]
            time_fit = curve_data['time_fit']
            od_fit = curve_data['od_fit']
            
            # Convert timestamps to datetime objects
            datetimes_fit = [datetime.fromtimestamp(ts) for ts in time_fit]
            
            # Add the fitted curve
            fig.add_trace(
                go.Scatter(
                    x=datetimes_fit,
                    y=od_fit,
                    mode='lines',
                    name=f'Vial {vial} ({curve_data["model_type"].title()} Fit)',
                    line=dict(color=color, width=3, dash='dot'),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                'Time: %{x}<br>' +
                                'OD: %{y:.4f}<br>' +
                                '<extra></extra>'
                )
            )
            
            # Plot the filtered data points that were actually used for fitting
            filtered_time = curve_data.get('filtered_time', data.get('raw_time', []))
            filtered_od = curve_data.get('filtered_od', data.get('raw_od', []))
            filtered_datetimes = [datetime.fromtimestamp(ts) for ts in filtered_time]
            
            fig.add_trace(
                go.Scatter(
                    x=filtered_datetimes,
                    y=filtered_od,
                    mode='markers',
                    name=f'Vial {vial} (Filtered Data)',
                    marker=dict(color=color, size=4, opacity=0.4),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                'Time: %{x}<br>' +
                                'OD: %{y:.4f}<br>' +
                                '<extra></extra>'
                )
            )
        else:
            # Plot growth rate vs time (for rolling windows and exponential)
            try:
                timestamps = [d['timestamp'] for d in data['growth_rate_results']]
                datetimes = [datetime.fromtimestamp(ts) for ts in timestamps]
                growth_rates = [d['growth_rate'] for d in data['growth_rate_results']]
            except KeyError as e:
                # Handle unexpected data structure gracefully
                logger.warning(f"Unexpected data structure for vial {vial}: missing key {e}")
                logger.warning(f"Available keys in first result: {list(data['growth_rate_results'][0].keys()) if data['growth_rate_results'] else 'No results'}")
                continue
            

            
            # Main growth rate line
            fig.add_trace(
                go.Scatter(
                    x=datetimes,
                    y=growth_rates,
                    mode='lines+markers',
                    name=f'Vial {vial}',
                    line=dict(color=color, width=2),
                    marker=dict(size=4, opacity=0.4)
                )
            )
    
    # Update layout based on plot type
    if has_fitted_curves:
        title = 'Growth Model Fit (Filtered Data)'
        yaxis_title = 'Optical Density (OD)'
    else:
        title = 'Growth Rate Analysis Results'
        yaxis_title = 'Growth Rate (/hr)'
    
    fig.update_layout(
        title=title,
        xaxis_title='Date and Time',
        yaxis_title=yaxis_title,
        height=600,
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=60, r=60, t=80, b=60)
    )
    
    # Configure x-axis for better datetime display
    fig.update_xaxes(
        tickformat='%b %d<br>%H:%M',  # Format: "Jun 21\n14:30"
        dtick=3600000*6,  # Tick every 6 hours
        tickangle=0
    )
    

    
    # Add grid for better readability
    fig.update_xaxes(showgrid=True, gridcolor='lightgray', gridwidth=0.5)
    fig.update_yaxes(showgrid=True, gridcolor='lightgray', gridwidth=0.5)
    
    # Clean the plot data before returning
    plot_dict = fig.to_dict()
    return clean_nan_values(plot_dict)


def analyze_growth_rate(time_data: np.ndarray, od_data: np.ndarray,
                       method: str = 'adaptive',
                       window_size: float = 3.0,
                       window_step: float = 0.5,
                       smoothing_method: str = 'median',
                       smoothing_window: int = 5,
                       outlier_handling: str = 'none',
                       outlier_threshold: float = 3.0,
                       outlier_window_size: int = 5,
                       start_time: Optional[str] = None,
                       end_time: Optional[str] = None,
                       min_od: Optional[float] = None,
                       max_od: Optional[float] = None,
                       model_type: str = 'rolling',
                       use_real_time_simulation: bool = True,
                       use_sliding_window: bool = False) -> Tuple[List[Dict], Dict]:
    """
    Comprehensive growth rate analysis with configurable parameters.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements
        method: Analysis method ('adaptive', 'fixed', 'rolling')
        window_size: Window size in hours (for fixed/rolling methods)
        window_step: Step size in hours (for rolling method)
        smoothing_method: Smoothing method
        smoothing_window: Smoothing window size
        outlier_handling: How to handle outliers ('none', 'remove', 'interpolate')
        outlier_threshold: Z-score threshold for outlier detection (default: 3.0)
        outlier_window_size: Rolling window size for outlier detection (default: 5)
        start_time: Start time for data trimming
        end_time: End time for data trimming
        min_od: Minimum OD value for data trimming
        max_od: Maximum OD value for data trimming
        model_type: Growth model type ('rolling', 'exponential', 'logistic', 'gompertz')
        use_real_time_simulation: If True, simulates real-time calculation (only past data). If False, uses retrospective analysis (past + future data)
        use_sliding_window: If True and model_type is 'exponential', uses sliding window analysis with exponential fitting in each window
    
    Returns:
        Tuple of (growth_rate_results, summary_statistics)
    """
    # Trim data by time if requested
    if start_time or end_time:
        time_data, od_data = trim_data_by_time(time_data, od_data, start_time, end_time)
    
    # Trim data by OD range if requested
    if min_od is not None or max_od is not None:
        time_data, od_data = trim_data_by_od(time_data, od_data, min_od, max_od)
    
    if len(time_data) < 3:
        return [], {}
    
    # Handle outliers based on selected method (BEFORE smoothing)
    if outlier_handling == 'remove':
        time_data, od_data = remove_outliers(time_data, od_data, outlier_threshold, outlier_window_size)
    elif outlier_handling == 'interpolate':
        time_data, od_data = interpolate_outliers(time_data, od_data, outlier_threshold, outlier_window_size)
    
    # Apply smoothing
    od_data_smooth = smooth_data(od_data, smoothing_method, smoothing_window)
    
    # Calculate growth rates based on method and model type
    if model_type in ['logistic', 'gompertz'] or (model_type == 'exponential' and not use_sliding_window):
        # Use parametric growth models (single fit to all data)
        model_result = fit_growth_model(time_data, od_data_smooth, model_type)
        
        if model_result['success']:
            # For parametric models, we create a fitted curve representation
            results = []
            time_hours = (time_data - time_data[0]) / 3600.0
            
            # Generate smooth time points for the fitted curve
            time_smooth = np.linspace(time_hours[0], time_hours[-1], 100)
            
            if model_type == 'logistic':
                y_fit = logistic_growth(time_smooth, 
                                      model_result['parameters']['N0'],
                                      model_result['parameters']['K'], 
                                      model_result['parameters']['r'])
            elif model_type == 'gompertz':
                y_fit = gompertz_growth(time_smooth,
                                      model_result['parameters']['N0'],
                                      model_result['parameters']['A'],
                                      model_result['parameters']['B'],
                                      model_result['parameters']['C'])
            elif model_type == 'exponential':
                y_fit = exponential_growth(time_smooth,
                                         model_result['parameters']['N0'],
                                         model_result['parameters']['r'])
            
            # Convert back to timestamps
            time_fit_stamps = time_data[0] + time_smooth * 3600
            
            # Store the fitted curve data instead of growth rate points
            results = [{
                'fitted_curve': True,
                'time_fit': time_fit_stamps.tolist(),
                'od_fit': y_fit.tolist(),
                'model_type': model_type,
                'parameters': model_result['parameters'],
                'fit_quality': model_result['fit_quality'],
                # Include the filtered data that was actually used for fitting
                'filtered_time': time_data.tolist(),
                'filtered_od': od_data_smooth.tolist()
            }]
            
            # Enhanced summary with model-specific statistics
            summary = {
                'max_growth_rate': model_result['parameters']['r'],
                'avg_growth_rate': model_result['parameters']['r'],
                'avg_growth_rate_ci': 0.1 * model_result['parameters']['r'],  # Rough estimate
                'std_growth_rate': 0.0,  # Single value fit
                'max_growth_time': float(time_data[len(time_data)//2]),
                'data_points': len(time_data),
                # Model-specific parameters
                'model_type': model_type,
                'model_parameters': model_result['parameters'],
                'fit_quality': model_result['fit_quality'],
                'model_success': True
            }
            
            # Debug: Print summary for logistic model
            if model_type == 'logistic':
                logger.warning(f"Logistic summary - model_parameters: {summary['model_parameters']}")
                logger.warning(f"Logistic summary - K value: {summary['model_parameters'].get('K', 'NOT_FOUND')}")
                logger.warning(f"Full summary keys: {list(summary.keys())}")
            
            # Clean any NaN values to prevent JSON serialization errors
            summary = clean_nan_values(summary)
            results = clean_nan_values(results)
        else:
            # Model fitting failed, return empty results
            results = []
            summary = {
                'max_growth_rate': None,
                'avg_growth_rate': None,
                'avg_growth_rate_ci': None,
                'std_growth_rate': None,
                'max_growth_time': None,
                'data_points': 0,
                'model_type': model_type,
                'model_error': model_result.get('error', 'Unknown error'),
                'model_success': False
            }
    else:
        # Use traditional rolling window methods or sliding window exponential
        if model_type == 'exponential' and use_sliding_window:
            # Sliding window with exponential fitting in each window
            results = calculate_sliding_window_exponential(
                time_data, od_data_smooth, method, window_size, window_step, use_real_time_simulation
            )
            summary = calculate_summary_statistics(results)
            summary['model_type'] = 'exponential_sliding'
            summary['model_success'] = True
        else:
            # Use unified growth rate calculation dispatch for rolling methods
            results = calculate_rolling_window_growth_rates(
                time_data, od_data_smooth, method, window_size, use_real_time_simulation
            )
            summary = calculate_summary_statistics(results)
            summary['model_type'] = 'rolling'
            summary['model_success'] = True
        
        # Clean any NaN values to prevent JSON serialization errors
        summary = clean_nan_values(summary)
        results = clean_nan_values(results)
    
    return results, summary


def exponential_sliding_window_realtime_exact(time_data: np.ndarray, od_data: np.ndarray) -> List[Dict]:
    """
    Replicate the exact real-time algorithm from experiment/growth_rate.py for exponential sliding window.
    This is the same algorithm used during the actual experiment.
    """
    if len(time_data) < 10:
        return []
    
    # Use the existing function that already replicates the main experiment exactly
    return adaptive_window_growth_rate(time_data, od_data)


def calculate_sliding_window_exponential(time_data: np.ndarray, od_data: np.ndarray,
                                       method: str, window_size: float, window_step: float,
                                       use_real_time_simulation: bool) -> List[Dict]:
    """
    Calculate growth rates using sliding window with exponential fitting in each window.
    For real-time mode, uses the same adaptive algorithm as the actual experiment.
    
    Args:
        time_data: Time points (Unix timestamps)
        od_data: OD measurements
        method: Analysis method ('adaptive', 'fixed')
        window_size: Window size in hours (ignored for adaptive real-time mode)
        window_step: Step size in hours
        use_real_time_simulation: If True, uses same algorithm as main experiment
    
    Returns:
        List of growth rate results for each window
    """
    if len(time_data) < 3:
        return []
    
    if use_real_time_simulation:
        # Use the EXACT same algorithm as the main experiment for real-time mode
        return exponential_sliding_window_realtime_exact(time_data, od_data)
    else:
        # For retrospective mode, use the appropriate approach based on method
        if method == 'adaptive':
            # For adaptive retrospective, use the adaptive algorithm
            return adaptive_window_growth_rate_retrospective(time_data, od_data)
        elif method == 'fixed' and window_size is not None:
            # For fixed retrospective, use the fixed window approach
            return fixed_window_growth_rate_retrospective(time_data, od_data, window_size)
        else:
            # Fallback: use adaptive if window_size is None
            logger.warning(f"window_size is None for method={method}, falling back to adaptive")
            return adaptive_window_growth_rate_retrospective(time_data, od_data)