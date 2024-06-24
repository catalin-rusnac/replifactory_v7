import traceback
import threading
import time
import queue

import sys
import io
from copy import deepcopy
from pprint import pformat, pprint

import numpy as np
import schedule
from experiment.database_models import ExperimentModel
from .ModelBasedCulture.culture_growth_model import culture_growth_model_default_parameters
from .ModelBasedCulture.morbidostat_updater import morbidostat_updater_default_parameters
from .culture import Culture
from flask import current_app


class ExperimentWorker:
    def __init__(self, experiment):
        self.experiment = experiment
        self.od_worker = QueueWorker(experiment=self.experiment, worker_name='OD_worker')
        self.dilution_worker = QueueWorker(experiment=self.experiment, worker_name='Dilution_worker')
        self.thread = threading.Thread(target=self.run_loop, daemon=False)
        self.thread.start()

    def run_loop(self):
        print('Experiment worker started')
        self.experiment.device.valves.close_all()
        self.experiment.device.eeprom.save_config_to_eeprom()
        while True:
            status = self.experiment.get_status()
            if status == 'stopped':
                self.stop()
                break
            else:
                self.experiment.schedule.run_pending()
                # print("ran pending", time.ctime())
            time.sleep(1)

    def stop(self):
        print("Stopping experiment worker: stopping dilution and OD workers")
        self.od_worker.stop()
        self.dilution_worker.stop()
        while self.dilution_worker.thread.is_alive() or self.od_worker.thread.is_alive():
            if self.dilution_worker.thread.is_alive():
                print("Waiting for dilution worker to stop")
            if self.od_worker.thread.is_alive():
                print("Waiting for OD worker to stop")
            time.sleep(0.5)
        self.experiment.device.stirrers.set_speed_all("stopped")
        print("Experiment worker stopped")


class QueueWorker:
    def __init__(self, experiment, worker_name):
        self.name = worker_name
        self.experiment = experiment
        self.queue = queue.Queue(maxsize=1)
        self.thread = threading.Thread(target=self.process_queue, args=[self.queue], daemon=False)
        self.is_performing_operation = False
        self.paused = False
        self.thread.start()

    def stop(self):
        self.queue.put(None)

    def process_queue(self, q):
        while True:
            operation = q.get()
            if operation is None:  # None is a sentinel value indicating to stop
                break
            if self.paused:
                print("Worker %s paused" % self.name)
                while self.paused:
                    time.sleep(1)
                print("Worker %s resumed" % self.name)
            self.is_performing_operation = True
            try:
                with self.experiment.app.app_context():
                    try:
                        operation()
                    except Exception as e:
                        # print full traceback
                        traceback.print_exc()
                        print("Exception in worker %s: %s" % (self.name, e))
            finally:
                self.is_performing_operation = False


# class AutoCommitParameters:
#     def __init__(self, model, db):
#         self.model = model
#         self.db = db
#
#     def __getattr__(self, name):
#         return self.model.parameters[name]
#
#     def __setattr__(self, name, value):
#         if name in ["model", "db"]:
#             self.__dict__[name] = value
#         else:
#             self.model.parameters[name] = value
#             self.model.parameters = self.model.parameters
#             self.db.session.add(self.model)
#             self.db.session.commit()


class Experiment:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is not None:
            if cls._instance.status != "stopped":
                print("Experiment instance already exists and is not stopped. Stopping it now.")
                cls._instance.stop()
            else:
                print("Experiment instance already exists")
        cls._instance = super(Experiment, cls).__new__(cls)
        return cls._instance

    def __init__(self, device, experiment_model, db):
        self.app = current_app._get_current_object()
        self.db = db
        self.model = experiment_model  # Store the database model object
        self.device = device
        self._status = self.model.status
        self.schedule = schedule.Scheduler()
        self.locks = {i: threading.Lock() for i in range(1, 8)}
        self.experiment_worker = None
        self.cultures = {i: Culture(self, i, db) for i in range(1, 8)}
        self.db.session.commit()

    @property
    def parameters(self):
        return self.model.parameters

    @parameters.setter
    def parameters(self, new_parameters):
        with self.app.app_context():
            # Make a deep copy of the parameters, modify it, and assign it back
            id = self.model.id
            experiment_model = self.db.session.get(ExperimentModel, id)

            # modify to float
            for v, culture_parameters in new_parameters["cultures"].items():
                for key, value in new_parameters["cultures"][v].items():
                    if key in morbidostat_updater_default_parameters.keys():
                        if type(value) not in [int, float]:
                            value = float(value)
                            new_parameters["cultures"][v][key] = value
            if "growth_parameters" in new_parameters.keys():
                for v, culture_parameters in new_parameters["growth_parameters"].items():
                    for key, value in new_parameters["growth_parameters"][v].items():
                        if key in culture_growth_model_default_parameters.keys():
                            if type(value) not in [int, float]:
                                value = float(value)
                                new_parameters["growth_parameters"][v][key] = value
            # print("New parameters", new_parameters)
            experiment_model.parameters = new_parameters
            self.model.parameters = new_parameters
            self.db.session.commit()

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        self.model.status = value
        self.db.session.commit()
        print(self.model.status,"status changed to", value)

    def _delete_all_data(self):
        for v in range(1, 8):
            self.cultures[v]._delete_all_records()

    def start(self):
        if self.experiment_worker is None or not self.experiment_worker.thread.is_alive():
            self.experiment_worker = ExperimentWorker(self)
            self.device.stirrers.set_speed_all("high")
            # self.device.eeprom.save_config_to_eeprom()
            self.make_schedule()
            self.status = "running"
        else:
            print("Experiment is already running.")
            if self.experiment_worker.dilution_worker.paused:
                print("Dilution worker is paused. Resuming.")
                self.experiment_worker.dilution_worker.paused = False

    def pause_dilution_worker(self):
        self.status = "paused"
        self.experiment_worker.dilution_worker.paused = True

    def stop(self):
        if self.status == "stopped":
            print("Experiment is already stopped.")
        self.status = "stopped"
        if self.experiment_worker is not None:
            if self.experiment_worker.dilution_worker.thread.is_alive() or self.experiment_worker.od_worker.thread.is_alive():
                print("Worker is finishing up. Waiting for it to finish.")
            while self.experiment_worker.dilution_worker.thread.is_alive() or self.experiment_worker.od_worker.thread.is_alive():
                time.sleep(0.5)
            print("dilution worker and od worker stopped")
        return

    def measure_od_and_rpm_in_background(self):
        def task():
            available_vials = []
            try:
                for vial in range(1, 8):
                    if not self.locks[vial].locked():
                        self.locks[vial].acquire(blocking=False) # blocking=False means don't wait for lock, just check if it's available
                        available_vials.append(vial)
                new_rpms = self.device.stirrers.measure_all_rpms(vials_to_measure=available_vials)
                new_ods = self.measure_od_all(vials_to_measure=available_vials)
                for vial in available_vials:
                    self.cultures[vial].log_od_and_rpm(new_ods[vial],new_rpms[vial])
            finally:
                for vial in available_vials:
                    self.locks[vial].release()
        if self.experiment_worker.od_worker.queue.empty():
            self.experiment_worker.od_worker.queue.put(task)
            # print("Task to measure optical density in available vials queued for background execution.")
        else:
            print("Task to measure optical density already in queue. Skipping.")

    # def make_dilution_queued(self, vial_number, main_pump_volume, drug_pump_volume, extra_vacuum=5):
    #     print(f"Attempting to dilute vial {vial_number} in background.")
    #     if self.experiment_worker.dilution_worker.paused:
    #         print("Dilution worker paused. Dilution will not be attempted.")
    #         return
    #
    #     def task():
    #         lock_acquired_here = False
    #         try:
    #             self.locks[vial_number].acquire(blocking=True, timeout=15)
    #             lock_acquired_here = True
    #             self.cultures[vial_number].make_dilution(
    #                 pump1_volume=main_pump_volume,
    #                 pump2_volume=drug_pump_volume,
    #                 pump3_volume=0,  # pump3 not connected
    #                 extra_vacuum=extra_vacuum)
    #         finally:
    #             if lock_acquired_here:
    #                 self.locks[vial_number].release()
    #
    #     self.experiment_worker.dilution_worker.queue.put(task)
    #     print(f"Task to dilute vial {vial_number} queued for background execution.")

    def update_cultures_in_background(self):
        def task():
            for vial in range(1, 8):
                if not self.status == "running":
                    break
                self.cultures[vial].update()
        if self.experiment_worker.dilution_worker.queue.empty():
            self.experiment_worker.dilution_worker.queue.put(task)
            # print("Task to update cultures queued for background execution.")
        else:
            print("Task to update cultures already in queue. Skipping.")

    def measure_od_all(self, vials_to_measure=(1, 2, 3, 4, 5, 6, 7)):
        """
        Measure optical density of all vials in the device
        :param vials_to_measure: tuple of vials to measure
        :return: dictionary of measured optical density values
        """
        measured_od_values = {}
        if len(vials_to_measure) > 0:
            for vial in vials_to_measure:
                self.device.stirrers.set_speed(vial=vial, speed="low")
            time.sleep(4)

            for vial in vials_to_measure:
                od, signal = self.device.od_sensors[vial].measure_od()
                measured_od_values[vial] = od
            for vial in vials_to_measure:
                self.device.stirrers.set_speed(vial=vial, speed="high")
        return measured_od_values

    def reconnect_device_if_disconnected(self):
        if self.device.is_connected():
            return
        else:
            print("Device disconnected. Attempting to reconnect.")
            self.device.connect()

    def make_schedule(self):
        print("Making schedule")
        self.schedule.clear()
        self.schedule.every().minute.at(":05").do(self.update_cultures_in_background)
        self.schedule.every().minute.at(":00").do(self.measure_od_and_rpm_in_background)
        # self.schedule.every().minute.at(":20").do(self.reconnect_device_if_disconnected)
        # self.schedule.every().minute.at(":20").do(self.measure_od_in_background)
        # self.schedule.every().minute.at(":40").do(self.measure_od_in_background)

    def get_status(self):
        # Simulated method to get experiment status from database
        return self.status

    def get_experiment_status_dict(self):
        info={}
        for vial in range(1, 8):
            c = self.cultures[vial]
            info[vial] = c.get_culture_status_dict()
        return info


def object_to_dict(obj):
    if not hasattr(obj, "__dict__"):
        return repr(obj)
    result = {}

    for key, value in obj.__dict__.items():
        if isinstance(value, dict):
            # if the value is a dictionary, we represent it as a multi-line string
            value = '\n'.join([f'{k}: {v}' for k, v in value.items()])
        else:
            value = repr(value)  # Otherwise, we use repr to get a string representation of the attribute value

        result[key] = value

    return result
