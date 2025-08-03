import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

# from replifactory.util.other import read_csv_tail


def growth_function(t, N0, growth_rate):
    y = N0 * np.exp(growth_rate * t)
    return y


def calculate_growth_rate(time_values, od_values):
    """
    fits exponential growth curve and returns growth rate calculated over the entire time window.
    time window must not include dilution.
    time values must be in seconds.
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

    # denoise, trim
    if len(time_values) >= 10:
        median_window = int(len(time_values) / 8) + 1
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


# def get_last_gr(od_filepath):
#     """
#     returns the last growth rate in an od.csv file,
#     calculated over an appropriate time window
#     """
#     df = read_csv_tail(od_filepath, lines=300)
#     df = df[df.index >= df.index[-1] - 60 * 60 * 5]  # cut last 5 hours
#     t = df.index.values
#     od = df.values.ravel()
#     timepoint, growth_rate, error = calculate_last_growth_rate(t, od)
#     return timepoint, growth_rate, error


def calculate_last_growth_rate(t, od):
    """
    returns the most recent growth rate in an OD sequence,
    calculated over an appropriate time window (~t_doubling/2)
    """
    if len(od) == 0:
        return np.nan, np.nan, np.nan
    od[od <= 0] = 1e-6
    od_delta = abs(od.max() - od.min())
    min_window_size = 10
    if od_delta < 0.1:
        max_window_size = 300
    else:
        max_window_size = 60

    timepoint, growth_rate, error = np.nan, np.nan, np.nan
    # initial guess
    window_size = min(60, (t[-1] - t[0]) / 60)  # minutes
    guessed_td = np.nan
    tmax = t[-1]

    for _ in range(4):
        tmin = tmax - window_size * 60
        imin = np.where(t >= tmin)[0][0]
        tw = t[imin:]
        odw = od[imin:]
        timepoint, growth_rate, error = calculate_growth_rate(tw, odw)
        td = np.log(2) / growth_rate  # hours
        if not np.isfinite(td):
            break
        guess_error = abs((td - guessed_td) / td)
        guessed_td = td

        new_window_size = int(
            abs(td) * 60 * 0.5
        )  # optimum window size [minutes] is ~half the doubling time
        new_window_size = max(new_window_size, min_window_size)
        new_window_size = min(new_window_size, max_window_size)
        if guess_error < 0.05:
            break
        if t[0] > tmin:
            break
        if new_window_size == window_size:
            break
        else:
            window_size = new_window_size

    return timepoint, growth_rate, error


def sliding_window_growth_rate(time_values, od_values, window_size_minutes):
    """
    time_values in seconds
    window size in minutes
    """
    time_values = np.array(time_values)
    od_values = np.array(od_values)
    od_values[od_values <= 0] = 1e-6

    growth_rates = []
    errors = []
    timepoints = []
    for i in range(len(time_values)):
        tmin = time_values[i]
        tmax = tmin + window_size_minutes * 60
        if tmax <= time_values[-1]:
            imax = np.where(time_values >= tmax)[0][0]
            time_window = time_values[i:imax + 1]
            od_window = od_values[i:imax + 1]

            timepoint = (tmin+tmax)/2
            try:
                timepoint_result, growth_rate, error = calculate_growth_rate(time_window, od_window)
            except:
                growth_rate, error = np.nan, np.nan
            timepoints += [timepoint]
            growth_rates += [growth_rate]
            errors += [error]
    growth_rates = np.array(growth_rates)
    errors = np.array(errors)
    timepoints = np.array(timepoints)
    return timepoints, growth_rates, errors


def sliding_window_doubling_time(t, od, window_size_minutes=20):
    timepoints, growth_rates, gr_errors = sliding_window_growth_rate(t, od, window_size_minutes=window_size_minutes)
    t_doubling = np.log(2) / growth_rates
    t_doubling_error = t_doubling * gr_errors / growth_rates
    return timepoints, t_doubling, t_doubling_error

# for i in range(len(od)):
#     imax = i + 10
#     if len(od) <= imax:
#         tmax = t[imax]
#         imax = np.where(t >= tmax)[0][0]
#         tw = t[i:imax + 1]
#         odw = od[i:imax + 1]
#         timepoint, growth_rate, error = calculate_last_growth_rate(tw, odw)
#         timepoints += [timepoint]
#         growth_rates += [growth_rate]
#         errors += [error]


def adaptive_window_growth_rate(t, od, dilution_timepoints=None):
    timepoints, growth_rates, errors = [], [], []
    for i in range(len(od) - 10):
        jmin = i
        jmax = jmin + 10
        if t[jmax] - t[0] <= 3600 * 5:
            jmin = 0
        else:
            tmax = t[jmax]
            tmin = tmax - 3600 * 5
            if dilution_timepoints is not None:
                tdil = [t for t in dilution_timepoints if tmin < t < tmax]
                if len(tdil) > 0:
                    tmin = tdil[-1]
            jmin = np.where(t >= tmin)[0][0]

        tw = t[jmin:jmax]
        odw = od[jmin:jmax]

        timepoint, growth_rate, error = calculate_last_growth_rate(tw, odw)
        timepoints += [timepoint]
        growth_rates += [growth_rate]
        errors += [error]

    growth_rates = np.array(growth_rates)
    timepoints = np.array(timepoints)
    errors = np.array(errors)
    return timepoints, growth_rates, errors


def adaptive_window_doubling_time(t, od, dilution_timepoints):
    timepoints, growth_rates, gr_errors = adaptive_window_growth_rate(
        t, od, dilution_timepoints
    )
    t_doubling = np.log(2) / growth_rates
    t_doubling_error = t_doubling * gr_errors / growth_rates
    return timepoints, t_doubling, t_doubling_error


def plot_gr(time_values, od_values, dilution_timepoints=None):
    od = np.array(od_values)
    t = np.array(time_values)

    fig, ax = plt.subplots(figsize=[16, 8], dpi=100)
    # i = 0
    # lines = []
    ax.plot(t / 3600, od, "k.", label="Optical Density")
    # ax.set_ylim(-0.05, 1.6)
    od[od <= 0] = 1e-6
    ax.set_ylabel("Optical Density")
    ax.set_xlabel("Time [hours]")
    ax2 = ax.twinx()

    # if not adaptive_window:
    #     colors = ["xkcd:dark red", "xkcd:light orange", "xkcd:green", "xkcd:purple"]
    #     for c, ws in zip(colors[:len(window_sizes_minutes)], window_sizes_minutes):
    #         td_timepoints, td, tderr = sliding_window_doubling_time(t, od, window_size_minutes=ws)
    #
    #         markers, caps, bars = ax2.errorbar(td_timepoints / 3600, td, tderr, color=c,
    #                                            alpha=0.5, label="doubling time, %d min time windows" % ws)
    #         [bar.set_alpha(0.1) for bar in bars]

    td_timepoints, td, tderr = adaptive_window_doubling_time(
        t, od, dilution_timepoints=dilution_timepoints
    )

    markers, caps, bars = ax2.errorbar(
        td_timepoints / 3600, td, tderr, alpha=0.5, label="doubling time"
    )
    [bar.set_alpha(0.1) for bar in bars]
    try:
        td = np.array(td)
        tderr = np.array(tderr)
        tdmax = np.nanmax(td[tderr < 0.05])
        tdmin = np.nanmin(td[tderr < 0.05])
        ax2.set_ylim(tdmin * 0.5, tdmax * 1.2)
    except Exception:
        pass

    ax2.grid()
    ax2.set_ylabel("Doubling time [hours]")
    # labels = [line.get_label() for line in lines]
    # ax.legend(loc=1)
    # ax2.legend(loc=2)
    # plt.show()
    return fig
