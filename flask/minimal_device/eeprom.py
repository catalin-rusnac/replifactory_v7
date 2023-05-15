import numpy as np
import yaml


def make_addr_bytes(page=511, byte=63):
    two_bytes = page << 6 | byte
    byte1 = two_bytes >> 8
    byte2 = two_bytes & 0b11111111
    return byte1, byte2


class EEPROM:
    PAGE_TEST = 511
    PAGE_VALVES = 510

    def __init__(self, device):
        self.device = device
        self.port = None
        self.loaded_device_keys = [
            "calibration_coefs_od",
            "calibration_coefs_pumps",
            "calibration_fan_speed_to_duty_cycle",
            "calibration_milk_to_mv",
            "calibration_milk_to_od",
            "calibration_od_to_mv",
            "calibration_pump_rotations_to_ml",
            "drying_prevention_pump_period_hrs",
            "drying_prevention_pump_volume",
        ]

        if self.device.is_connected():
            self.connect()

    def connect(self):
        """
        Connects to the EEPROM
        :return:
        """
        try:
            self.port = self.device.i2c.get_port(0x53)
        except Exception:
            print("Not connected to EEPROM")

    def save_config_to_eeprom(self, from_file=False):
        """
        Writes the device object config to the EEPROM
        :param from_file: file directory, the config is read from the file instead of the device object
        :return:
        """
        if from_file:
            config_directory = from_file
            config = open(config_directory, "r").read()
            config_to_write = config
        else:
            config_to_write = {
                k: self.device.__dict__[k]
                for k in self.device.__dict__
                if k in self.loaded_device_keys
            }
            config_to_write = yaml.dump(config_to_write)
        config_bytes = bytearray(config_to_write, "utf-8")
        filler_size = 32768 - len(config_bytes)
        for i in range(filler_size):
            config_bytes.append(0xFF)
        for page in range(512):
            b1, b2 = make_addr_bytes(page=page, byte=0)
            self.port.write(
                [b1, b2] + [b for b in config_bytes[64 * page : 64 * (page + 1)]]
            )
            if page % 20 == 0:
                print(
                    "Writing to EEPROM: %d%% done" % (page / 5.12),
                    end="                              \r",
                )
        print("Writing new config to EEPROM COMPLETE")

    def read_config_from_device(self):
        """
        Reads the config from the device and returns it as a dictionary
        :return: config dictionary
        """
        loaded_text = self.read_eeprom()
        loaded_config = yaml.load(loaded_text, Loader=yaml.Loader)
        return loaded_config

    def load_config_from_eeprom(self):
        """
        Loads the config from the EEPROM into the device object
        :return:
        """
        loaded_config = self.read_config_from_device()
        if type(loaded_config) is dict:
            for k in loaded_config:
                self.device.__dict__[k] = loaded_config[k]

    def write_to_page(self, page, content, byte=0, fill=True):
        assert byte < 64
        content = yaml.dump(content)
        content_bytes = bytearray(content, "utf-8")
        assert len(content_bytes) <= 64
        if fill:
            filler_size = 64 - len(content_bytes)
            for i in range(filler_size):
                content_bytes.append(0xFF)
        b1, b2 = make_addr_bytes(page=page, byte=byte)
        self.port.write([b1, b2] + [b for b in content_bytes])

    def write_byte(self, page, byte, content_bytes):
        b1, b2 = make_addr_bytes(page=page, byte=byte)
        self.port.write([b1, b2] + [b for b in content_bytes])

    def read_from_page(self, page):
        tail = bytearray([0xFF] * 1)
        b1, b2 = make_addr_bytes(page=page, byte=0)
        self.port.write([b1, b2], relax=False)
        bytes_read = self.port.read(64)
        assert len(bytes_read.partition(tail)[-1]) > 0
        decoded_data = bytes_read.partition(tail)[0].decode("utf-8")
        data = yaml.load(decoded_data, Loader=yaml.Loader)
        return data

    def erase_memory(self):
        for page in range(512):
            b1, b2 = make_addr_bytes(page=page, byte=0)
            self.port.write([b1, b2] + [0xFF] * 64)
            if page % 10 == 0:
                print(
                    "Erasing EEPROM: %d%% done" % (page / 5.12),
                    end="                 \r",
                )
        print("Erasing EEPROM complete")

    def read_eeprom(self):
        pages_read = []
        tail = bytearray([0xFF] * 63)
        for page in range(512):
            b1, b2 = make_addr_bytes(page=page, byte=0)
            self.port.write([b1, b2], relax=False)
            bytes_read = self.port.read(64)
            pages_read += bytes_read
            if len(bytes_read.partition(tail)[-1]) > 0:
                break
            print(
                "Reading EEPROM: content found in %d pages" % (page + 1),
                end="                    \r",
            )
        decoded_data = bytearray(pages_read).partition(tail)[0].decode("utf-8")
        return decoded_data

    def test_memory(self):
        page = self.PAGE_TEST
        test_data = list(np.random.randint(0, 255, 64))
        b1, b2 = make_addr_bytes(page=page, byte=0)
        self.port.write([b1, b2] + test_data)
        self.port.write([b1, b2], relax=False)
        bytes_read = self.port.read(64)
        if [i for i in bytes_read] == test_data:
            return True
        else:
            print("EEPROM memory error")
            return False
