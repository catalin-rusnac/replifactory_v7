import time
import threading
from queue import Queue

import numpy as np
import yaml
import gzip

def make_addr_bytes(page=511, byte=63):
    two_bytes = page << 6 | byte
    byte1 = two_bytes >> 8
    byte2 = two_bytes & 0b11111111
    return byte1, byte2

class EEPROM:
    PAGE_TEST = 511

    class EepromWriter:
        def __init__(self, eeprom):
            print("Starting EEPROM writer worker thread", time.ctime())
            self.eeprom = eeprom
            self.data = None
            self.queue = Queue()
            self.timer = None
            self.lock = threading.Lock()
            self.worker_thread = threading.Thread(target=self.worker)
            self.worker_thread.start()

        def worker(self):
            while True:
                with self.lock:
                    data = self.data
                    self.data = None
                if data is not None:
                    self.eeprom._write_to_eeprom(data)
                time.sleep(1)

        def add_data(self, data):
            with self.lock:
                self.data = data
                print("Added data to EEPROM writer queue", time.ctime())

    def __init__(self, device):
        print("Initializing EEPROM", time.ctime())
        self.device = device
        self.port = None
        self.writer = self.EepromWriter(self)
        if self.device.is_connected():
            self.connect()

    def connect(self):
        """
        Connects to the EEPROM
        :return:
        """
        try:
            self.port = self.device.i2c.get_port(0x53)
            self.load_config_from_eeprom()
        except Exception:
            print("Not connected to EEPROM")

    def save_config_to_eeprom(self):
        """
        Writes the device object config to the EEPROM
        :param from_file: file directory, the config is read from the file instead of the device object
        :return:
        """
        self.writer.add_data(self.device.device_data)

    def _write_to_eeprom(self, data):
        config_to_write = data
        config_to_write = yaml.dump(config_to_write)
        config_to_write = config_to_write.encode("utf-8")
        config_to_write = gzip.compress(config_to_write)
        config_bytes = bytearray(config_to_write)
        # filler_size = 32768 - len(config_bytes)
        filler_size = 64
        print("Writing", len(config_bytes), "bytes to EEPROM", time.ctime())
        # print(filler_size, "bytes of filler to write to EEPROM")
        for i in range(filler_size):
            config_bytes.append(0xFF)
        n_pages_to_write = int(np.ceil(len(config_bytes) / 64))
        # print(n_pages_to_write,"pages to write to EEPROM")
        for page in range(n_pages_to_write):
            b1, b2 = make_addr_bytes(page=page, byte=0)
            self.port.write(
                [b1, b2] + [b for b in config_bytes[64 * page : 64 * (page + 1)]]
            )
        self.eeprom_config = self.device.device_data

        #     if page % 20 == 0:
        #         print(
        #             "Writing to EEPROM: %d%% done" % (page / 5.12),
        #             end="                              \r",
        #         )
        # print("Writing new config to EEPROM COMPLETE")

    def load_config_from_eeprom(self):
        """
        Loads the config from the EEPROM into the device object
        :return:
        """
        loaded_config = self.read_eeprom()
        self.device.device_data = loaded_config

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
        loaded_data = gzip.decompress(bytearray(pages_read).partition(tail)[0])
        loaded_data = loaded_data.decode("utf-8")
        loaded_data = yaml.load(loaded_data, Loader=yaml.Loader)
        return loaded_data

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
