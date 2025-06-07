import os
from logger.logger import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import functools
from sqlalchemy.orm import Session
# Always resolve db_path as absolute path relative to the project root
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'db', 'replifactory.db'))

# Print the resolved path for debugging
logger.info(f"Resolved DB path: {db_path}")

# Check if db exists
if not os.path.exists(db_path):
    raise FileNotFoundError(f"Database file not found at {db_path}")
else:
    logger.info(f"Database file found at {db_path}")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"


def get_db():
    """Module-level FastAPI dependency for DB session, uses the singleton manager's session factory."""
    db = experiment_manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()

from threading import Lock
from experiment.database_models import db
from experiment.experiment import Experiment
from experiment.database_models import ExperimentModel
from minimal_device.base_device import BaseDevice
from experiment.exceptions import ExperimentNotFound
import os
from logger.logger import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'db', 'replifactory.db'))
logger.info(f"Resolved DB path: {db_path}")

if not os.path.exists(db_path):
    raise FileNotFoundError(f"Database file not found at {db_path}")
else:
    logger.info(f"Database file found at {db_path}")

def with_db_session(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        # logger.info(f"kwargs initial: {kwargs}")        # check if db_session is in kwargs or args. check if args contains type Session
        if 'db_session' in kwargs:
            db_session = kwargs.pop('db_session')
        elif any(isinstance(arg, Session) for arg in args):
            db_session = next(arg for arg in args if isinstance(arg, Session))
            args = tuple(arg for arg in args if arg != db_session)
        else:
            db_session = None
        if db_session is not None:
            # logger.info(f"Using provided db_session")
            return method(self, *args, db_session=db_session, **kwargs)
        else:
            with self.get_session() as db:
                logger.info(f"Using new db_session")
                return method(self, *args, db_session=db, **kwargs)
    return wrapper

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
        self.SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
        self.engine = create_engine(self.SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self._current_experiment_obj = None
        self._device = None
        self._exp_lock = Lock()  # For experiment state
        self._db = db  # Use the imported db object

    @property
    def experiment(self):
        return self._current_experiment_obj
    
    @property
    def device(self):
        return self._device
    
    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def get_session(self):
        return self.SessionLocal()

    def set_blank_device(self):
        self._device = BaseDevice(connect=False)

    def connect_device(self):
        self.set_blank_device()
        self._device.connect()
        self._device.hello_quick()
        if self._current_experiment_obj is not None:
            self._current_experiment_obj.device = self._device

    @with_db_session
    def set_current_experiment(self, experiment_id, db_session=None):
        with self._exp_lock:
            self._current_experiment_obj = Experiment(self._device, experiment_id, manager=self)
            self._current_experiment_obj.model = db_session.query(ExperimentModel).get(experiment_id)

    @with_db_session
    def create_experiment(self, name, parameters, db_session=None):
        experiment = ExperimentModel(name=name, parameters=parameters)
        db_session.add(experiment)
        db_session.commit()
        db_session.refresh(experiment)
        return experiment

    @with_db_session
    def select_experiment(self, experiment_id, db_session=None):
        experiment_model = db_session.query(ExperimentModel).get(experiment_id)
        if not experiment_model:
            raise ExperimentNotFound(f"Experiment {experiment_id} not found")
        self.set_current_experiment(experiment_id, db_session=db_session)
        return self.experiment

    @with_db_session
    def get_all_experiments(self, db_session=None):
        all_experiments = db_session.query(ExperimentModel).all()
        logger.info(f"All experiments: {all_experiments}")
        return all_experiments

    @with_db_session
    def get_experiment_by_id(self, experiment_id, db_session=None):
        experiment = db_session.query(ExperimentModel).get(experiment_id)
        if not experiment:
            raise ExperimentNotFound(f"Experiment {experiment_id} not found")
        return experiment

    @with_db_session
    def get_current_experiment_growth_parameters(self, db_session=None):
        experiment = self.get_current_experiment(db_session)
        if experiment is None:
            raise ExperimentNotFound("No current experiment set")
        return experiment.model.parameters.get("growth_parameters", {})

    @with_db_session
    def update_current_experiment_parameters(self, parameters, db_session=None):
        experiment = self.experiment
        if experiment is None:
            raise ExperimentNotFound("No current experiment set")
        old_parameters = experiment.model.parameters.copy()
        old_parameters["parameters"] = parameters
        self.experiment.parameters = parameters
        db_session.commit()
        experiment.reload_model_from_db(db_session)
        for culture in experiment.cultures.values():
            culture.update_parameters_from_experiment()
        return experiment.model.parameters

    @with_db_session
    def update_current_experiment_growth_parameters(self, growth_parameters, db_session=None):
        experiment = self.experiment
        if experiment is None:
            raise ExperimentNotFound("No current experiment set")
        old_parameters = experiment.model.parameters.copy()
        old_parameters["growth_parameters"] = growth_parameters
        experiment.parameters = old_parameters
        db_session.commit()
        for culture in experiment.cultures.values():
            culture.update_parameters_from_experiment()
        return experiment.model.parameters["growth_parameters"]

    def update_experiment_status(self, status, db_session=None):
        experiment = self.get_current_experiment(db_session)
        if experiment is None:
            raise ExperimentNotFound("No current experiment set")
        experiment.model.status = status
        db_session.commit()
        return {"message": f"Experiment {status}"}

    
    def shutdown(self):
        """Gracefully stop all device and worker threads."""
        device = self._device  # Use the current device reference directly
        if device is None:
            logger.info("No device to shut down.")
            return
        # Only attempt to stop workers if the device is connected
        try:
            if hasattr(device, 'is_connected') and not device.is_connected():
                logger.info("Device is not connected. No shutdown actions needed.")
                return
            if hasattr(device, 'eeprom') and hasattr(device.eeprom, 'writer'):
                device.eeprom.writer.stop()
                logger.info("EEPROM writer stopped cleanly.")
            if hasattr(device, 'od_worker') and device.od_worker is not None:
                logger.info("Stopping od_worker thread...")
                device.od_worker.stop()
                logger.info("od_worker stopped cleanly.")
            if hasattr(device, 'dilution_worker') and device.dilution_worker is not None:
                logger.info("Stopping dilution_worker thread...")
                device.dilution_worker.stop()
                logger.info("dilution_worker stopped cleanly.")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def get_clean_experiment(self):
        """Return a clean (default/template) experiment dict."""
        return {"id": 0, "name": "---- default template ----", "status": "stopped"}



experiment_manager = ExperimentManager()
