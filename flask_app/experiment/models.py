# models.py

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON
db = SQLAlchemy()


class ExperimentModel(db.Model):
    __tablename__ = 'experiments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    status = db.Column(db.String(64), nullable=False, default='inactive')
    parameters = db.Column(JSON, nullable=False, default={
        'main_stock_volume': 2000,
        'drug_stock_volume': 1000,
        'waste_volume': 5000,
        'drug_stock_concentration': 0.1,
    })

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'parameters': self.parameters,
        }


class Culture(db.Model):
    __tablename__ = 'cultures'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False)

    parameters = db.Column(JSON, nullable=False, default={
        'dead_volume': 15,
        'od_threshold': 0.3,
    })
    active_parameters = db.Column(JSON, nullable=False, default={})

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'experiment_id': self.experiment_id,
            'parameters': self.parameters,
            'active_parameters': self.active_parameters}


class ExperimentParameterHistory(db.Model):
    __tablename__ = 'experiment_parameter_history'

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False)
    parameters = db.Column(JSON, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'parameters': self.parameters,
            'timestamp': self.timestamp,
        }


class CultureParameterHistory(db.Model):
    __tablename__ = 'culture_parameter_history'

    id = db.Column(db.Integer, primary_key=True)
    culture_id = db.Column(db.Integer, db.ForeignKey('cultures.id'), nullable=False)
    parameters = db.Column(JSON, nullable=False)
    active_parameters = db.Column(JSON, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'culture_id': self.culture_id,
            'parameters': self.parameters,
            'active_parameters': self.active_parameters,
            'timestamp': self.timestamp,
        }

