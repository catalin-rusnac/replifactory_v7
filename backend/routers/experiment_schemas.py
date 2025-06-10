from pydantic import BaseModel
from typing import Optional, Dict

class ExperimentCreate(BaseModel):
    name: str

class ExperimentOut(BaseModel):
    id: int
    name: str
    status: str
    parameters: dict
    model_config = {"from_attributes": True}

class SelectExperimentIn(BaseModel):
    experiment_id: int

class SetCurrentExperimentIn(BaseModel):
    experiment_id: int

class ParametersUpdate(BaseModel):
    parameters: dict
