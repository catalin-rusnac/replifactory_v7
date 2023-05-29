import logging
import os
import queue
import threading
import time


class ExperimentWorker:
    def __init__(self, experiment):
        self.experiment = experiment
        self.thread = None
        self.keep_running = True

    def start(self):
        assert not self.is_alive(), "experiment already running"
        self.keep_running = True
        self.thread = threading.Thread(target=self._run_schedule, daemon=False)
        self.thread.start()

    def close(self):
        self.handler.close()

    def is_alive(self):
        if self.thread is None:
            return False
        else:
            return self.thread.is_alive()

    def status(self):
        if self.is_alive():
            print(time.ctime(), "Main thread: RUNNING")
        else:
            print(time.ctime(), "Main thread: NOT RUNNING")
        if self.experiment.device is not None:
            if (
                self.experiment.device.od_worker is not None
                and self.experiment.device.dilution_worker is not None
            ):
                self.experiment.device.od_worker.check_status()
                self.experiment.device.dilution_worker.check_status()
            else:
                print("Background thread workers not initialized.")
            for vial, lock in self.experiment.device.locks_vials.items():
                if lock.locked():
                    print("Vial %d: LOCKED" % vial)
            if self.experiment.device.lock_pumps.locked():
                print("Pumps: LOCKED")

    def stop(self):
        self.keep_running = False
        while self.thread.is_alive():
            time.sleep(0.5)
        while (
            self.experiment.device.od_worker.is_performing_operation
            or self.experiment.device.dilution_worker.is_performing_operation):
            time.sleep(5)
        if self.thread._tstate_lock:
            self.thread._tstate_lock.release()
        self.thread._stop()

    def emergency_stop(self):
        self.experiment.device.emergency_stop()
        print("EMERGENCY STOP EXECUTED")
        self.stop()

    def _run_schedule(self):
        while self.keep_running:
            self.experiment.schedule.run_pending()
            time.sleep(1)


class QueueWorker:
    def __init__(self, device, worker_name):
        self.name = worker_name
        self.device = device
        self.queue = queue.Queue(maxsize=1)
        self.thread = threading.Thread(
            target=self.process_queue, args=[self.queue], daemon=False
        )
        self.is_performing_operation = False
        self.thread.start()

    def stop(self):
        if self.thread._tstate_lock:
            self.thread._tstate_lock.release()
        self.thread._stop()

    def check_status(self):
        if not self.queue.empty():
            print("%s worker queue: NOT EMPTY" % self.name)
        if self.is_performing_operation:
            print(time.ctime(), "%s worker: WORKING" % self.name)
            # else:
            #     print("%s worker queue is empty." % self.name)
        else:
            print("%s worker: IDLE" % self.name)

    def process_queue(self, q):
        while True:
            try:
                queued_operation = q.get_nowait()
                try:
                    self.is_performing_operation = True
                    queued_operation()
                    self.is_performing_operation = False
                except Exception as e:
                    try:
                        print("************** Fatal ERROR in loop **************")
                        print(e)
                        self.is_performing_operation = False
                    except Exception:  # if there is no logger file
                        pass
            except queue.Empty:
                time.sleep(0.5)
