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


class CultureData(db.Model):
    __tablename__ = 'culture_data'

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False)
    vial_number = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    od_reading = db.Column(db.Float, nullable=False)
    growth_rate = db.Column(db.Float, nullable=False)

    # To represent the relationship between an experiment and its cultures
    experiment = db.relationship('ExperimentModel', backref='culture_data')

    def to_dict(self):
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'vial_number': self.vial_number,
            'timestamp': self.timestamp.isoformat(),
            'od_reading': self.od_reading,
            'growth_rate': self.growth_rate,
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
