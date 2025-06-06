from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Database setup (moved from fastapi_db.py)
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, '../db/replifactory.db')
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from threading import Lock
from experiment.database_models import db
from experiment.experiment import Experiment
from experiment.database_models import ExperimentModel
from minimal_device.base_device import BaseDevice

class ExperimentManager:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_singleton()
        return cls._instance

    def _init_singleton(self):
        self._current_experiment_obj = None
        self._device = BaseDevice(connect=False)
        self._exp_lock = Lock()  # For experiment state
        self._db = db  # Use the imported db object

    @classmethod
    def get_instance(cls):
        return cls()

    def set_device(self, device=None):
        with self._lock:
            if device is not None:
                self._device = device
            elif self._device is None:
                self._device = BaseDevice(connect=False)
            # attach device to experiment if experiment is not none

    def get_device(self):
        with self._lock:
            if self._device is None:
                self._device = BaseDevice(connect=False)
            return self._device

    def set_current_experiment(self, experiment_id):
        with self._exp_lock:
            self._current_experiment_obj = Experiment(self._device, experiment_id)
    
    def stop_all_experiments_in_db(self, session):
        with self._exp_lock:
            self._current_experiment_obj = None
            for experiment in session.query(ExperimentModel).all():
                if experiment.status == 'running':
                    print("Stopping experiment", experiment.id)
                    experiment.status = 'stopped'
                    session.commit()

    def get_current_experiment(self):
        with self._exp_lock:
            return self._current_experiment_obj

    def clear_current_experiment(self):
        with self._exp_lock:
            self._current_experiment_obj = None

    def get_current_experiment_id(self):
        with self._lock:
            return self._current_experiment_obj.model.id if self._current_experiment_obj else None

    def connect_device(self):
        self._device.connect()
        self._device.hello_quick()
        if self._current_experiment_obj is not None:
            self._current_experiment_obj.device = self._device

    @property
    def device(self):
        return self.get_device()

    @device.setter
    def device(self, value):
        self.set_device(value)

    @property
    def experiment(self):
        return self.get_current_experiment()

    @experiment.setter
    def experiment(self, value):
        # value should be an Experiment instance
        with self._exp_lock:
            self._current_experiment_obj = value

# singleton experiment manager instance is initialized here. accessible globally with imports
experiment_manager = ExperimentManager()

# using experiment_manager outside of fastapi app:








