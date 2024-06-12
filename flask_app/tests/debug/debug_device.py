import time

import pyftdi
from pyftdi.i2c import I2cController
from pyftdi.spi import SpiController


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
    PORT_PWM = 0x70  # PCA9685
    PORT_EEPROM = 0x53

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

        # self.pwm_controller = PwmController(device=self, frequency=50)
        # self.valves = Valves(device=self)
        # self.stirrers = Stirrers(device=self)
        # self.photodiodes = Photodiodes(device=self)
        # self.lasers = Lasers(device=self)
        # self.od_sensors = {v: OdSensor(device=self, vial_number=v) for v in range(1, 8)}
        # self.pump1 = Pump(device=self, cs=0)
        # self.pump2 = Pump(device=self, cs=1)
        # self.pump3 = Pump(device=self, cs=2)
        # self.pump4 = Pump(device=self, cs=3)
        # self.thermometers = Thermometers(device=self)
        # self.eeprom = EEPROM(device=self)
        # self.cultures = CultureDict(self)
    def connect(self, ftdi_address="ftdi://ftdi:2232h", retries=10):
        assert ftdi_address[-1] != "/", "ftdi_address should not end with a '/'"
        self.spi = SpiController(cs_count=5)
        self.spi.configure(ftdi_address + "/1")
        self.i2c = I2cController()
        self.i2c.configure(ftdi_address + "/2", frequency=1e4)


if __name__ == "__main__":
    dev = BaseDevice()
    dev.connect()
    print("debug device connected - i2c and spi ok")