from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Experiment(Base):
    __tablename__ = 'experiments'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    cultures = relationship('Culture', back_populates='experiment')

class Culture(Base):
    __tablename__ = 'cultures'

    id = Column(Integer, primary_key=True)
    type = Column(String, default='inactive')
    parameters = Column(JSON, default={})
    active_parameters = Column(JSON, default={})

    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    experiment = relationship('Experiment', back_populates='cultures')




CULTURE_TYPES = {
    "batch": ["od", "growth_rate", "volume"],
    "chemostat": ["od", "growth_rate", "volume", "dilution_rate", "dilution_volume", "dead_volume"],
    "turbidostat": ["od", "growth_rate", "volume", "od_threshold", "dilution_volume", "dead_volume"],
    "morbidostat": ["od", "growth_rate", "volume", "od_threshold", "dilution_volume", "dead_volume"],
    "inactive": []
}

def change_culture_type(culture_id, new_type):
    # Get the culture from the database
    culture = session.query(Culture).filter(Culture.id == culture_id).first()

    # Update the culture type
    culture.type = new_type

    # Update the active parameters based on the new type
    culture.active_parameters = {k: v for k, v in culture.parameters.items() if k in CULTURE_TYPES[new_type]}

    # Commit the session to save changes to the database
    session.commit()
