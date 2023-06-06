# models.py
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON
db = SQLAlchemy()

default_parameters = {"stock_concentration_drug": 100,
              "stock_volume_drug": 1000,
              "stock_volume_main": 2000,
              "stock_volume_waste": 5000,
              }
culture_parameters = {"name": "Species 1",
                      "description": "Strain 1",

                      "volume_fixed": 15,
                      "volume_added": 10,

                      "od_threshold": 0.3,
                      "od_threshold_first_dilution": 0.4,
                      "stress_dose_first_dilution": 2.0,

                      "stress_increase_delay_generations": 3.0,
                      "stress_increase_tdoubling_min_hrs": 4,

                      "stress_decrease_delay_hrs": 16,
                      "stress_decrease_tdoubling_max_hrs": 24,
                      }
default_parameters['cultures'] = {i: culture_parameters for i in range(1, 8)}


class ExperimentModel(db.Model):
    __tablename__ = 'experiments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    status = db.Column(db.String(64), nullable=False, default=lambda: "inactive")
    parameters = db.Column(JSON, nullable=False, default=lambda: default_parameters)

    def to_dict(self):
        parameters = self.parameters.copy()
        parameters['cultures'] = {int(key): value for key, value in parameters['cultures'].items()}
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'parameters': self.parameters,
}


class PumpData(db.Model):
    __tablename__ = 'pump_data'

    id = db.Column(db.Integer, primary_key=True)

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False, index=True)
    vial_number = db.Column(db.Integer, nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.now, index=True)

    volume_main = db.Column(db.Float, nullable=False)
    volume_drug = db.Column(db.Float, nullable=False)
    volume_waste = db.Column(db.Float, nullable=False)
    # To represent the relationship between an experiment and its pump data
    experiment = db.relationship('ExperimentModel', backref='pump_data')

    def to_dict(self):
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'vial_number': self.vial_number,
            'timestamp': self.timestamp.isoformat(),
            'volume_main': self.volume_main,
            'volume_drug': self.volume_drug,
            'volume_waste': self.volume_waste
        }


class CultureGenerationData(db.Model):
    __tablename__ = 'generation_data'

    id = db.Column(db.Integer, primary_key=True)

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False, index=True)
    vial_number = db.Column(db.Integer, nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.now, index=True)

    generation = db.Column(db.Integer, nullable=False)
    drug_concentration = db.Column(db.Float, nullable=False)

    # To represent the relationship between an experiment and its cultures
    experiment = db.relationship('ExperimentModel', backref='generation_data')

    def to_dict(self):
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'vial_number': self.vial_number,
            'timestamp': self.timestamp.isoformat(),
            'generation': self.generation,
            'drug_concentration': self.drug_concentration
        }


class CultureData(db.Model):
    __tablename__ = 'culture_data'

    id = db.Column(db.Integer, primary_key=True)

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False, index=True)
    vial_number = db.Column(db.Integer, nullable=False,index=True)
    timestamp = db.Column(db.DateTime, default=datetime.now, index=True)

    od = db.Column(db.Float, nullable=True)
    growth_rate = db.Column(db.Float, nullable=True)

    # To represent the relationship between an experiment and its cultures
    experiment = db.relationship('ExperimentModel', backref='culture_data')

    def to_dict(self):
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'vial_number': self.vial_number,
            'timestamp': self.timestamp.isoformat(),
            'od': self.od_reading,
            'growth_rate': self.growth_rate}


# class Culture(db.Model):
#     __tablename__ = 'cultures'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(64), nullable=False)
#     experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False)
#
#     parameters = db.Column(JSON, nullable=False, default={
#         'dead_volume': 15,
#         'od_threshold': 0.3,
#     })
#     active_parameters = db.Column(JSON, nullable=False, default={})
#
#     def to_dict(self):
#         return {
#             'id': self.id,
#             'name': self.name,
#             'experiment_id': self.experiment_id,
#             'parameters': self.parameters,
#             'active_parameters': self.active_parameters}
