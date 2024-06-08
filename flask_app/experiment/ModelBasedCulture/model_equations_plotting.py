import matplotlib.pyplot as plt
import numpy as np


def plot_mu(model=None, mu=None):
    if model is not None:
        mu_min, mu_max, ic10_ic50_ratio, ic50 = model.mu_min, model.mu_max, model.ic10_ic50_ratio, model.ic50_initial
        doses = np.linspace(0, ic50 * 4, 101)
    else:
        doses = np.linspace(0, 100, 101)
        mu_min, mu_max, ic10_ic50_ratio, ic50 = -0.1, 1, 0.1, 50

    # round all values to 2 decimal places
    mu_min, mu_max, ic10_ic50_ratio, ic50 = round(mu_min, 2), round(mu_max, 2), round(ic10_ic50_ratio, 2), round(ic50, 2)

    mu_values = mu(doses, mu_min = mu_min, mu_max=mu_max, ic10_ic50_ratio=ic10_ic50_ratio, ic50=ic50)

    plt.figure(figsize=(10, 6))
    plt.plot(doses, mu_values, label='Growth Rate')
    plt.xlabel('Antibiotic Dose')
    plt.ylabel('Growth Rate')
    plt.title('Effect of Antibiotic Dose on Bacterial Growth Rate')
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_dose_effective(model=None, dose_effective=None):
    """
    Plot the effective antibiotic dose over time, taking into account the lag time before the drug takes effect.
    """
    dose = 100
    time_since_addition_hrs = np.linspace(0, 6, 100)

    plt.figure(figsize=(10, 6))
    if model is not None:
        lag_time_mins, slope_width_mins = model.time_lag_drug_effect_mins, model.dose_effective_slope_width_mins
        effective_doses = dose_effective(dose=dose, lag_time_hrs=model.time_lag_drug_effect_mins / 60, time_since_addition_hrs=time_since_addition_hrs, slope_width_hrs=model.dose_effective_slope_width_mins/60)
        plt.plot(time_since_addition_hrs, effective_doses, label='Lag Time Constant = {} mins, Slope Width = {} mins'.format(lag_time_mins,
                                                                                       slope_width_mins), color='black', linewidth=2)

    for lag_time_mins in [30, 120]:
        for slope_width_mins in [30, 240]:
            effective_doses = dose_effective(dose, lag_time_mins / 60, time_since_addition_hrs,
                                             slope_width_hrs=slope_width_mins / 60)
            plt.plot(time_since_addition_hrs, effective_doses,
                     label='Lag Time Constant = {} mins, Slope Width = {} mins'.format(lag_time_mins,
                                                                                       slope_width_mins),alpha=0.3, linestyle='--')
    plt.xlabel('Time Since Drug Addition (hours)')
    plt.ylabel('Effective Dose (% actual dose)')
    plt.title('Drug effect lag afer addition')
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_mu_effective(model=None, mu_effective=None):
    max_dose = 100 if model is None else model.ic50_initial * 4
    mu_max = 1 if model is None else round(model.mu_max, 2)
    mu_min = -0.1 if model is None else round(model.mu_min, 2)
    ic10_ic50_ratio = 0.9 if model is None else model.ic10_ic50_ratio
    ic50 = 50 if model is None else model.ic50_initial
    carrying_capacity = 2 if model is None else model.carrying_capacity

    plt.figure(figsize=(10, 6))

    doses = np.linspace(0, max_dose, 101)
    for population in [f * carrying_capacity for f in [0.1, 0.3, 0.6, 0.9]]:
        mu_values = mu_effective(doses, mu_min=mu_min, mu_max=mu_max, ic10_ic50_ratio=ic10_ic50_ratio, ic50=ic50,
                                 population=population, carrying_capacity=carrying_capacity)
        plt.plot(doses, mu_values, label='Effective Growth Rate (Population={:.3f})'.format(population))
    plt.axvline(x=ic50, color='red', linestyle='--', label='IC50 = {}'.format(ic50))
    plt.xlabel('Antibiotic Dose')
    plt.ylabel('Effective Growth Rate')
    plt.title('Effective Growth Rate of Bacteria with Antibiotic Dose and Population Size')
    if model is not None:
        plt.suptitle('IC50 = {}, mu_max = {}, ic10_ic50_ratio = {}, carrying_capacity = {}'.format(ic50, mu_max, ic10_ic50_ratio, carrying_capacity))
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_adaptation_rate(model=None, adaptation_rate=None):
    """plot for different values of adaptation_rate_ic10_ic50_ratio"""
    ic50 = 23 if model is None else model.ic50_initial
    adaptation_rate_max = 0.05 if model is None else model.adaptation_rate_max
    ic10_ic50_ratio = 0.8 if model is None else model.ic10_ic50_ratio
    ic10 = ic50 * ic10_ic50_ratio

    doses = np.linspace(0, ic50*2, 100)

    plt.figure(figsize=(10, 6))
    if model is not None:
        adapt_rates = adaptation_rate(doses, adaptation_rate_max, ic50, ic10_ic50_ratio, model.adaptation_rate_ic10_ic50_ratio)
        plt.plot(doses, adapt_rates, label='adaptation_rate_ic10_ic50_ratio = {}'.format(model.adaptation_rate_ic10_ic50_ratio), color='black')
    else:
        for adaptation_rate_ic10_ic50_ratio in [0.1, 0.5, 0.95, 0.99]:
            adapt_rates = adaptation_rate(doses, adaptation_rate_max, ic50, ic10_ic50_ratio,
                                          adaptation_rate_ic10_ic50_ratio)
            plt.plot(doses, adapt_rates,
                     label='adaptation_rate_ic10_ic50_ratio = {}'.format(adaptation_rate_ic10_ic50_ratio))

    plt.axvline(x=ic50, color='red', linestyle='--', label='IC50 = {}'.format(ic50))
    plt.axvline(x=ic10, color='red', linestyle='--', alpha=0.5, label='IC10 = {}'.format(ic10))
    plt.xlabel('Effective Antibiotic Dose')
    plt.ylabel('Adaptation Rate [1/hour]')
    plt.title('Effect of Antibiotic Dose on Adaptation Rate (IC50 = {})'.format(ic50))
    plt.legend()
    plt.grid(True)
    plt.show()