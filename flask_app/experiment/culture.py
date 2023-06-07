import copy
from datetime import datetime, timedelta

import numpy as np
from experiment.models import CultureData, PumpData, CultureGenerationData
from experiment.growth_rate import calculate_last_growth_rate
import time
from .plot import plot_culture
from copy import deepcopy


class AutoCommitDict:
    def __init__(self, initial_dict, db_session, experiment_model, vial):
        self.inner_dict = deepcopy(initial_dict)
        self.db_session = db_session
        self.experiment_model = experiment_model
        self.vial = vial

    def __getitem__(self, key):
        try:  # If the key is a number, return it as a number
            return float(self.inner_dict[key])
        except ValueError:  # If the key is a string, return it as a string
            return self.inner_dict[key]

    def __setitem__(self, key, value):
        self.inner_dict[key] = value
        parameters = deepcopy(self.experiment_model.parameters)
        parameters["cultures"][str(self.vial)] = self.inner_dict
        self.experiment_model.parameters = parameters
        self.db_session.commit()

    def __repr__(self):
        return repr(self.inner_dict)

class Culture:
    def __init__(self, experiment, vial, db):

        self.experiment = experiment
        self.vial = vial
        self.db = db

        self.od = None
        self.growth_rate = None

        self.drug_concentration = 0
        self.generation = 0
        self.last_stress_increase_generation = None
        self.last_dilution_time = None

        self.new_culture_data = None

        self.get_latest_data_from_db()

        self.parameters = AutoCommitDict(
            experiment.model.parameters["cultures"][str(vial)],
            vial=vial,
            db_session=db.session,
            experiment_model=experiment.model
        )

    def plot(self, *args, **kwargs):
        return plot_culture(self, *args, **kwargs)

    def get_latest_data_from_db(self):
        # Get the last culture data for this culture
        latest_culture_data = self.db.session.query(CultureData).filter(
            CultureData.experiment_id == self.experiment.model.id,
            CultureData.vial_number == self.vial).order_by(CultureData.timestamp.desc()).first()

        # Get the last generation data for this culture
        latest_generation_data = self.db.session.query(CultureGenerationData).filter(
            CultureGenerationData.experiment_id == self.experiment.model.id,
            CultureGenerationData.vial_number == self.vial).order_by(CultureGenerationData.timestamp.desc()).first()
        if latest_generation_data is not None:
            self.generation = latest_generation_data.generation
            self.drug_concentration = latest_generation_data.drug_concentration
            self.last_dilution_time = latest_generation_data.timestamp

        if latest_culture_data is not None:
            self.od = latest_culture_data.od
            self.growth_rate = latest_culture_data.growth_rate

            # load latest drug increase
        gen_data = self.db.session.query(CultureGenerationData).filter(
            CultureGenerationData.experiment_id == self.experiment.model.id,
            CultureGenerationData.vial_number == self.vial
        ).order_by(CultureGenerationData.timestamp.desc()).limit(20).all()
        if gen_data is not None:
            for data in gen_data:
                if data.drug_concentration < self.drug_concentration:
                    # The drug concentration decreased at this generation
                    self.last_stress_increase_generation = data.generation
                    break

    def log_od(self, od=None):
        self.od = od
        with self.experiment.app.app_context():
            self.new_culture_data = CultureData(
                experiment_id=self.experiment.model.id,
                vial_number=self.vial,
                od=od, growth_rate=None)

            self.db.session.add(self.new_culture_data)
            self.calculate_latest_growth_rate()
            if self.new_culture_data.growth_rate is not None:
                self.growth_rate = self.new_culture_data.growth_rate
            self.db.session.commit()
            self.get_latest_data_from_db()  # TODO: speed up by not querying the database again

    def log_pump_data(self, main_pump_volume, drug_pump_volume):
        with self.experiment.app.app_context():
            new_pump_data = PumpData(
                experiment_id=self.experiment.model.id,
                vial_number=self.vial,
                volume_main=main_pump_volume,
                volume_drug=drug_pump_volume,
                volume_waste=main_pump_volume+drug_pump_volume)
            self.db.session.add(new_pump_data)
            self.db.session.commit()
            self.get_latest_data_from_db()

    def log_generation(self, generation, concentration):
        self.generation = generation
        self.drug_concentration = concentration
        with self.experiment.app.app_context():
            new_generation_data = CultureGenerationData(
                experiment_id=self.experiment.model.id,
                vial_number=self.vial,
                generation=generation,
                drug_concentration=concentration,
            )
            self.db.session.add(new_generation_data)
            self.db.session.commit()
            self.get_latest_data_from_db()

    def _log_testing_generation(self, generation, concentration, timestamp=datetime.now()):
        self.generation = generation
        self.drug_concentration = concentration
        with self.experiment.app.app_context():
            new_generation_data = CultureGenerationData(
                experiment_id=self.experiment.model.id,
                vial_number=self.vial,
                generation=generation,
                drug_concentration=concentration,
                timestamp=timestamp
            )
            self.db.session.add(new_generation_data)
            self.db.session.commit()
            self.get_latest_data_from_db()

    def _log_testing_od(self, od=None, timestamp=datetime.now()):
        self.od = od

        with self.experiment.app.app_context():
            self.new_culture_data = CultureData(
                experiment_id=self.experiment.model.id,
                vial_number=self.vial,
                od=od, growth_rate=None, timestamp=timestamp)

            self.db.session.add(self.new_culture_data)
            self.calculate_latest_growth_rate()
            self.db.session.commit()
            self.get_latest_data_from_db()

    def _delete_all_records(self):
        self.db.session.query(CultureData).filter(CultureData.experiment_id == self.experiment.model.id,
                                                  CultureData.vial_number == self.vial).delete()
        self.db.session.query(PumpData).filter(PumpData.experiment_id == self.experiment.model.id,
                                               PumpData.vial_number == self.vial).delete()
        self.db.session.query(CultureGenerationData
                              ).filter(CultureGenerationData.experiment_id == self.experiment.model.id,
                                       CultureGenerationData.vial_number == self.vial).delete()
        self.db.session.commit()

    def calculate_latest_growth_rate(self):
        """
        reads last od values and calculates growth rate
        :return:
        """
        od_dict, _ = self.get_last_ods(include_current=True)
        t = np.array(list(int(dt.timestamp()) for dt in od_dict.keys()))
        od = np.array(list(od_dict.values()))
        od[od <= 0] = 1e-6
        timepoint, mu, error = calculate_last_growth_rate(t, od)
        if np.isfinite(mu):
            self.new_culture_data.growth_rate = mu

    def get_last_ods(self, limit=100, include_current=False, since_pump=False):
        culture_data = self.db.session.query(CultureData).filter(
            CultureData.experiment_id == self.experiment.model.id,
            CultureData.vial_number == self.vial
        ).order_by(CultureData.timestamp.desc()).limit(limit).all()

        if since_pump and len(culture_data) > 0:
            if self.last_dilution_time is not None:
                culture_data = [data for data in culture_data if data.timestamp > self.last_dilution_time]

        od_dict = {data.timestamp: data.od for data in culture_data}
        mu_dict = {data.timestamp: data.growth_rate for data in culture_data}
        if include_current and self.new_culture_data is not None:
            od_dict[self.new_culture_data.timestamp] = self.new_culture_data.od  # Include current uncommitted data
        od_dict = {k: v for k, v in sorted(od_dict.items(), key=lambda item: item[0])}
        return od_dict, mu_dict

    def get_last_generations(self, limit=100):
        generation_data = self.db.session.query(CultureGenerationData).filter(
            CultureGenerationData.experiment_id == self.experiment.model.id,
            CultureGenerationData.vial_number == self.vial
        ).order_by(CultureGenerationData.timestamp.desc()).limit(limit).all()
        generation_dict = {data.timestamp: data.generation for data in generation_data}
        concentration_dict = {data.timestamp: data.drug_concentration for data in generation_data}

        generation_dict = {k: v for k, v in sorted(generation_dict.items(), key=lambda item: item[0])}
        concentration_dict = {k: v for k, v in sorted(concentration_dict.items(), key=lambda item: item[0])}
        return generation_dict, concentration_dict

    def update(self):
        if self.is_time_to_dilute():
            if self.is_time_to_increase_stress():
                print(f"Increasing {self.vial} stress")
                self.increase_stress()
            else:
                print(f"Diluting {self.vial} to same concentration ")
                self.make_dilution(target_concentration=self.drug_concentration)
            return
        if self.is_time_to_rescue():
            print(f"Rescuing {self.vial}")
            self.make_dilution(target_concentration=0)  # Decrease drug concentration towards 0
            return

    def increase_stress(self):
        if self.last_stress_increase_generation is None:
            target_concentration = self.parameters["stress_dose_first_dilution"]
        else:
            volume_added = self.parameters["volume_added"]
            current_volume = self.parameters["volume_fixed"]
            dilution_factor = volume_added + current_volume / current_volume
            stress_increase_factor = (dilution_factor + 1) / 2
            target_concentration = self.drug_concentration * stress_increase_factor
        self.make_dilution(target_concentration=target_concentration)

    def is_time_to_dilute(self, verbose=False):
        if verbose:
            print("Running is_time_to_dilute method...")

        # No OD data
        if self.od is None:
            if verbose:
                print("No OD data. Not time to dilute.")
            return False

        # Not enough time has passed since last dilution
        minutes_wait = 10
        if self.last_dilution_time and self.last_dilution_time > datetime.now() - timedelta(minutes=minutes_wait):
            if verbose:
                print(f"Not updating {self.vial}, too soon after last dilution.")
            return False

        od_threshold = self.parameters["od_threshold"] if self.last_dilution_time else self.parameters[
            "od_threshold_first_dilution"]
        if self.od < od_threshold:
            if verbose:
                print("OD below threshold. Not time to dilute.")
            return False
        else:
            if verbose:
                print("OD above threshold and checks passed. Time to dilute.")
            return True

    def is_time_to_increase_stress(self, verbose=False):
        if self.last_dilution_time is None or self.growth_rate is None or self.last_stress_increase_generation is None:
            if verbose:
                print(
                    "One or more of last dilution time, growth rate, or last stress increase generation is None. Not time to increase stress.")
            return False

        stress_increase_delay_generations = self.parameters["stress_increase_delay_generations"]
        if self.generation <= stress_increase_delay_generations or self.growth_rate <= 0:
            if verbose:
                print("Generation not greater than delay or growth rate not positive. Not time to increase stress.")
            return False

        if self.generation - self.last_stress_increase_generation <= stress_increase_delay_generations:
            if verbose:
                print(
                    "Generation difference with last stress increase not greater than delay. Not time to increase stress.")
            return False

        stress_increase_tdoubling_min_hrs = self.parameters["stress_increase_tdoubling_min_hrs"]
        latest_t_doubling = np.log(2) / self.growth_rate
        if latest_t_doubling >= stress_increase_tdoubling_min_hrs:
            if verbose:
                print("Doubling time not below threshold. Not time to increase stress.")
            return False

        if verbose:
            print("All conditions met. Time to increase stress.")
        return True

    def is_time_to_rescue(self, verbose=False):
        if self.last_dilution_time is None:
            if verbose:
                print("No last dilution time. Not time to rescue.")
            return False
        if self.growth_rate is None:
            if verbose:
                print("No growth rate. Not time to rescue.")
            return False
        stress_decrease_delay_hrs = self.parameters["stress_decrease_delay_hrs"]
        if self.last_dilution_time > datetime.now() - timedelta(hours=stress_decrease_delay_hrs):
            if verbose:
                print("Last dilution too recent. Not time to rescue.")
            return False
        stress_decrease_tdoubling_max_hrs = self.parameters["stress_decrease_tdoubling_max_hrs"]
        latest_t_doubling = np.log(2) / self.growth_rate
        if 0 < latest_t_doubling < stress_decrease_tdoubling_max_hrs:
            if verbose:
                print("Doubling time is positive and below threshold. Not time to rescue.")
            return False
        else:
            if verbose:
                print("Doubling time is negative or above threshold. Time to rescue.")
            return True

    def make_dilution(self, target_concentration=None):
        if target_concentration is None:
            target_concentration = self.drug_concentration
        main_pump_volume, drug_pump_volume = self.calculate_pump_volumes(target_concentration)

        device = self.experiment.device
        lock_acquired_here = False
        try:
            if not self.experiment.locks[self.vial].locked():
                self.experiment.locks[self.vial].acquire(blocking=True)
                lock_acquired_here = True
            device.make_dilution(vial=self.vial,
                                 pump1_volume=main_pump_volume,
                                 pump2_volume=drug_pump_volume,
                                 extra_vacuum=5)
            self.last_dilution_time = datetime.now()
            self.log_pump_data(main_pump_volume, drug_pump_volume)
            self.calculate_generation_concentration_after_dil(main_pump_volume=main_pump_volume,
                                                              drug_pump_volume=drug_pump_volume)
        finally:
            if lock_acquired_here:
                self.experiment.locks[self.vial].release()

    def calculate_pump_volumes(self, target_concentration):
        volume_added = self.parameters["volume_added"]
        current_volume = self.parameters["volume_fixed"]
        current_concentration = self.drug_concentration
        if current_concentration is None:
            current_concentration = 0
        stock_concentration = self.experiment.model.parameters["stock_concentration_drug"]
        total_volume = volume_added + current_volume
        drug_total_amount = total_volume * target_concentration
        drug_current_amount = current_volume * current_concentration
        drug_pumped_amount = drug_total_amount - drug_current_amount
        drug_pump_volume = drug_pumped_amount / stock_concentration
        drug_pump_volume = round(drug_pump_volume, 3)
        drug_pump_volume = min(volume_added, max(0.001, drug_pump_volume))
        if target_concentration == 0:
            drug_pump_volume = 0
        main_pump_volume = volume_added - drug_pump_volume
        return main_pump_volume, drug_pump_volume

    def calculate_generation_concentration_after_dil(self, main_pump_volume, drug_pump_volume):
        v0 = self.parameters["volume_fixed"]
        v1 = v0 + main_pump_volume + drug_pump_volume
        dilution_factor = v1 / v0
        if self.generation is None:
            generation = np.log2(dilution_factor)
        else:
            generation = self.generation + np.log2(dilution_factor)

        stock_concentration_drug = self.experiment.model.parameters["stock_concentration_drug"]

        # Calculate the new drug concentration after dilution and adding drug
        drug_concentration = ((v0 * self.drug_concentration) + (drug_pump_volume * stock_concentration_drug)) / v1
        self.log_generation(generation, drug_concentration)  # also stores to self
        self.get_latest_data_from_db()  # TODO: speed up by not querying db again




