from datetime import datetime

import numpy as np
from experiment.database_models import CultureData, PumpData, CultureGenerationData
from experiment.growth_rate import calculate_last_growth_rate
from experiment.ModelBasedCulture.morbidostat_updater import MorbidostatUpdater, morbidostat_updater_default_parameters
from minimal_device.dilution import make_device_dilution
from fastapi_db import SessionLocal

from .ModelBasedCulture.culture_growth_model import CultureGrowthModel, culture_growth_model_default_parameters
from .ModelBasedCulture.real_culture_wrapper import RealCultureWrapper
from .plot import plot_culture
from .export import export_culture_csv, export_culture_plot_html
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
    def __init__(self, experiment, vial):
        self.experiment = experiment
        self.vial = vial
        self.od = None
        self.growth_rate = None
        self.drug_concentration = None
        self.generation = 0
        self.last_stress_increase_generation = 0
        self.last_dilution_time = None
        self.new_culture_data = None
        self.parameters = AutoCommitDict(
            experiment.model.parameters["cultures"][str(vial)],
            vial=vial,
            db_session=None,  # Will be set per operation
            experiment_model=experiment.model)
        self.culture_growth_model = CultureGrowthModel()
        self.get_latest_data_from_db()
        self.updater = MorbidostatUpdater(**self.parameters.inner_dict)
        self.adapted_culture = RealCultureWrapper(self)

    @property
    def time_current(self):
        return datetime.now()

    def update(self):
        self.updater = MorbidostatUpdater(**self.parameters.inner_dict)
        self.adapted_culture = RealCultureWrapper(self)
        self.updater.update(self.adapted_culture)

    def plot(self, *args, **kwargs):
        return plot_culture(self, *args, **kwargs)

    def plot_predicted(self):
        self.updater = MorbidostatUpdater(**self.parameters.inner_dict)
        growth_parameters = self.experiment.model.parameters["growth_parameters"][str(self.vial)]
        self.culture_growth_model = CultureGrowthModel(**growth_parameters)
        self.culture_growth_model.updater = self.updater
        self.culture_growth_model.simulate_experiment()
        return plot_culture(self.culture_growth_model)

    def export_csv(self, output_directory=""):
        return export_culture_csv(self, output_directory=output_directory)

    def export_plot_html(self, output_directory=""):
        return export_culture_plot_html(self, output_directory=output_directory)

    def export_predicted_plot_html(self, output_directory=""):
        return export_culture_plot_html(self, output_directory=output_directory, predicted=True)

    def get_first_od_timestamp(self):
        with SessionLocal() as db:
            culture_data = db.query(CultureData).filter(
                CultureData.experiment_id == self.experiment.model.id,
                CultureData.vial_number == self.vial
            ).order_by(CultureData.timestamp).first()
        return culture_data.timestamp

    def get_latest_data_from_db(self):
        print("Getting latest data from db")
        with SessionLocal() as db:
            latest_culture_data = db.query(CultureData).filter(
                CultureData.experiment_id == self.experiment.model.id,
                CultureData.vial_number == self.vial).order_by(CultureData.timestamp.desc()).first()

            latest_generation_data = db.query(CultureGenerationData).filter(
                CultureGenerationData.experiment_id == self.experiment.model.id,
                CultureGenerationData.vial_number == self.vial).order_by(CultureGenerationData.timestamp.desc()).first()
            if latest_generation_data is not None:
                self.generation = latest_generation_data.generation
                self.drug_concentration = latest_generation_data.drug_concentration
                self.last_dilution_time = latest_generation_data.timestamp

            if latest_culture_data is not None:
                self.od = latest_culture_data.od
                if latest_culture_data.growth_rate is not None:
                    self.growth_rate = latest_culture_data.growth_rate
                else:
                    latest_generation_data = db.query(CultureGenerationData).filter(
                        CultureGenerationData.experiment_id == self.experiment.model.id,
                        CultureGenerationData.vial_number == self.vial).order_by(
                        CultureGenerationData.timestamp.desc()).limit(20).all()
                    for d in latest_generation_data:
                        if hasattr(d, "growth_rate"):
                            if d.growth_rate is not None:
                                self.growth_rate = d.growth_rate
                                break

            gen_data = db.query(CultureGenerationData).filter(
                CultureGenerationData.experiment_id == self.experiment.model.id,
                CultureGenerationData.vial_number == self.vial
            ).order_by(CultureGenerationData.timestamp).all()
            if len(gen_data) > 0:
                last_stress_increase_generation = gen_data[0].generation
                for i in range(len(gen_data) - 1):
                    c1 = gen_data[i].drug_concentration
                    c2 = gen_data[i + 1].drug_concentration
                    if c2 > c1:
                        if c1 == 0 or (c2-c1)/c1 > 0.01:
                            last_stress_increase_generation = gen_data[i + 1].generation
                self.last_stress_increase_generation = last_stress_increase_generation

    def get_data_at_timepoint(self, timepoint):
        self.parameters = AutoCommitDict(
            self.experiment.model.parameters["cultures"][str(self.vial)],
            vial=self.vial,
            db_session=None,  # Will be set per operation
            experiment_model=self.experiment.model)

        with SessionLocal() as db:
            # Get the last culture data for this culture
            latest_culture_data = db.query(CultureData).filter(
                CultureData.experiment_id == self.experiment.model.id,
                CultureData.vial_number == self.vial,
                CultureData.timestamp <= timepoint).order_by(CultureData.timestamp.desc()).first()

            # Get the last generation data for this culture
            latest_generation_data = db.query(CultureGenerationData).filter(
                CultureGenerationData.experiment_id == self.experiment.model.id,
                CultureGenerationData.vial_number == self.vial,
                CultureGenerationData.timestamp <= timepoint).order_by(CultureGenerationData.timestamp.desc()).first()

            if latest_generation_data is not None:
                self.generation = latest_generation_data.generation
                self.drug_concentration = latest_generation_data.drug_concentration
                self.last_dilution_time = latest_generation_data.timestamp

            if latest_culture_data is not None:
                self.od = latest_culture_data.od
                self.growth_rate = latest_culture_data.growth_rate

                # load latest drug increase
            gen_data = db.query(CultureGenerationData).filter(
                CultureGenerationData.experiment_id == self.experiment.model.id,
                CultureGenerationData.vial_number == self.vial,
                CultureGenerationData.timestamp <= timepoint
            ).order_by(CultureGenerationData.timestamp).all()
            if gen_data is not None:
                last_stress_increase_generation = 0
                for i in range(len(gen_data)-1):
                    c1 = gen_data[i].drug_concentration
                    c2 = gen_data[i + 1].drug_concentration
                    if c2 > c1:
                        if c1 == 0 or (c2-c1)/c1 > 0.01:
                            last_stress_increase_generation = gen_data[i+1].generation
                self.last_stress_increase_generation = last_stress_increase_generation

    def log_od_and_rpm(self, od=None, rpm=None):
        self.od = od
        self.new_culture_data = CultureData(
            experiment_id=self.experiment.model.id,
            vial_number=self.vial,
            od=od, growth_rate=None, rpm=rpm)
        with SessionLocal() as db:
            db.add(self.new_culture_data)
            self.calculate_latest_growth_rate(db)
            if self.new_culture_data.growth_rate is not None:
                self.growth_rate = self.new_culture_data.growth_rate
            db.commit()
        self.get_latest_data_from_db()  # TODO: speed up by not querying the database again

    def log_pump_data(self, main_pump_volume, drug_pump_volume):
        new_pump_data = PumpData(
            experiment_id=self.experiment.model.id,
            vial_number=self.vial,
            volume_main=main_pump_volume,
            volume_drug=drug_pump_volume,
            volume_waste=main_pump_volume+drug_pump_volume)
        with SessionLocal() as db:
            db.add(new_pump_data)
            db.commit()
        self.get_latest_data_from_db()

        parameters = self.experiment.parameters
        parameters["stock_volume_main"] = float(parameters["stock_volume_main"]) - main_pump_volume
        parameters["stock_volume_drug"] = float(parameters["stock_volume_drug"]) - drug_pump_volume
        parameters["stock_volume_waste"] = float(parameters["stock_volume_waste"]
                                                 ) - main_pump_volume - drug_pump_volume
        self.experiment.parameters = parameters

    def log_generation(self, generation, concentration):
        self.generation = generation
        self.drug_concentration = concentration
        new_generation_data = CultureGenerationData(
            experiment_id=self.experiment.model.id,
            vial_number=self.vial,
            generation=generation,
            drug_concentration=concentration,
        )
        with SessionLocal() as db:
            db.add(new_generation_data)
            db.commit()
        self.get_latest_data_from_db()

    def _delete_all_records(self):
        with SessionLocal() as db:
            db.query(CultureData).filter(CultureData.experiment_id == self.experiment.model.id,
                                                  CultureData.vial_number == self.vial).delete()
            db.query(PumpData).filter(PumpData.experiment_id == self.experiment.model.id,
                                               PumpData.vial_number == self.vial).delete()
            db.query(CultureGenerationData
                              ).filter(CultureGenerationData.experiment_id == self.experiment.model.id,
                                       CultureGenerationData.vial_number == self.vial).delete()
            db.commit()

    def calculate_latest_growth_rate(self, db):
        od_dict, _, _ = self.get_last_ods_and_rpms(db=db, limit=200, include_current=True, since_pump=True)
        t = np.array(list(int(dt.timestamp()) for dt in od_dict.keys()))
        od = np.array([float(value) if value is not None else np.nan for value in od_dict.values()])
        if np.issubdtype(od.dtype, np.number):
            t = t[~np.isnan(od)]
            od = od[~np.isnan(od)]
            od[od <= 0] = 1e-6
            timepoint, mu, error = calculate_last_growth_rate(t, od)
            if np.isfinite(mu):
                self.new_culture_data.growth_rate = mu

    def get_last_ods_and_rpms(self, db=None, limit=100, include_current=False, since_pump=False):
        if db is None:
            with SessionLocal() as db:
                return self.get_last_ods_and_rpms(db, limit, include_current, since_pump)
        culture_data = db.query(CultureData).filter(
            CultureData.experiment_id == self.experiment.model.id,
            CultureData.vial_number == self.vial
        ).order_by(CultureData.timestamp.desc()).limit(limit).all()
        if since_pump and len(culture_data) > 0:
            if self.last_dilution_time is not None:
                culture_data = [data for data in culture_data if data.timestamp > self.last_dilution_time]
        od_dict = {data.timestamp: data.od for data in culture_data}
        mu_dict = {data.timestamp: data.growth_rate for data in culture_data}
        rpm_dict = {data.timestamp: data.rpm for data in culture_data}
        if include_current and self.new_culture_data is not None:
            od_dict[self.new_culture_data.timestamp] = self.new_culture_data.od
        od_dict = {k: v for k, v in od_dict.items() if v is not None and k is not None}
        mu_dict = {k: v for k, v in mu_dict.items() if v is not None and k is not None}
        rpm_dict = {k: v for k, v in rpm_dict.items() if v is not None and k is not None}
        od_dict = {k: v for k, v in sorted(od_dict.items(), key=lambda item: item[0])}
        mu_dict = {k: v for k, v in sorted(mu_dict.items(), key=lambda item: item[0])}
        rpm_dict = {k: v for k, v in sorted(rpm_dict.items(), key=lambda item: item[0])}
        return od_dict, mu_dict, rpm_dict

    def get_last_generations(self, limit=1000):
        with SessionLocal() as db:
            generation_data = db.query(CultureGenerationData).filter(
                CultureGenerationData.experiment_id == self.experiment.model.id,
                CultureGenerationData.vial_number == self.vial
            ).order_by(CultureGenerationData.timestamp.desc()).limit(limit).all()
            generation_dict = {data.timestamp: data.generation for data in generation_data}
            concentration_dict = {data.timestamp: data.drug_concentration for data in generation_data}

            generation_dict = {k: v for k, v in sorted(generation_dict.items(), key=lambda item: item[0])}
            concentration_dict = {k: v for k, v in sorted(concentration_dict.items(), key=lambda item: item[0])}
            return generation_dict, concentration_dict

    def make_culture_dilution(self, target_concentration=None, dilution_factor=None, current_volume=None, postfill=False):
        if self.drug_concentration is None:
            self.drug_concentration = self.parameters["pump1_stock_drug_concentration"]
        if target_concentration is None:
            target_concentration = self.drug_concentration
        main_pump_volume, drug_pump_volume = self.calculate_pump_volumes(target_concentration=target_concentration,
                                                                         dilution_factor=dilution_factor,
                                                                         current_volume=current_volume)
        lock_acquired_here = False
        self.updater.status_dict["dilution_pump_volumes"] = "current_concentration: %.2f, target_concentration: %.2f, main_pump_volume: %.2f, drug_pump_volume: %.2f" % (
            self.drug_concentration, target_concentration, main_pump_volume, drug_pump_volume)
        try:
            if not self.experiment.locks[self.vial].locked():
                self.experiment.locks[self.vial].acquire(blocking=True)
                lock_acquired_here = True
            postfill = self.parameters["postfill"] > 0
            with SessionLocal() as db:
                make_device_dilution(device=self.experiment.device,
                                     vial=self.vial,
                                     pump1_volume=main_pump_volume,
                                     pump2_volume=drug_pump_volume,
                                     extra_vacuum=5,
                                     postfill=postfill)
            self.last_dilution_time = datetime.now()
            self.log_pump_data(main_pump_volume, drug_pump_volume)
            self.calculate_generation_concentration_after_dil(main_pump_volume=main_pump_volume,
                                                              drug_pump_volume=drug_pump_volume)
        finally:
            if lock_acquired_here:
                self.experiment.locks[self.vial].release()

    def calculate_pump_volumes(self, target_concentration, dilution_factor=None, current_volume=None):
        if dilution_factor is None:
            dilution_factor = self.parameters["dilution_factor"]
        if current_volume is None:
            current_volume = self.parameters["volume_vial"]

        total_vial_volume = 40 # ml
        current_volume = min(max(current_volume, 0.5), total_vial_volume)  # Ensure current volume is within bounds
        added_volume = current_volume * (dilution_factor - 1)  # Calculate the volume to be added
        added_volume = min(added_volume, total_vial_volume - current_volume)  # Ensure added volume is within bounds
        stock1_concentration = self.parameters["pump1_stock_drug_concentration"]
        stock2_concentration = self.parameters["pump2_stock_drug_concentration"]
        max_added_amount = added_volume * max(stock1_concentration, stock2_concentration)
        if self.drug_concentration is None:
            self.drug_concentration = self.parameters["pump1_stock_drug_concentration"]
        current_concentration = self.drug_concentration
        current_amount = current_concentration * current_volume
        total_volume = current_volume + added_volume
        added_amount = target_concentration * total_volume - current_amount
        added_amount = max(added_amount, 0)
        added_amount = min(added_amount, max_added_amount)
        added_concentration = added_amount / added_volume

        # pump1_volume * stock1_concentration + pump2_volume * stock2_concentration = added_volume * added_concentration
        # pump1_volume + pump2_volume = added_volume
        # solve for pump1_volume and pump2_volume, handling the case where stock1_concentration == stock2_concentration and stock1_concentration > stock2_concentration and stock1_concentration < stock2_concentration
        if stock1_concentration == stock2_concentration:
            main_pump_volume = added_volume / 2
            drug_pump_volume = added_volume / 2

        elif stock1_concentration > stock2_concentration:
            drug_pump_volume = added_volume * (stock1_concentration - added_concentration) / (stock1_concentration - stock2_concentration)
            main_pump_volume = added_volume - drug_pump_volume
        else:
            main_pump_volume = added_volume * (added_concentration - stock2_concentration) / (stock1_concentration - stock2_concentration)
            drug_pump_volume = added_volume - main_pump_volume

        main_pump_volume = min(max(main_pump_volume, 0), added_volume)
        drug_pump_volume = min(max(drug_pump_volume, 0), added_volume)
        self.updater.status_dict["pump_volume_calculations"] = "current_concentration: %.2f, target_concentration: %.2f, current_volume: %.2f, added_volume: %.2f, added_concentration: %.2f, main_pump_volume: %.2f, drug_pump_volume: %.2f" % (
            current_concentration, target_concentration, current_volume, added_volume, added_concentration, main_pump_volume, drug_pump_volume)

        return main_pump_volume, drug_pump_volume

    def calculate_generation_concentration_after_dil(self, main_pump_volume, drug_pump_volume):
        v0 = self.parameters["volume_vial"]
        total_volume = v0 + main_pump_volume + drug_pump_volume
        dilution_factor = total_volume / v0
        if self.generation is None:
            generation = np.log2(dilution_factor)
        else:
            generation = self.generation + np.log2(dilution_factor)
        try:
            stock1_concentration = self.parameters["pump1_stock_drug_concentration"]
        except KeyError:
            stock1_concentration = 0
        stock2_concentration = self.parameters["pump2_stock_drug_concentration"]

        # Calculate the new drug concentration after dilution and adding drug
        drug_concentration = (v0 * self.drug_concentration + main_pump_volume * stock1_concentration +
                              drug_pump_volume * stock2_concentration) / total_volume
        self.log_generation(generation, drug_concentration)  # also stores to self
        self.get_latest_data_from_db()  # TODO: speed up by not querying db again

    def get_culture_status_dict(self):
        culture_info = {
            "od": self.od,
            "growth_rate": self.growth_rate,
            "drug_concentration": self.drug_concentration,
            "generation": self.generation,
            "last_stress_increase_generation": self.last_stress_increase_generation,
            "last_dilution_time": self.last_dilution_time,
            "parameters": self.parameters.inner_dict,
            "updater_status": self.updater.status_dict,
        }
        return culture_info



