import os
from logger.logger import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import functools
from sqlalchemy.orm import Session
from experiment.database_models import default_parameters
# Always resolve db_path as absolute path relative to the project root
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'db', 'replifactory.db'))
if not os.path.exists(db_path):
    raise FileNotFoundError(f"Database file not found at {db_path}")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

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
import asyncio
from fastapi import WebSocket

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
        self.fix_inconsistent_experiment_states()
        self.active_sockets = set()
        self.main_event_loop = None

    @property
    def experiment(self):
        return self._current_experiment_obj
    
    @property
    def device(self):
        return self._device
    
    def get_db(self):
        db = self.SessionLocal()
        try:
            # logger.info(f"Yielding db")
            yield db
        finally:
            db.close()

    def get_session(self):
        # logger.info(f"Getting session")
        return self.SessionLocal()

    def connect_device(self):
        logger.info(f"Connecting device")
        try: 
            if self._device is not None:
                self._device.shutdown()
                time.sleep(2)
        except:
            logger.error(f"Error shutting down device")
        if self._device is None:
            self._device = BaseDevice(connect=False)
        self._device.connect()
        self._device.hello_quick()
        if self._current_experiment_obj is not None:
            self._current_experiment_obj.device = self._device
    
    def get_status(self):
        status_dict = {"device": None, "experiment": None}
        try:
            status_dict["device"] = self._device.status
        except:
            status_dict["device"] = "disconnected"
        try:
            status_dict["experiment"] = self.experiment.status
        except:
            status_dict["experiment"] = "not running"
        try:
            status_dict["cultures"] = {i: self._current_experiment_obj.cultures[i].status for i in range(1, 8)}
        except:
            status_dict["cultures"] = {i: "not running" for i in range(1, 8)}
        return status_dict
    
    # @with_db_session
    # def set_current_experiment(self, experiment_id, db_session=None):
    #     if self.experiment is not None:
    #         if self.experiment.is_running():
    #             self.experiment.stop()
    #     with self._exp_lock:
    #         if experiment_id == 0:
    #             self._current_experiment_obj = None
    #         else:
    #             self._current_experiment_obj = Experiment(self._device, experiment_id, manager=self)
    #             self._current_experiment_obj.model = db_session.query(ExperimentModel).get(experiment_id)

    @with_db_session
    def create_experiment(self, name, db_session=None):
        new_experiment_parameters = default_parameters
        if self.experiment is not None:
            current_experiment_id = self.experiment.model.id
            new_experiment_parameters = self.experiment.parameters.copy()
            logger.info(f"Copying parameters from current experiment {current_experiment_id} {self.experiment.model.name}")
        
        experiment_model = ExperimentModel(name=name, parameters=new_experiment_parameters)
        db_session.add(experiment_model)
        db_session.commit()
        db_session.refresh(experiment_model)
        self.select_experiment(experiment_model.id, db_session=db_session)
        logger.info(f"Created experiment {experiment_model.id} {experiment_model.name}")
        return self.experiment

    @with_db_session
    def select_experiment(self, experiment_id, db_session=None):
        if self.experiment is not None:
            if self.experiment.is_running():
                if self.experiment.model.id == experiment_id:
                    return self.experiment
                else:
                    logger.info(f"Stopping experiment {self.experiment.model.id} {self.experiment.model.name} because it is running")
                    self.experiment.stop()
        if experiment_id == 0:
            self._current_experiment_obj = None
            return None
        self._current_experiment_obj = Experiment(self._device, experiment_id, manager=self)
        self._current_experiment_obj.model = db_session.query(ExperimentModel).get(experiment_id)
        return self.experiment
    
    def get_default_experiment(self):
        """Return a clean (default/template) experiment dict."""
        experiment_model = ExperimentModel(name="---- default template ----", parameters={}, status="stopped")
        experiment_model.id = 0
        return experiment_model

    @with_db_session
    def get_all_experiments(self, db_session=None):
        default_experiment = self.get_default_experiment()
        all_experiments = db_session.query(ExperimentModel).all()
        return [default_experiment] + all_experiments

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
        self.experiment.parameters = old_parameters
        db_session.commit()
        for culture in experiment.cultures.values():
            culture.update_parameters_from_experiment()
        return experiment.model.parameters["growth_parameters"]

    @with_db_session
    def can_start_experiment(self, db_session=None):
        running = db_session.query(ExperimentModel).filter(ExperimentModel.status == 'running').first()
        if running:
            return False, f"Cannot start: experiment {running.name} is already running"
        paused = db_session.query(ExperimentModel).filter(ExperimentModel.status == 'paused').first()
        if paused and paused.id != self.experiment.model.id:
            return False, f"Cannot start: experiment {paused.name} is paused"
        return True, None

    @with_db_session
    def stop_experiment(self, db_session=None):
        experiment = self.experiment
        if experiment is None:
            return {'message': 'No current experiment set'}
        if experiment.model.status == 'stopped':
            # emit ws message with error type
            self.emit_ws_message({"type": "error", "message": "Experiment is already stopped"})
            return {'message': 'Experiment is already stopped'}
        experiment.stop()
        db_session.commit()
        return {"message": "Experiment stopped"}

    @with_db_session
    def update_experiment_status(self, status, db_session=None):
        experiment = self.experiment
        if experiment is None:
            return {'error': 'No current experiment set'}
        if status == 'running':
            ok, msg = self.can_start_experiment(db_session)
            if not ok:
                return {'error': msg}
            self.experiment.start()
        if status == 'stopped':
            self.stop_experiment(db_session=db_session)
            return {"message": "Experiment stopped"}
        db_session.commit()
        return {"message": f"Experiment {status}"}

    def shutdown(self):
        """Gracefully stop all device and worker threads."""
        import threading
        logger.info(f"Threads at shutdown: {threading.enumerate()}")
        # Only attempt to stop workers if the device is connected
        if self.experiment is not None:
            if self.experiment.is_running():
                self.experiment.stop()
        if self._device is not None:
            self._device.shutdown()

    @with_db_session
    def fix_inconsistent_experiment_states(self, db_session=None):
        logger.info(f"Fixing inconsistent experiment states (if not stopped or inactive)")
        not_stopped_or_inactive = db_session.query(ExperimentModel).filter(
            ExperimentModel.status.not_in(['stopped', 'inactive'])
        ).all()
        for exp in not_stopped_or_inactive:
            exp.status = 'stopped'
            logger.warning(f"Fixed experiment {exp.id} {exp.name} from {exp.status} to stopped")
        db_session.commit()
        if not_stopped_or_inactive:
            logger.warning(f"Fixed {len(not_stopped_or_inactive)} experiments left in running/paused state.")

    def register_socket(self, ws: WebSocket):
        print(f"Adding ws id: {id(ws)} to active_sockets")
        self.active_sockets.add(ws)

    def unregister_socket(self, ws: WebSocket):
        if ws in self.active_sockets:
            print(f"Removing ws id: {id(ws)} from active_sockets")
            self.active_sockets.remove(ws)

    async def broadcast(self, message):
        for ws in list(self.active_sockets):
            logger.info(f"Broadcasting to ws {id(ws)} with debug_id {message.get('debug_id')}. number of active sockets: {len(self.active_sockets)}")
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"Error sending to ws {id(ws)}: {e}")

    def emit_ws_message(self, message):
        future = asyncio.run_coroutine_threadsafe(self.broadcast(message), self.main_event_loop)
        def log_if_exception(fut):
            try:
                fut.result()
            except Exception as e:
                print(f"Exception in broadcast: {e}")
        future.add_done_callback(log_if_exception)

experiment_manager = ExperimentManager()
