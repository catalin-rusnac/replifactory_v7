import numpy as np


def mu(dose, mu_min, mu_max, ic10_ic50_ratio, ic50):
    """
    Calculate the growth rate of the bacteria as a function of the drug dose.
    dose: drug dose
    mu_max: maximum growth rate [1/hour]
    ic10_ic50_ratio: ratio of ic10 to ic50, describing the steepness of the growth rate response to the drug dose
    d50: dose at which the growth rate is half of mu_max (ic50)
    return: growth rate
    """

    dose_ic10 = ic50 * ic10_ic50_ratio
    k_mu = np.log(9) / (ic50 - dose_ic10)
    return mu_min + (mu_max / (1 + np.exp(-k_mu * (ic50 - dose))))


def dose_effective(dose, lag_time_hrs, time_since_addition_hrs, slope_width_hrs):
    """
    Calculate the effective dose of the drug, taking into account the lag time before the drug takes effect
    and modeling the increase in effective dose with a sigmoid function based on a specified slope_width_hrs.

    Parameters:
    - dose: The total dose of the drug.
    - lag_time_hrs: The lag time in hours before the drug reaches half of its effectiveness.
    - time_since_addition_hrs: The elapsed time in hours since the drug was administered.
    - slope_width_hrs: Describes the width of the transition from 5% to 95% effectiveness.

    Returns:
    - The effective dose, varying between 0 and the total dose.
    """
    # Calculate the value of k using the slope_width_hrs to achieve the desired 5% to 95% transition
    k = np.log(19) / (0.5 * slope_width_hrs)  # Based on solving the sigmoid function for 5% and 95%

    # Adjust x to shift the sigmoid curve so that the inflection point is at the lag time
    x_value = (time_since_addition_hrs - lag_time_hrs)

    # Apply the sigmoid function to calculate the effective dose
    effective_dose = dose / (1 + np.exp(-k * x_value))
    # print("time_since_addition_hrs: {}, effective_dose: {}".format(time_since_addition_hrs, effective_dose))
    return effective_dose


def mu_effective(dose, mu_min, mu_max, ic10_ic50_ratio, ic50, population, carrying_capacity):
    """
    Calculate the effective growth rate of the bacteria, taking into account the drug dose,
    the carrying capacity, and the current population size.
    dose: drug dose
    mu_max: maximum growth rate
    ic10_ic50_ratio: ratio of ic10 to ic50, describing the steepness of the growth rate response to the drug dose
    ic50: dose at which the growth rate is half of mu_max (ic50)
    population: current population size
    carrying_capacity: maximum population size
    return: effective growth rate
    """
    # print("dose: {}, mu_max: {}, ic10_ic50_ratio: {}, ic50: {}, population: {}, carrying_capacity: {}".format(dose, mu_max, ic10_ic50_ratio, ic50, population, carrying_capacity))
    return mu_min + mu(dose, 0, mu_max, ic10_ic50_ratio, ic50) * (1 - population / carrying_capacity)


def adaptation_rate(dose, adaptation_rate_max, ic50, ic10_ic50_ratio, adaptation_rate_ic10_ic50_ratio):
    """
    Calculate the adaptation rate as a function of the drug dose using a Gaussian curve modified by a
    coefficient representing the height of the curve at a dose equal to 50% of ic50.

    Parameters:
    - dose: Antibiotic dose.
    - adaptation_rate_max: The maximum adaptation rate, which occurs at ic50.
    - ic50: Dose at which the growth rate is half of mu_max (IC50).
    - ic10_ic50_ratio: Ratio of ic10 to ic50, describing the steepness of the growth rate response to the drug dose.
    - adaptation_rate_ic10_ic50_ratio: ratio of the adaptation rate at ic10 to the adaptation rate at ic50,
    describing the steepness of the adaptation rate response to the drug dose.

    Returns:
    - Adaptation rate based on the given dose and curve parameters.
    """

    # Calculate k_adapt dynamically based on height_at_50
    # We solve for k_adapt such that the Gaussian formula equals height_at_50 * adaptation_rate_max at dose = ic50 / 2
    ic10 = ic50 * ic10_ic50_ratio
    k_adapt = -np.log(adaptation_rate_ic10_ic50_ratio) / ((ic10 - ic50) ** 2)
    adapt_rate = adaptation_rate_max * np.exp(-k_adapt * ((dose - ic50) ** 2))
    return adapt_rate
