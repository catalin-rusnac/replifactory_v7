import os
import threading
import time
from datetime import datetime
import traceback
import warnings

import pyftdi.i2c
import usb

import yaml
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
        print("Initializing device", time.ctime())
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
        self.connect_i2c_spi()
        try:
            self.pwm_controller.connect()
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
            self.eeprom.connect()
        except Exception as e:
            warnings.warn(f"Failed to connect eeprom: {e}")

        self.dilution_worker = QueueWorker(device=self, worker_name="dilution")
        self.od_worker = QueueWorker(device=self, worker_name="od")
        self.hard_stop_trigger = False
        self.soft_stop_trigger = False
        self.release_vial_locks()

    # def connect(self, ftdi_address="ftdi://ftdi:2232h", retries=10):
    #     # if ftdi_address is None:
    #     #     ftdi_address = self.ftdi_address
    #     # else:
    #     try:
    #         # t0=time.time()
    #         assert ftdi_address[-1] != "/", "ftdi_address should not end with a '/'"
    #         self.spi = SpiController(cs_count=5)
    #         self.spi.configure(ftdi_address + "/1")
    #         self.i2c = pyftdi.i2c.I2cController()
    #         self.i2c.configure(ftdi_address + "/2", frequency=5e4)
    #         self.pwm_controller.connect()  # valves and stirrers
    #         # self.valves.connect()
    #         self.stirrers.connect()
    #         self.photodiodes.connect()
    #         self.lasers.connect()
    #         self.thermometers.connect()
    #         self.pump1.connect()
    #         self.pump2.connect()
    #         self.pump3.connect()
    #         self.pump4.connect()
    #         self.eeprom.connect()
    #         # print("Device %s connection established" % ftdi_address)
    #         self.dilution_worker = QueueWorker(device=self, worker_name="dilution")
    #         self.od_worker = QueueWorker(device=self, worker_name="od")
    #         self.hard_stop_trigger = False
    #         self.soft_stop_trigger = False
    #
    #     # except USBError as ex:
    #     #     raise FtdiError('UsbError: %s' % str(ex)) from None
    #
    #     except pyftdi.ftdi.FtdiError as ex:
    #         raise ConnectionError("Connection failed! %s" % ex) from None
    #     except pyftdi.usbtools.USBError:
    #         if retries >0:
    #             try:
    #                 self.spi.terminate()
    #             except Exception:
    #                 pass
    #             try:
    #                 self.i2c.terminate()
    #             except Exception:
    #                 pass
    #             UsbTools.release_all_devices()
    #             UsbTools.flush_cache()
    #             print("Retrying connection...")
    #             self.connect(ftdi_address=ftdi_address, retries=retries - 1)
    #         print("Device connected but does not recognize the command.\nPlease reset connections.")
    #     except pyftdi.usbtools.UsbToolsError as ex:
    #         print("Connection failed! %s" % ex)
    #         print("Device %s not connected." % ftdi_address)
    #     for lock in self.locks_vials.values():
    #         if lock.locked():
    #             lock.release()

    @staticmethod
    def reset_usb_device():
        # Find the USB device
        dev = usb.core.find(idVendor=0x0403, idProduct=0x6010)  # FT2232H

        if dev is None:
            raise ValueError("Device not found")

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

    def hello(self):
        self.pwm_controller.play_turn_on_sound()
        self.lasers.blink()
        self.rgb_leds.blink_hello()
        self.valves.connect()
        print("Said hello from device")
    
    def hello_quick(self):
        self.pwm_controller.play_quick_beep()
        self.lasers.blink_quick()
        print("Said hello from device")

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
            print("Culture update not queued. dilution thread queue is not empty.")

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

    def save(self):
        """
        saves calibration data and stock concentrations to self.directory/device_config.yaml
        """
        config_path = os.path.join(self.directory, "device_config.yaml")
        save_object(self, filepath=config_path)

    def save_timestamped_device_config(self):
        """
        saves calibration data to self.directory/device_config_{timestamp}.yaml
        """
        timestamp_iso = datetime.now().isoformat()
        timestamped_config_path = os.path.join(self.directory, f"device_config_{timestamp_iso}.yaml")
        save_object(self, filepath=timestamped_config_path)

    def load_dev_config(self):
        """
        loads calibration data and stock concentrations from self.directory/device_config.yaml
        """
        assert self.file_lock.acquire(timeout=5)
        try:
            config_path = os.path.join(self.directory, "device_config.yaml")
            if os.path.exists(config_path):
                load_config(self, filepath=config_path)
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

    def calibrate(self, dummy_data=False):
        if dummy_data:
            # self.calibration_mv_to_od = {1: {1: 5, 10: 2, 22: 0.5, 35: 0.1, 41: 0.0001},
            #                              2: {1: 5, 10: 2, 22: 0.5, 35: 0.1, 41: 0.0001},
            #                              3: {1: 5, 10: 2, 35: 0.1, 41: 0.0001},
            #                              4: {1: 5, 10: 2, 35: 0.1, 41: 0.0001},
            #                              5: {1: 5, 10: 2, 35: 0.1, 41: 0.0001},
            #                              6: {1: 5, 10: 2, 35: 0.1, 41: 0.0001},
            #                              7: {1: 5, 10: 2, 35: 0.1, 41: 0.0001}}
            for v in range(1, 8):
                self.calibration_od_to_mv[v] = {
                    11.973: [0.40625, 0.4103125],
                    5.644: [0.75, 0.7575],
                    2.661: [1.6484375, 1.664921875],
                    1.254: [4.2890625, 4.331953125],
                    0.591: [10.6796875, 10.786484375],
                    0.279: [21.1015625, 21.312578125],
                    0.131: [29.8671875, 30.165859375],
                    0.062: [38.1328125, 38.514140625],
                    0.029: [42.515625, 42.94078125],
                    0.014: [45.71875, 46.1759375],
                    0: [47.859375, 48.33796875],
                }

            self.calibration_fan_speed_to_duty_cycle = {
                1: {1: 0.3, 2: 0.6, 3: 1},
                2: {1: 0.3, 2: 0.6, 3: 1},
                3: {1: 0.3, 2: 0.6, 3: 1},
                4: {1: 0.3, 2: 0.6, 3: 1},
                5: {1: 0.3, 2: 0.6, 3: 1},
                6: {1: 0.3, 2: 0.6, 3: 1},
                7: {1: 0.3, 2: 0.6, 3: 1},
            }
            self.calibration_pump_rotations_to_ml = {
                1: {1: 0.184, 3: 0.55, 20: 3.59, 80: 14.23},
                2: {1: 0.184, 3: 0.55, 20: 3.59, 80: 14.23},
                3: {},
                4: {1: 0.17, 5: 0.64, 10: 1.05, 50: 5.1, 100: 7.55, 200: 13.71},
            }
            self.save()
            self.fit_calibration_functions()

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

    def load_calibration(self, config_path):
        assert config_path.endswith("device_config.yaml")
        config = open(config_path).read()
        loaded_dict = yaml.load(config, Loader=yaml.Loader)
        # assert loaded_dict["_class"] == self.__class__
        for k in loaded_dict.keys():
            if k != "directory":
                self.__dict__[k] = loaded_dict[k]
        print("Loaded calibration data from %s" % config_path)
        self.fit_calibration_functions()
