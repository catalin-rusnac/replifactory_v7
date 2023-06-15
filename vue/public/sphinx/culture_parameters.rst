Culture Parameters
==================

Below is an explanation of each culture parameter:

.. tip::

   :negative controls:

   All cultures which are not inoculated act as negative controls with periodic dilutions of fresh medium. The period is determined by the `stress_decrease_delay_hrs` parameter and the amount of medium added is determined by the `volume_added` parameter.



``name``

    The name of the culture. This might refer to the species of the organism, like *Escherichia coli* or *Saccharomyces cerevisiae*.

``description``

    A description of the culture, for example, a strain designation like *MG1655* or *BY4741*.

``volume_fixed``

    The fixed volume of the culture in milliliters (ml), typically 15 ml. This refers to the volume of the culture that remains in the vial, below the waste needle.

``volume_added``

    The total media volume added to the culture at a dilution step, in milliliters (ml), typically 10 ml. This is the sum of the clean medium volume and drug medium volume.

``od_threshold``

    The optical density (OD) threshold at which the culture gets diluted. This is a measure of how dense the culture is and is used to monitor the growth of the culture.

``od_threshold_first_dilution``

    The optical density (OD) threshold for the culture to be diluted for the first time. This value is usually set higher than the standard OD threshold, allowing the culture to reach a higher density before the first dilution occurs.

``stress_dose_first_dilution``

    The resulting stress dose after the first dilution. This is the concentration of the stress-inducing agent in the culture after the 'volume_added' of the stock solutions is mixed with the 'volume_fixed' of the culture. The initial amount of drug required to reach this dose from the stock concentration (for example, 200 units) can be calculated using the formula:

    .. math::

        V1 = (C2 * V2) / C1

    where:

    - C1 is the drug concentration in the stock bottle ('stock_concentration_drug'),

    - V1 is the volume of the solution to be added ('volume_added'),

    - C2 is the final concentration of the solution ('stress_dose_first_dilution'), and

    - V2 is the total volume of the solution after dilution ('volume_fixed' + 'volume_added').

    For example, the fraction of the 10 ml 'volume_added' that should be the drug can be calculated as (50 units * 25 ml) / 200 units = 6.25 ml. Therefore, 6.25 ml of the drug should be added to 3.75 ml of the non-drug medium to reach the desired 'stress_dose_first_dilution' of 50 units. Make sure that this volume is high enough for pumping accurately. For example, if the stock concentration is 100 a vial dose below 1 will be difficult to achieve with high accuracy. The pumped volume should generally be above 0.1 ml.

``stress_increase_delay_generations``

    This parameter sets the number of generations the culture must grow between increases in stress dose. These generations are computed from the dilution coefficient. For instance, when 10ml is diluted into 15ml, the dilution coefficient is 25/15 or ~1.67. The number of generations is determined by taking the base-2 logarithm of this dilution coefficient, :math:`\log_2(1.67)` which is approximately 0.74. This indicates that about 0.74 generations (or doublings) are needed to offset this dilution, increasing the generation number by roughly 0.74 at each dilution. The stress dose is increased only at dilutions that occur X generations after the previous stress dose increase, where X is this parameter. If the dilution coefficient is 1.67, the stress increase factor will be (1.67+1)/2 or ~1.335. While this stress increase factor remains consistent at each stress increase dilution, its frequency can be controlled by adjusting this parameter.

``stress_increase_tdoubling_max_hrs``

    This is the maximum doubling time (in hours) for the culture, beyond which an increase in stress dose is allowed. If the culture exhibits slow growth (high doubling time), the stress dose does not change. For example, if this parameter is set to 4 hrs, the growth rate of the culture must exceed :math:`\ln(2)/4` (approximately 0.173) for the stress dose to increase.

``stress_decrease_delay_hrs``

    The time interval between dilutions if the OD does not reach the threshold. Acts as dilution period for negative control vials (which are not inoculated). This is the waiting period (in hours) before the stress dose is decreased if the culture does not reach the OD threshold.

``stress_decrease_tdoubling_min_hrs``

    This parameter sets the minimum culture doubling time (in hours) that must be exceeded to allow a decrease in stress dose. If the doubling time is less than this value, the culture is deemed to be in good health, and there is no need to decrease the stress dose. For example, if this parameter is set to 24 hrs, the growth rate of the culture must be less than :math:`\ln(2)/24` (approximately 0.029) for the stress dose to decrease or for a negative control vial dilution to occur. Make sure that the noise in the growth rate measurement of negative control vials is less than this value.


Growth Rate and Doubling Time
-----------------------------

In the context of cell cultures, the growth rate is a measure of how quickly the cells in the culture replicate. The doubling time, on the other hand, is the amount of time it takes for the culture to double in size.

The relationship between growth rate (r) and doubling time (t) is given by the formula:

.. math:: r = \log(2) / t

Where:
- \(\log(2)\) is the natural logarithm of 2,
- t is the doubling time.

In other words, the growth rate is the reciprocal of the doubling time (scaled by the natural logarithm of 2), and vice versa. If you have a high growth rate, you'll have a shorter doubling time, and if you have a long doubling time, your growth rate will be lower.

Let's consider some examples with different growth rates:

1. For a growth rate of 0, the doubling time is infinitely long. This means the culture is not growing.

2. For a growth rate of 0.1, the doubling time is:

   .. math:: t = \log(2) / 0.1

   Which is approximately 6.93 hours.

3. For a growth rate of 0.5, the doubling time is:

   .. math:: t = \log(2) / 0.5

   Which is approximately 1.39 hours.

4. For a growth rate of 1, the doubling time is:

   .. math:: t = \log(2) / 1

   Which is approximately 0.69 hours, or about 41.4 minutes.