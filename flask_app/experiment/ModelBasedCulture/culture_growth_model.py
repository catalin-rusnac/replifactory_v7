from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np

from .model_equations import dose_effective, mu_effective, adaptation_rate

culture_growth_model_default_parameters = {
    'initial_population': 0.05,
    'doubling_time_mins': 20,
    'carrying_capacity': 0.9,
    'mu_min': -0.1,
    'ic50_initial': 5,
    'ic10_ic50_ratio': 0.5,
    'dose_effective_slope_width_mins': 120,
    'time_lag_drug_effect_mins': 30,
    'adaptation_rate_max': 0.08,
    'adaptation_rate_ic10_ic50_ratio': 0.8,
    'drug_concentration': 0,
    'effective_dose': 0,
}


def get_simulation_efficiency(model):
    # print("d50: {}, dilution_count: {}, effective_dose: {}".format(model.ic50_initial, len(model.doses), model.effective_dose))
    volume_used = len(model.doses) * 10
    ic50_fold_change = model.ic50s[-1][0] / model.ic50s[0][0]
    total_time = (model.population[-1][1] - model.population[0][1]).total_seconds() / 3600
    # print("Volume Used: {:.1f} ml, IC50 fold change: {:.2f}".format(volume_used, ic50_fold_change))
    volume_per_ic50_doubling = volume_used / np.log2(ic50_fold_change)
    # print("Volume per IC50 doubling: {:.1f} ml".format(volume_per_ic50_doubling))
    time_per_ic50_doubling = total_time / np.log2(ic50_fold_change)
    # print("Time per IC50 doubling: {:.1f} hours".format(total_time / np.log2(ic50_fold_change)))
    return volume_per_ic50_doubling, time_per_ic50_doubling


class CultureGrowthModel:
    def __init__(self, **kwargs):
        defaults = culture_growth_model_default_parameters
        # Update defaults with any overrides provided at initialization
        defaults.update(kwargs)

        # Assign all default values to instance variables
        for key, value in defaults.items():
            setattr(self, key, value)

        # Calculate maximum growth rate from doubling time
        self.mu_max = np.log(2) / (self.doubling_time_mins / 60)
        self._initialize_model_state()
        self.updater = None

    def _initialize_model_state(self):
        self.time_current = datetime.now()
        self.population = []
        self.generations = []
        self.doses = []
        self.effective_doses = []
        self.ic50s = [(self.ic50_initial, self.time_current)]
        self.effective_growth_rates = []
        self.adaptation_rates = []

    @property
    def growth_rate(self):
        return self.effective_growth_rates[-1][0] if self.effective_growth_rates else 0

    @property
    def first_od_timestamp(self):
        if not self.population:
            print("WARNING: Getting first OD timestamp without population data")
        return self.population[0][1] if self.population else self.time_current

    def calculate_effective_dose(self, time_current):
        """
        Calculate the effective dose of the drug at the current time, taking into account the doses added,
        the time since each addition and the lag time before the drug reaches half of its effectiveness.
        """
        if not self.effective_doses:
            current_effective_dose = self.adaptation_rate[0][0] if self.doses else 0
            self.effective_doses.append((current_effective_dose, self.time_current))
        effective_dose = self.effective_doses[0][0]  # Initial effective dose
        initial_equilibrium_dose = 0
        added_doses = np.diff([initial_equilibrium_dose]+[dose[0] for dose in self.doses])
        dilution_times = [dose[1] for dose in self.doses[0:]]
        # print(added_doses)
        for added_dose, dilution_time in zip(added_doses, dilution_times):
            if added_dose == 0:
                continue
            time_since_addition_hrs = (time_current - dilution_time).total_seconds() / 3600.0  # Convert to hours
            effective_dose += dose_effective(added_dose, self.time_lag_drug_effect_mins / 60,
                                             time_since_addition_hrs, self.dose_effective_slope_width_mins / 60)  # Assuming lag_time is in minutes
            # print("Effective Dose at time {}: {}".format(time_current, effective_dose))
        return effective_dose

    def simulate_experiment_minute(self):
        """
        Simulate one step of culture growth.
        Calculate:
            - The effective dose of the drug
            - The effective growth rate of the culture
            - The new population size
            - The adaptation rate
        Append new values to self data lists.
        Dilute the culture if needed.
        """
        effective_dose = self.calculate_effective_dose(self.time_current)
        self.effective_doses.append((effective_dose, self.time_current))
        if self.population:
            effective_growth_rate = mu_effective(effective_dose, self.mu_min, self.mu_max, self.ic10_ic50_ratio,
                                                 self.ic50s[-1][0], self.population[-1][0], self.carrying_capacity)
            self.effective_growth_rates.append((effective_growth_rate, self.time_current))

        if effective_dose > 0:
            adapt_rate = adaptation_rate(effective_dose, self.adaptation_rate_max, self.ic50s[-1][0],
                                         self.ic10_ic50_ratio,
                                         self.adaptation_rate_ic10_ic50_ratio)
            self.adaptation_rates.append((adapt_rate, self.time_current))

            ic50 = self.ic50s[-1][0] * np.exp(adapt_rate / 60)
            self.ic50s.append((ic50, self.time_current))
        if not self.population:
            new_population = self.initial_population
        else:
            new_population = self.population[-1][0] * np.exp(effective_growth_rate / 60)
        self.population.append((new_population, self.time_current))
        self.updater.update(model=self)

    def dilute_culture(self, target_dose=0, dilution_factor=1.6):
        """
        Dilute the culture and adjust the drug dose based on the dilution factor and the added dose.
        """
        added_volume = self.updater.volume_vial * (dilution_factor - 1)
        stock1_concentration = self.updater.pump1_stock_drug_concentration
        stock2_concentration = self.updater.pump2_stock_drug_concentration
        current_dose = self.drug_concentration
        current_volume = self.updater.volume_vial
        total_volume = current_volume + added_volume
        only_pump1_resulting_dose = (current_dose * current_volume + stock1_concentration * added_volume) / total_volume
        only_pump2_resulting_dose = (current_dose * current_volume + stock2_concentration * added_volume) / total_volume
        min_dose, max_dose = min(only_pump1_resulting_dose, only_pump2_resulting_dose), max(only_pump1_resulting_dose, only_pump2_resulting_dose)
        target_dose = min(max_dose, max(min_dose, target_dose))

        added_dose = target_dose - self.drug_concentration
        self.drug_concentration += added_dose
        self.doses.append((self.drug_concentration, self.time_current))
        self.population[-1] = (self.population[-1][0] / dilution_factor, self.time_current)
        # print("Stock 1 concentration: {:.2f}, Stock 2 concentration: {:.2f}".format(stock1_concentration, stock2_concentration))
        # print("min dose: {:.2f}, max dose: {:.2f}".format(min_dose, max_dose))
        # print("Current dose: {:.2f}, Added dose: {:.2f}, Target dose: {:.2f}".format(self.drug_concentration, added_dose, target_dose))

        generation_number = np.log2(dilution_factor)
        if self.generations:
            generation_number += self.generations[-1][0]
        self.generations.append((generation_number, self.time_current))

    def simulate_experiment(self, simulation_hours=48):
        """
        Simulate bacterial growth over a specified period, with a change in drug dose after 3 dilutions.
        """
        for t in range(1, simulation_hours * 60):
            self.time_current += timedelta(minutes=1)
            self.simulate_experiment_minute()

    def plot_parameters(self):
        from .model_equations import dose_effective, mu_effective, adaptation_rate
        from .model_equations_plotting import plot_dose_effective, plot_mu_effective, \
            plot_adaptation_rate

        plot_dose_effective(model=self, dose_effective=dose_effective)
        plot_mu_effective(model=self, mu_effective=mu_effective)
        plot_adaptation_rate(model=self, adaptation_rate=adaptation_rate)

    def plot_simulation(self, simulation_hours):
        self.simulate_experiment(simulation_hours)

        # population, doses, effective_growth_rates, ic50s, adaptation_rates, effective_doses
        times = [p[1] for p in self.population]
        ods = [p[0] for p in self.population]
        growth_rates, times_growth_rates = zip(*self.effective_growth_rates)
        d50_values, times_d50s = zip(*self.ic50s)
        doses_values, times_doses = zip(*self.doses)
        adaptation_rates = self.adaptation_rates
        effective_dose_values, times_effective_doses = zip(*self.effective_doses)
        generations, times_generations = zip(*self.generations)



        # Plot the main graph
        fig, ax1 = plt.subplots(figsize=(16, 9))
        ax1.plot(times, ods, "ko:", label='Bacteria Population', alpha=0.5)
        ax1.set_ylabel('Optical Density')

        # Setup Effective Growth Rate secondary y-axis (ax3)
        ax3 = ax1.twinx()
        ax3.spines['right'].set_position(('outward', 60))  # Pushes ax3 to the right
        ax3.plot(times_growth_rates, growth_rates, 'o-', color='blue', label='Effective Growth Rate')
        ax3.set_ylabel('Effective Growth Rate', color='blue')
        ax3.tick_params(axis='y', colors='blue')

        # Combine IC50 and Doses on the same secondary y-axis (ax4) on the left
        ax4 = ax1.twinx()
        ax4.spines["right"].set_visible(False)  # Hide the right spine
        ax4.yaxis.set_label_position('left')
        ax4.yaxis.set_ticks_position('left')
        ax4.spines["left"].set_position(('outward', 60))  # Adjust to avoid overlap
        ax4.set_ylabel('Dose / IC50', color='green')

        ax4.plot(times_d50s, d50_values, ':', color='green', label='IC50')

        # add point at the end to make step all the way to the right
        doses_values += (doses_values[-1],)
        times_doses += (times[-1],)

        ax4.step(times_doses, doses_values, "-", color='green', label='Dose', where='post', linewidth=1)
        ax4.tick_params(axis='y', colors='green', labelleft=True)
        ax4.step(times_effective_doses, effective_dose_values, "--", color='green', label='Effective Dose', where='post',linewidth=3)

        # Setup Adaptation Rate secondary y-axis (ax5)
        if len(adaptation_rates)>0:
            adaptation_values, times_adaptation = zip(*adaptation_rates)

            ax5 = ax1.twinx()
            ax5.plot(times_adaptation, adaptation_values, 'o-', color='xkcd:violet', label='Adaptation Rate [1/h]', markersize=2, alpha=0.5)
            ax5.set_ylabel('Adaptation Rate', color='xkcd:violet')
            ax5.tick_params(axis='y', colors='xkcd:violet')

        # Plot generations in red
        ax6 = ax1.twinx()
        ax6.spines["right"].set_visible(False)
        ax6.yaxis.set_label_position('left')
        ax6.yaxis.set_ticks_position('left')
        ax6.spines["left"].set_position(('outward', 110))
        ax6.set_ylabel('Generations', color='red')
        ax6.plot(times_generations, generations, 'ro-', label='Generations', alpha=0.5)
        ax6.tick_params(axis='y', colors='red')

        ax1.set_title('Model of adaptive evolution experiment')
        # fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9))
        fig.legend()
        plt.show()