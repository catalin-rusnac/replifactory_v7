from datetime import datetime, timedelta

import numpy as np
from experiment.database_models import CultureData, PumpData, CultureGenerationData
from experiment.growth_rate import calculate_last_growth_rate
from experiment.ModelBasedCulture.morbidostat_updater import MorbidostatUpdater
from minimal_device.dilution import make_device_dilution
from logger.logger import logger


from .ModelBasedCulture.culture_growth_model import CultureGrowthModel
from .ModelBasedCulture.real_culture_wrapper import RealCultureWrapper
from .database_models import ExperimentModel, CultureData, PumpData, CultureGenerationData
from .plot import plot_culture
from .export import export_culture_csv, export_culture_plot_html
from copy import deepcopy

from copy import deepcopy

class AutoCommitDict:
    def __init__(self, initial_dict, experiment_manager, experiment_id, vial):
        self.inner_dict = deepcopy(initial_dict)
        self.experiment_manager = experiment_manager
        self.experiment_id = experiment_id
        self.vial = int(vial)

    def __getitem__(self, key):
        # Always read from the in-memory dict
        try:
            return float(self.inner_dict[key])
        except ValueError:
            return self.inner_dict[key]

    def __setitem__(self, key, value):
        self.inner_dict[key] = value
        # Update database immediately with fresh session
        with self.experiment_manager.get_session() as session:
            experiment = session.query(ExperimentModel).get(self.experiment_id)
            if experiment is None:
                raise ValueError("Experiment not found")
            parameters = deepcopy(experiment.parameters)
            # Ensure all keys are strings for cultures
            parameters["cultures"] = {str(k): v for k, v in parameters.get("cultures", {}).items()}
            parameters["cultures"][self.vial] = self.inner_dict.copy()
            experiment.parameters = parameters
            session.commit()
            session.refresh(experiment.model)

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
                        experiment_manager=experiment.manager, 
                        experiment_id=experiment.model.id, 
                        vial=self.vial)
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
    
    def plot_data(self, *args, **kwargs):
        return plot_culture(self, *args, **kwargs)

    def plot_predicted(self, rerun=True, simulation_hours=48, title=None):
        if rerun:
            self.updater = MorbidostatUpdater(**self.parameters.inner_dict)
            growth_parameters = self.experiment.model.parameters["growth_parameters"][str(self.vial)]
            self.culture_growth_model = CultureGrowthModel(**growth_parameters)
            self.culture_growth_model.vial = "%d(simulated)" % self.vial
            self.culture_growth_model.updater = self.updater
            self.culture_growth_model.simulate_experiment(simulation_hours=simulation_hours)
        return plot_culture(self.culture_growth_model, title=title)
    
    def run_and_save_simulation(self, simulation_hours=48):
        self.updater = MorbidostatUpdater(**self.parameters.inner_dict)
        growth_parameters = self.experiment.model.parameters["growth_parameters"][str(self.vial)]
        self.culture_growth_model = CultureGrowthModel(**growth_parameters)
        self.culture_growth_model.vial = "%d(simulated)" % self.vial
        self.culture_growth_model.updater = self.updater
        self.culture_growth_model.simulate_experiment(simulation_hours=simulation_hours)
        return True

    def export_csv(self, output_directory=""):
        return export_culture_csv(self, output_directory=output_directory)

    def export_plot_html(self, output_directory=""):
        return export_culture_plot_html(self, output_directory=output_directory)

    def export_predicted_plot_html(self, output_directory=""):
        return export_culture_plot_html(self, output_directory=output_directory, predicted=True)

    def get_first_od_timestamp(self):
        with self.experiment.manager.get_session() as db:
            culture_data = db.query(CultureData).filter(
                CultureData.experiment_id == self.experiment.model.id,
                CultureData.vial_number == self.vial
            ).order_by(CultureData.timestamp).first()
        if culture_data is None:
            return None
        return culture_data.timestamp

    def get_last_od_timestamp(self):
        with self.experiment.manager.get_session() as db:
            culture_data = db.query(CultureData).filter(
                CultureData.experiment_id == self.experiment.model.id,
                CultureData.vial_number == self.vial
            ).order_by(CultureData.timestamp.desc()).first()
        if culture_data is None:
            return None
        return culture_data.timestamp

    def update_parameters_from_experiment(self):
        self.parameters = AutoCommitDict(
            self.experiment.model.parameters["cultures"][str(self.vial)],
            experiment_manager=self.experiment.manager, 
            experiment_id=self.experiment.model.id, 
            vial=self.vial)
        self.growth_parameters = self.experiment.model.parameters["growth_parameters"][str(self.vial)]
        self.culture_growth_model = CultureGrowthModel(**self.growth_parameters)
        self.culture_growth_model.vial = "%d(simulated)" % self.vial
        self.updater = MorbidostatUpdater(**self.parameters.inner_dict)

    
    def get_latest_data_from_db(self, db_session=None):
        # logger.info(f"Getting latest data from db for culture {self.vial}. current parameters: {self.parameters}")
        if db_session is None:
            db_session = self.experiment.manager.get_session()

        with db_session as db:
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
        # logger.info(f"Latest data from db for culture {self.vial} after update: {self.parameters}")

    def get_data_at_timepoint(self, timepoint):
        self.parameters = AutoCommitDict(
            experiment_manager=self.experiment.manager,
            experiment_id=self.experiment.model.id,
            vial=self.vial)

        with self.experiment.manager.get_session() as db:
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
        with self.experiment.manager.get_session() as db:
            db.add(self.new_culture_data) 
            self.calculate_latest_growth_rate(include_current=True)
            
            if self.new_culture_data.growth_rate is not None:
                self.growth_rate = self.new_culture_data.growth_rate
            db.commit()
            # timestamp is added by db at the time of commit
        self.get_latest_data_from_db()  # TODO: speed up by not querying the database again

    def log_pump_data(self, main_pump_volume, drug_pump_volume):
        new_pump_data = PumpData(
            experiment_id=self.experiment.model.id,
            vial_number=self.vial,
            volume_main=main_pump_volume,
            volume_drug=drug_pump_volume,
            volume_waste=main_pump_volume+drug_pump_volume)
        with self.experiment.manager.get_session() as db:
            db.add(new_pump_data)
            db.commit()
        self.get_latest_data_from_db()

        parameters = self.experiment.parameters
        
        # Validate and handle NaN values for stock volumes
        def safe_float_conversion(value, default=0.0, param_name="unknown"):
            """Convert value to float, handling NaN and None cases"""
            try:
                if value is None:
                    logger.warning(f"Parameter {param_name} is None, using default {default}")
                    return default
                result = float(value)
                if not np.isfinite(result):  # Handles NaN and infinity
                    logger.warning(f"Parameter {param_name} is {result}, using default {default}")
                    return default
                return result
            except (ValueError, TypeError):
                logger.warning(f"Could not convert {param_name} value '{value}' to float, using default {default}")
                return default
        
        # Safe conversion of stock volumes
        current_main = safe_float_conversion(parameters["stock_volume_main"], 0.0, "stock_volume_main")
        current_drug = safe_float_conversion(parameters["stock_volume_drug"], 0.0, "stock_volume_drug") 
        current_waste = safe_float_conversion(parameters["stock_volume_waste"], 0.0, "stock_volume_waste")
        
        parameters["stock_volume_main"] = current_main - main_pump_volume
        parameters["stock_volume_drug"] = current_drug - drug_pump_volume
        # Waste volume = pumped volume + extra vacuum (5mL as per dilution.py)
        actual_waste_volume = main_pump_volume + drug_pump_volume + 5
        parameters["stock_volume_waste"] = current_waste + actual_waste_volume
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
        with self.experiment.manager.get_session() as db:
            db.add(new_generation_data)
            db.commit()
        self.get_latest_data_from_db()

    def _delete_all_records(self):
        with self.experiment.manager.get_session() as db:
            db.query(CultureData).filter(CultureData.experiment_id == self.experiment.model.id,
                                                  CultureData.vial_number == self.vial).delete()
            db.query(PumpData).filter(PumpData.experiment_id == self.experiment.model.id,
                                               PumpData.vial_number == self.vial).delete()
            db.query(CultureGenerationData
                              ).filter(CultureGenerationData.experiment_id == self.experiment.model.id,
                                       CultureGenerationData.vial_number == self.vial).delete()
            db.commit()

    def calculate_latest_growth_rate(self, db=None, include_current=True):
        od_dict, _, _ = self.get_last_ods_and_rpms(db=db, limit=200, since_pump=True, include_current=include_current)
        t = np.array(list(int(dt.timestamp()) for dt in od_dict.keys()))
        od = np.array([float(value) if value is not None else np.nan for value in od_dict.values()])
        if np.issubdtype(od.dtype, np.number):
            t = t[~np.isnan(od)]
            od = od[~np.isnan(od)]
            od[od <= 0] = 1e-6
            timepoint, mu, error = calculate_last_growth_rate(t, od)
            if np.isfinite(mu):
                self.new_culture_data.growth_rate = mu

    def get_last_ods_and_rpms(self, db=None, limit=100, since_pump=False, include_current=False):
        if db is None:
            db = self.experiment.manager.get_session()

        with db as db:
        # Query and extract all needed data while session is open
            culture_data = db.query(CultureData).filter(
                CultureData.experiment_id == self.experiment.model.id,
                CultureData.vial_number == self.vial
            ).order_by(CultureData.timestamp.desc()).limit(limit).all()
            # Extract all relevant fields into a list of dicts
            extracted = []
            for row in culture_data:
                if row.timestamp is not None:
                    extracted.append({
                        "timestamp": row.timestamp,
                        "od": row.od,
                        "growth_rate": row.growth_rate,
                        "rpm": row.rpm
                    })
            # Optionally filter by last dilution time
            if since_pump and self.last_dilution_time is not None:
                extracted = [d for d in extracted if d["timestamp"] > self.last_dilution_time]
            # Build the result dicts
            od_dict = {d["timestamp"]: d["od"] for d in extracted if d["od"] is not None}
            mu_dict = {d["timestamp"]: d["growth_rate"] for d in extracted if d["growth_rate"] is not None}
            rpm_dict = {d["timestamp"]: d["rpm"] for d in extracted if d["rpm"] is not None}

            # Optionally include the current (not-yet-committed) data.
            if include_current:
                if self.new_culture_data is not None:
                    if hasattr(self.new_culture_data, "timestamp"):
                        new_od = self.new_culture_data.od
                        new_timestamp = self.new_culture_data.timestamp
                    if new_timestamp is not None and new_od is not None:
                        od_dict[new_timestamp] = new_od

        # Sort by timestamp
        od_dict = dict(sorted(od_dict.items()))
        mu_dict = dict(sorted(mu_dict.items()))
        rpm_dict = dict(sorted(rpm_dict.items()))
        return od_dict, mu_dict, rpm_dict


    def get_last_generations(self, limit=1000):
        db = self.experiment.manager.get_session()
        with db as db:
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

    def get_latest_od(self):
        """Get the latest OD measurement with timestamp"""
        if self.od is not None:
            od_dict, _, _ = self.get_last_ods_and_rpms(limit=1)
            if od_dict:
                latest_timestamp = max(od_dict.keys())
                return {
                    'value': self.od,
                    'timestamp': latest_timestamp
                }
        return None
    
    def get_current_growth_rate(self):
        """Get the current growth rate"""
        return self.growth_rate
    
    def get_total_dilution_count(self):
        """Get the total number of dilutions performed"""
        with self.experiment.manager.get_session() as db:
            count = db.query(PumpData).filter(
                PumpData.experiment_id == self.experiment.model.id,
                PumpData.vial_number == self.vial
            ).count()
            return count
    
    def get_last_dilution_time(self):
        """Get time since last dilution in human readable format"""
        if self.last_dilution_time is None:
            return None
        
        from datetime import datetime
        time_diff = datetime.now() - self.last_dilution_time
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m ago"
        else:
            return f"{minutes}m ago"
    
    def get_runtime(self):
        first_od_time = self.get_first_od_timestamp()
        if not first_od_time:
            return "0s"
        
        last_od_time = self.get_last_od_timestamp()
        if not last_od_time:
            last_od_time = first_od_time
            
        runtime_delta = last_od_time - first_od_time
        
        hours, remainder = divmod(runtime_delta.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"
    
    def get_volume_usage_1h(self):
        """Get medium and drug volume usage in the past hour"""
        from datetime import datetime, timedelta
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        with self.experiment.manager.get_session() as db:
            pump_data = db.query(PumpData).filter(
                PumpData.experiment_id == self.experiment.model.id,
                PumpData.vial_number == self.vial,
                PumpData.timestamp >= one_hour_ago
            ).all()
            
            medium_total = sum(p.volume_main for p in pump_data if p.volume_main)
            drug_total = sum(p.volume_drug for p in pump_data if p.volume_drug)
            
            return medium_total, drug_total
    
    def get_volume_usage_24h(self):
        """Get medium and drug volume usage in the past 24 hours"""
        from datetime import datetime, timedelta
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        
        with self.experiment.manager.get_session() as db:
            pump_data = db.query(PumpData).filter(
                PumpData.experiment_id == self.experiment.model.id,
                PumpData.vial_number == self.vial,
                PumpData.timestamp >= twenty_four_hours_ago
            ).all()
            
            medium_total = sum(p.volume_main for p in pump_data if p.volume_main)
            drug_total = sum(p.volume_drug for p in pump_data if p.volume_drug)
            
            return medium_total, drug_total
    
    def get_rpm_stats_1h(self):
        """Get RPM mean and standard deviation for the past hour"""
        from datetime import datetime, timedelta
        import statistics
        
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        with self.experiment.manager.get_session() as db:
            culture_data = db.query(CultureData).filter(
                CultureData.experiment_id == self.experiment.model.id,
                CultureData.vial_number == self.vial,
                CultureData.timestamp >= one_hour_ago,
                CultureData.rpm.isnot(None)
            ).all()
            
            rpm_values = [data.rpm for data in culture_data]
            
            if not rpm_values:
                return None, None
                
            mean_rpm = statistics.mean(rpm_values)
            std_rpm = statistics.stdev(rpm_values) if len(rpm_values) > 1 else 0.0
            
            return mean_rpm, std_rpm
    
    @staticmethod
    def get_all_vials_rpm_stats_1h(experiment_id, db_session):
        """Efficiently get RPM stats for all vials in one query"""
        from datetime import datetime, timedelta
        from sqlalchemy import func
        import statistics
        
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        # Get all RPM data for the experiment in the past hour
        culture_data = db_session.query(CultureData).filter(
            CultureData.experiment_id == experiment_id,
            CultureData.timestamp >= one_hour_ago,
            CultureData.rpm.isnot(None)
        ).all()
        
        # Group by vial and calculate statistics
        vial_rpm_data = {}
        for data in culture_data:
            vial = data.vial_number
            if vial not in vial_rpm_data:
                vial_rpm_data[vial] = []
            vial_rpm_data[vial].append(data.rpm)
        
        # Calculate mean and std for each vial
        rpm_stats = {}
        for vial, rpm_values in vial_rpm_data.items():
            if rpm_values:
                mean_rpm = statistics.mean(rpm_values)
                std_rpm = statistics.stdev(rpm_values) if len(rpm_values) > 1 else 0.0
                rpm_stats[vial] = {'mean': mean_rpm, 'std': std_rpm}
            else:
                rpm_stats[vial] = {'mean': None, 'std': None}
        
        return rpm_stats

    def get_last_dilution_timestamp(self):
        with self.experiment.manager.get_session() as db:
            last_dilution = db.query(PumpData).filter(
                PumpData.experiment_id == self.experiment.model.id,
                PumpData.vial_number == self.vial
            ).order_by(PumpData.timestamp.desc()).first()
        if last_dilution:
            return last_dilution.timestamp
        return None



