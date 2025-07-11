import os
import threading
import time
from datetime import datetime
import traceback
import warnings
from logger.logger import logger

import pyftdi.i2c
import usb

import yaml
import shutil
from pyftdi.spi import SpiController
from pyftdi.usbtools import UsbTools

from .adc import Photodiodes
from .eeprom import EEPROM
from .lasers import Lasers
from .led import RGBLedController
from .od_sensor import OdSensor
from .pump import Pump
from .pwm import PwmController
from .stirrers import Stirrers
from .thermometers import Thermometers
from .valves import Valves
from .workers import QueueWorker
from .loading import load_config, load_object, save_object
from .other import CultureDict
from .device_data import default_device_data


class BaseDevice:
    PORT_ADC = 0x68  # MCP3421A0  1101 000
    # PORT_ADC = 0x69  # MCP3421A1  1101 001
    # PORT_ADC = 0x6a  # MCP3421A2  1101 010
    # PORT_ADC = 0x6b  # MCP3421A3  1101 011
    PORT_GPIO_MULTIPLEXER_LASERS = 0x20  # PCA 9555
    PORT_GPIO_MULTIPLEXER_ADC = 0x21  # PCA 9555
    PORT_GPIO_MULTIPLEXER_STIRRERS = 0x25  # PCA 9555
    PORT_THERMOMETER_VIALS = 0x49  # ADT 75  #0x4C?
    PORT_THERMOMETER_VIALS_v4 = 0x4C  # device version 4
    PORT_THERMOMETER_BOARD = 0x48  # ADT 75
    PORT_PWM = 0x5A  # PCA9685 motors
    PORT_RGB_PWM1 = 0x5C # PCA9685 LEDs 1-5
    PORT_RGB_PWM2 = 0x5D # PCA9685 LEDs 6-7
    PORT_EEPROM = 0x53  # deprecated

    def __init__(self, ftdi_address="ftdi://ftdi:2232h", connect=False, directory=None):
        t0 = time.time()
        self.ftdi_address = ftdi_address
        self.directory = directory

        self.active_pumps = (1, 2, 4)

        self.dilution_worker = None
        self.od_worker = None

        self.hard_stop_trigger = False
        self.soft_stop_trigger = False

        self.i2c = None
        self.spi = None
        self.device_data = default_device_data

        self.drying_prevention_pump_period_hrs = 12
        self.drying_prevention_pump_volume = 0.1
        self.setup_time = time.time()

        self.locks_vials = {v: threading.Lock() for v in range(1, 8)}
        self.lock_pumps = threading.Lock()
        # self.lock_spi = threading.Lock()
        # self.lock_i2c = threading.Lock()

        self.lock_ftdi = threading.Lock()

        self.file_lock = threading.Lock()
        # self.pump_calibrations_rotations_to_ml = {1: {}, 2: {}, 3: {}, 4: {}}
        self.pump_stock_concentrations = {1: None, 2: None, 3: None, 4: None}
        self.pump_stock_volumes = {1: None, 2: None, 3: None, 4: None}

        self.od_values = {v: None for v in range(1, 8)}
        self.pwm_controller = PwmController(device=self, frequency=50)
        self.valves = Valves(device=self)
        self.stirrers = Stirrers(device=self)
        self.photodiodes = Photodiodes(device=self)
        self.lasers = Lasers(device=self)
        self.rgb_leds = RGBLedController(device=self)
        self.od_sensors = {v: OdSensor(device=self, vial_number=v) for v in range(1, 8)}
        self.pump1 = Pump(device=self, cs=0)
        self.pump2 = Pump(device=self, cs=1)
        self.pump3 = Pump(device=self, cs=2)
        self.pump4 = Pump(device=self, cs=3)
        self.thermometers = Thermometers(device=self)
        self.eeprom = EEPROM(device=self)
        self.cultures = CultureDict(self)
        self.cultures[1] = None
        self.cultures[2] = None
        self.cultures[3] = None
        self.cultures[4] = None
        self.cultures[5] = None
        self.cultures[6] = None
        self.cultures[7] = None
        if self.directory is not None:
            try:
                self.load_dev_and_cultures_config()
                print("loaded", time.time() - t0)
            except FileNotFoundError:
                print("saving", time.time() - t0)
                self.save()
        if connect:
            self.connect()

    def shutdown(self):
        """shutdown all threads - eeprom writer, dilution worker, od worker"""
        try:
            if self.eeprom.writer is not None:
                self.eeprom.writer.stop()   
        except Exception as e:
            logger.error(f"Error stopping EEPROM writer: {e}")
        try:
            if self.dilution_worker is not None:
                self.dilution_worker.stop()
        except Exception as e:
            logger.error(f"Error stopping dilution worker: {e}")
        try:
            if self.od_worker is not None:
                self.od_worker.stop()
        except Exception as e:
            logger.error(f"Error stopping od worker: {e}")
        logger.info("All device workers stopped")

    def connect_i2c_spi(self, ftdi_address="ftdi://ftdi:2232h", retries=5):
        # acquire lock_pumps to prevent concurrent attempts to connect
        assert self.lock_pumps.acquire(timeout=5)
        try:
            self.spi = SpiController(cs_count=5)
            self.i2c = pyftdi.i2c.I2cController()
            for attempt in range(retries):
                try:
                    self.spi.configure(ftdi_address + "/1")
                    self.i2c.configure(ftdi_address + "/2", frequency=5e4)
                    print("closing SPI and I2C")
                    self.spi.close()
                    self.i2c.close()
                    print("opening SPI and I2C again")
                    self.spi.configure(ftdi_address + "/1")
                    self.i2c.configure(ftdi_address + "/2", frequency=5e4)
                    return
                except Exception as e:
                    # self.reset_usb_device()
                    self.disconnect_all()
                    print(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(0.5)
        finally:
            self.lock_pumps.release()
        raise ConnectionError("Failed to connect to I2C and SPI")

    def connect(self):
        logger.info("Attempting to connect to device...")
        self.connect_i2c_spi()
        try:
            self.eeprom.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect eeprom: {e}")

        try:
            frequency = self.device_data["frequency_multiplier"] * 50
        except Exception as e:
            frequency = None
        try:
            self.pwm_controller.connect(frequency=frequency)
        except Exception as e:
            warnings.warn(f"Failed to connect pwm_controller: {e}")

        try:
            self.stirrers.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect stirrers: {e}")

        try:
            self.photodiodes.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect photodiodes: {e}")

        try:
            self.lasers.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect lasers: {e}")

        try:
            self.rgb_leds.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect rgb_leds: {e}")

        try:
            self.thermometers.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect thermometers: {e}")

        try:
            self.pump1.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect pump1: {e}")

        try:
            self.pump2.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect pump2: {e}")

        try:
            self.pump3.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect pump3: {e}")

        try:
            self.pump4.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect pump4: {e}")

        try:
            logger.info("Connecting valves")
            self.valves.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect valves: {e}")

        self.dilution_worker = QueueWorker(device=self, worker_name="dilution")
        self.od_worker = QueueWorker(device=self, worker_name="od")
        self.hard_stop_trigger = False
        self.soft_stop_trigger = False
        self.release_vial_locks()

    @staticmethod
    def reset_usb_device():
        # Find the USB device
        dev = usb.core.find(idVendor=0x0403, idProduct=0x6010)  # FT2232H

        if dev is None:
            logger.error("No FT2232H device found")
            raise ConnectionError("No FT2232H device found")

        # Detach any kernel drivers and reset the device
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
            dev.reset()
            time.sleep(5)  # Wait for the device to reset and reinitialize
        except usb.core.USBError as e:
            print(f"Failed to reset the USB device: {e}")
            raise

    def reinitialize_workers(self):
        """
        Reinitialize the workers after directory change
        :return:
        """
        if self.dilution_worker is not None:
            self.dilution_worker.stop()
        if self.od_worker is not None:
            self.od_worker.stop()
        assert os.path.exists(self.directory)
        self.dilution_worker = QueueWorker(device=self, worker_name="dilution")
        self.od_worker = QueueWorker(device=self, worker_name="od")

    def disconnect_all(self):
        try:
            self.spi.terminate()
        except Exception:
            pass
        try:
            self.i2c.terminate()
        except Exception:
            pass

        UsbTools.release_all_devices()
        UsbTools.flush_cache()
        self.reset_usb_device()
        logger.info("Disconnected from device")

    def hello(self):
        # self.pwm_controller.play_turn_on_sound()
        self.lasers.blink()
        self.rgb_leds.blink_hello()
        logger.info("Said hello from device")
    
    def hello_quick(self):
        # self.pwm_controller.play_quick_beep()
        self.lasers.blink_quick()
        logger.info("Said hello_quick from device")

    def update_cultures(self):
        def queued_function():
            for v, c in self.cultures.items():
                if self.soft_stop_trigger:
                    break
                if c is not None:
                    c.update()

        if self.dilution_worker.queue.empty():
            self.dilution_worker.queue.put(queued_function)
        else:
            logger.info("Culture update not queued. dilution thread queue is not empty.")

    @property
    def pumps(self):
        return {1: self.pump1, 2: self.pump2, 3: self.pump3, 4: self.pump4}

    def stop_pumps(self):
        self.pump1.stop()
        self.pump2.stop()
        self.pump3.stop()
        self.pump4.stop()

    def measure_temperature(self):
        def queued_function():
            self.thermometers.measure_temperature()

        if self.od_worker.queue.empty():
            self.od_worker.queue.put(queued_function)
        else:
            print("Temperature measurement not queued. od thread queue is not empty.")

    def release_vial_locks(self):
        for lock in self.locks_vials.values():
            if lock.locked():
                lock.release()

    def release_locks(self):
        if self.is_pumping():
            self.stop_pumps()
            print("Stopped pumps")
        self.release_vial_locks()
        if self.lock_pumps.locked():
            self.lock_pumps.release()
            print("released pump lock")

    def is_pumping(self):
        return any(
            p.is_pumping() for p in [self.pump1, self.pump2, self.pump3, self.pump4]
        )

    def emergency_stop(self):
        # self.hard_stop_trigger = True
        self.pump1.stop()
        self.pump2.stop()
        self.pump3.stop()
        self.pump4.stop()
        self.stirrers.emergency_stop()

    def is_connected(self):
        try:
            if hasattr(self.spi, "_ftdi") and hasattr(self.i2c, "_ftdi"):
                return self.spi._ftdi.is_connected and self.i2c._ftdi.is_connected
            else:
                return False
        except:
            traceback.print_exc()
            return False

    def save_timestamped_device_config(self):
        """
        saves calibration data to self.eeprom.filename with timestamp in filename
        """
        config_path = self.eeprom.filename
        timestamp_for_filename = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if "." in config_path:
            #replace last occurence of . with timestamp
            timestamped_config_path = config_path.rsplit(".", 1)[0] + "_" + timestamp_for_filename + "." + config_path.rsplit(".", 1)[1]
        else:
            timestamped_config_path = config_path + "_" + timestamp_for_filename
        # copy config_path to timestamped_config_path
        shutil.copy(config_path, timestamped_config_path)
        logger.info(f"Saving device config to {timestamped_config_path}")
        save_object(self, filepath=timestamped_config_path)

    def list_device_configs(self):
        """
        lists all device configs in self.directory
        """
        eeprom_dir = os.path.dirname(self.eeprom.filename)
        options = [f for f in os.listdir(eeprom_dir) if f.endswith(".yaml") and f.startswith("device_data_")]
        return options
    
    def load_dev_config(self,filename):
        """
        loads calibration data and stock concentrations from self.directory/device_config.yaml
        """
        assert self.file_lock.acquire(timeout=5)
        try:
            eeprom_dir = os.path.dirname(self.eeprom.filename)
            config_path = os.path.join(eeprom_dir, filename)
            if os.path.exists(config_path):
                load_config(self, filepath=config_path)
                logger.info(f"Loaded device config from {config_path}")
            else:
                print("No device config file found. Using default device config.")
        finally:
            self.file_lock.release()

    def load_cultures(self):
        """
        loads culture data from self.directory/cultures.yaml
        """
        assert self.file_lock.acquire(timeout=5)
        try:
            for v in range(1, 8):
                vial_directory = os.path.join(self.directory, "vial_%d" % v)
                vial_config_path = os.path.join(vial_directory, "culture_config.yaml")
                if os.path.exists(vial_config_path):
                    self.cultures[v] = load_object(vial_config_path)
                else:
                    print("No culture config file found for vial %d" % v)
        finally:
            self.file_lock.release()

    def load_dev_and_cultures_config(self):
        self.load_dev_config()
        self.load_cultures()

    def copy_all_culture_configs(self, source_exp_directory):
        for v in range(1, 8):
            source_config_path = os.path.join(
                source_exp_directory, "vial_%d/culture_config.yaml" % v
            )
            self.copy_culture_config(
                source_config_path=source_config_path, target_vial_number=v
            )

    def copy_culture_config(self, source_config_path, target_vial_number):
        source_culture = load_object(source_config_path)
        _class = source_culture.__dict__["_class"]
        target_culture = self.cultures[target_vial_number] = _class(
            self.directory, target_vial_number
        )

        for k in target_culture.__dict__.keys():
            if not k.startswith("_") and k not in [
                "vial_number",
                "directory",
                "file_lock",
                "od_blank",
            ]:
                target_culture.__dict__[k] = source_culture.__dict__[k]
        target_culture.save()

    def show_parameters(self):
        self.stirrers.show_parameters()
        print()
        self.pump1.show_parameters()
        self.pump2.show_parameters()
        self.pump3.show_parameters()
        self.pump4.show_parameters()
        print()
        for od_sensor in self.od_sensors.values():
            od_sensor.plot_calibration_curve()