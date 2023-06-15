Experiment
==========


---------------------------
Setting Up a New Experiment
---------------------------

Firstly, navigate to the 'Experiment' tab and either select an existing experiment or create a new one. Creating a new experiment will duplicate the parameters of the current experiment. If you want to start a new experiment with the default parameters, choose "default template" from the drop-down menu.

Preparation of Growth Medium Bottles
------------------------------------

Install the growth medium bottles with aseptic technique. It is crucial to be aware of airflow and maintain sterility during this process. Consider your hands as potential contamination sources - imagine they are covered in glitter that you don't want to enter the bottle.

Priming the Tubing
------------------

Next, prime the tubing with the growth medium. Go to the 'Device' tab and pump medium through the tubing until it reaches the needle. Avoid pumping drug into the vial during this step! If you accidentally pump more than a few drops of the drug medium while priming, slightly tilt the vial and use the waste pump to eliminate all the medium from the vial. Use a magnet to position the stirrer bar near the waste needle and pump out every remaining drop.

Filling the Vials
-----------------

Once the tubing is primed, each vial should be filled with 15mL of fresh growth medium. While the tubing is filling, ensure there are no leaks. The medium should be directed into only one vial, and the other lines should remain drip-free.

Setting Up Experiment Parameters
--------------------------------

After setting up the physical components, it's time to configure the experiment.

Refer to the :doc:`culture_parameters` for detailed instructions on setting up the parameters for each culture.

Examples:

   * no dilutions at all:
      Relevant parameters:

      - ``od_threshold``: 100 (very high, so it will never trigger a dilution)
      - ``od_threshold_first_dilution``: 100 (very high, so it will never trigger a dilution)
      - ``stress_decrease_delay_hrs``: 2400 (100 days, more than the expected experiment duration))

   * dilute every 24 hours with clean medium
      Relevant parameters:

      - ``od_threshold``: 100 (very high, so it will never trigger a dilution for increasing the stress)
      - ``od_threshold_first_dilution``: 100 (very high, so it will never trigger a dilution)
      - ``stress_decrease_delay_hrs``: 24 (this parameter will trigger a dilution to decrease the stress (or keep it at 0) every 24 hours)
      - ``stress_decrease_tdoubling_min_hrs``: 0.1 (almost always consider culture as 'not healthy'. If the growth rate noise is ~0.1, this value should be below ln(2)/0.1 = 6.9 hours)

   * when OD reaches 0.4, set the drug concentration at 30. Then, dilute when OD>0.3, increase stress every 3 generations as long as the doubling time is <4h. If OD<0.3 for more than 16 hours and the current doubling time is >24h - decrease the drug concentration.
      Relevant parameters:

        - ``od_threshold``: 0.3 (this parameter will trigger a dilution to increase the stress when the OD reaches 0.3)
        - ``od_threshold_first_dilution``: 0.3 (this parameter will trigger the first dilution to set the stress when the OD reaches 0.3)
        - ``stress_increase_delay_generations``: 3
        - ``stress_dose_first_dilution``: 30
        - ``stress_decrease_delay_hrs``: 16
        - ``stress_decrease_tdoubling_min_hrs``: 24