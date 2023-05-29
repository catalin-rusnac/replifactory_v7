import threading
import time
import queue
import schedule

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
cultures = {i: culture_parameters for i in range(1, 8)}
default_parameters['cultures'] = cultures


class ExperimentWorker:
    def __init__(self, experiment):
        self.experiment = experiment
        self.od_worker = QueueWorker(experiment=self.experiment, worker_name='OD_worker')
        self.dilution_worker = QueueWorker(experiment=self.experiment, worker_name='Dilution_worker')
        self.thread = threading.Thread(target=self.run_loop, daemon=False)
        self.thread.start()

    def run_loop(self):
        print('Experiment worker started')
        while True:
            status = self.experiment.get_experiment_status()
            if status == 'stopped':
                print('Experiment worker stopped. Stopping OD and dilution workers')
                self.stop()
                break
            else:
                self.experiment.schedule.run_pending()
                print("ran pending", time.ctime())
            time.sleep(1)

    def stop(self):
        self.od_worker.stop()
        self.dilution_worker.stop()
        while self.dilution_worker.thread.is_alive() or self.od_worker.thread.is_alive():
            time.sleep(0.5)
        self.experiment.device.stirrers.set_speed_all("stopped")
        print("All workers stopped")


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
                operation()
            finally:
                self.is_performing_operation = False


class Experiment:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is not None:
            if cls._instance.status != "stopped":
                print("Experiment instance already exists and is not stopped. Stopping it now.")
            else:
                print("Experiment instance already exists")
            cls._instance.stop()
        cls._instance = super(Experiment, cls).__new__(cls)
        return cls._instance

    def __init__(self, device, experiment_model):
        self.status = "stopped"
        self.device = device
        self.schedule = schedule.Scheduler()
        self.locks = {i: threading.Lock() for i in range(1, 8)}
        self.model = experiment_model  # Store the database model object
        self.experiment_worker = None

    def start(self):
        if self.experiment_worker is None or not self.experiment_worker.thread.is_alive():
            self.status = "running"
            self.experiment_worker = ExperimentWorker(self)
            self.device.stirrers.set_speed_all("high")
            self.make_schedule()
        else:
            print("Experiment is already running.")
            if self.experiment_worker.dilution_worker.paused:
                print("Dilution worker is paused. Resuming.")
                self.experiment_worker.dilution_worker.paused = False



    def pause_dilution_worker(self):
        self.experiment_worker.dilution_worker.paused = True

    def stop(self):
        if self.status == "stopped":
            print("Experiment is already stopped.")
            if self.experiment_worker is not None:
                if self.experiment_worker.dilution_worker.thread.is_alive() or self.experiment_worker.od_worker.thread.is_alive():
                    print("Worker is finishing up. Waiting for it to finish.")
            return
        self.status = "stopped"

    def measure_od_in_background(self):
        def task():
            available_vials = []
            try:
                for vial in range(1, 8):
                    if not self.locks[vial].locked():
                        self.locks[vial].acquire(blocking=False)
                        available_vials.append(vial)
                self.measure_od_all(vials_to_measure=available_vials)
            finally:
                for vial in available_vials:
                    self.locks[vial].release()

        self.experiment_worker.od_worker.queue.put(task)
        print("Task to measure optical density in available vials queued for background execution.")

    def attempt_dilute_in_background(self, vial_number, main_pump_volume, drug_pump_volume, extra_vacuum=5):
        print(f"Attempting to dilute vial {vial_number} in background.")
        if self.experiment_worker.dilution_worker.paused:
            print("Dilution worker paused. Dilution will not be attempted.")
            return

        def task():
            lock_acquired_here = False
            try:
                self.locks[vial_number].acquire(blocking=True, timeout=15)
                lock_acquired_here = True
                self.dilute(vial_number, main_pump_volume, drug_pump_volume, extra_vacuum)
            finally:
                if lock_acquired_here:
                    self.locks[vial_number].release()

        self.experiment_worker.dilution_worker.queue.put(task)
        print(f"Task to dilute vial {vial_number} queued for background execution.")

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
                od = self.device.od_sensors[vial].measure_od()
                measured_od_values[vial] = od
            for vial in vials_to_measure:
                self.device.stirrers.set_speed(vial=vial, speed="high")
        return measured_od_values

    def dilute(self, vial_number, main_pump_volume, drug_pump_volume, extra_vacuum=5):
        self.device.make_dilution(
                    vial=vial_number,
                    pump1_volume=main_pump_volume,
                    pump2_volume=drug_pump_volume,
                    pump3_volume=0,
                    extra_vacuum=extra_vacuum)

    def update_cultures(self):
        self.attempt_dilute_in_background(vial_number=7, main_pump_volume=0, drug_pump_volume=0)

    # def update_cultures(self):
    #     def queued_function():
    #         for v, c in self.cultures.items():
    #             if self.soft_stop_trigger:
    #                 break
    #             if c is not None:
    #                 c.update()
    #
    #     if self.dilution_worker.queue.empty():
    #         self.dilution_worker.queue.put(queued_function)
    #     else:
    #         print("Culture update not queued. dilution thread queue is not empty.")

    def make_schedule(self):
        print("Making schedule")
        self.schedule.clear()
        self.schedule.every().minute.at(":57").do(
            self.device.thermometers.measure_temperature_background_thread
        )
        self.schedule.every().minute.at(":05").do(self.update_cultures)
        self.schedule.every().minute.at(":00").do(self.measure_od_in_background)

    def get_experiment_status(self):
        # Simulated method to get experiment status from database
        return self.status
