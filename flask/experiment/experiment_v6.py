import os

import schedule

from ..minimal_device.base_device import BaseDevice
from .workers import ExperimentWorker

_experiment = None


class Experiment:
    def __init__(self, directory=None, connect=False):
        global _experiment
        if "_experiment" in globals().keys():
            if _experiment is not None:
                if _experiment.is_running():
                    print("Experiment '%s' is running!" % _experiment.directory)
            else:
                _experiment = self
        else:
            _experiment = self
        self.directory = directory
        self.schedule = schedule.Scheduler()
        if not os.path.exists(directory):  # new exp folder
            os.mkdir(directory)
            print("Created new experiment directory: '%s'" % directory)

        device_config_path = os.path.join(directory, "device_config.yaml")
        if os.path.exists(device_config_path):
            self._device = load_object(filepath=device_config_path)
            if self._device.directory != directory:
                print("changing directory")
                self._device.directory = directory
                # self._device.save()
        else:
            self.device = BaseDevice()

        if self.device is not None:
            self.device.load_dev_and_cultures_config()
            if connect:
                self.device.connect()
            # else:
            # print("Not linked to device.")
        if not os.path.exists(device_config_path):
            print("No device config found in '%s'" % self.directory)
        self.worker = ExperimentWorker(experiment=self)

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, dev):
        if dev is not None:
            if self.directory is not None:
                if os.path.exists(os.path.join(self.directory, "device_config.yaml")):
                    if dev.directory != self.directory:
                        print(self.directory, dev.directory)
                        raise RuntimeError(
                            "Device config %s already exists. %s"
                            % (self.directory, dev.directory)
                        )
                        # q = input("Overwrite existing device config in '%s'? [y/n]" % self.directory)
                        # if q != "y":

            dev.directory = self.directory
            dev.reinitialize_workers()
            print("setting device directory to exp directory %s" % self.directory)
            # dev.connect()
        self._device = dev
        self.save()
        return

    def save(self):
        if self.device is not None:
            self.device.save()

    def run(self):
        device = self.device

        assert not self.worker.is_alive(), "experiment already running!"
        # self.device.hard_stop_trigger = False
        self.device.soft_stop_trigger = False
        self.device.run_self_test()
        device.valves.close_all()
        device.stirrers.set_speed_all(speed=2)
        print("Closed valves, passed checks. starting background worker.")
        self.schedule.clear()
        self.schedule.every().minute.at(":57").do(
            device.thermometers.measure_temperature_background_thread
        )
        self.schedule.every().minute.at(":00").do(device.measure_od_all)
        self.schedule.every().minute.at(":30").do(device.update_cultures)
        if not device.is_lagoon_device():
            self.schedule.every().minute.at(":31").do(device.flush_tubing)
        else:
            print("lagoon device, no flushing!")
        self.device.reinitialize_workers()
        self.worker.start()

    def is_running(self):
        if not hasattr(self, "worker"):
            return False
        return self.worker.is_alive()

    def stop(self):
        self.worker.stop()

    def plot(self, last_hours=24, increase_verbosity=False, td_ylim=None):
        for v in range(1, 8):
            if self.device.cultures[v] is not None:
                if self.device.cultures[v].is_active() or increase_verbosity:
                    fig = self.device.cultures[v].plot(last_hours=last_hours)
                    if td_ylim:
                        fig.axes[1].set_ylim(td_ylim[0], td_ylim[1])
