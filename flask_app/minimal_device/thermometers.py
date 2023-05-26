import os
import time

import pyftdi.i2c


class Thermometers:
    def __init__(self, device):
        self.device = device
        self.thermometer_vials = None
        self.thermometer_board = None

        if self.device.is_connected():
            self.connect()

    def connect(self):
        try:
            self.thermometer_vials = self.device.i2c.get_port(
                self.device.PORT_THERMOMETER_VIALS
            )
            self.thermometer_board = self.device.i2c.get_port(
                self.device.PORT_THERMOMETER_BOARD
            )
        except pyftdi.i2c.I2cNackError:
            print("PCA9685 PWM controller connection ERROR.")
        try:
            self.thermometer_vials.write([0x04])
            time.sleep(0.06)
            self.thermometer_vials.read_from(0x04, 2)
        except pyftdi.i2c.I2cNackError:
            self.thermometer_vials = self.device.i2c.get_port(
                self.device.PORT_THERMOMETER_VIALS_v4
            )

    # near DC-DC converters which get warm

    def measure_temperature_background_thread(self):
        if self.device.od_worker.queue.empty():
            self.device.od_worker.queue.put(self.measure_temperature)
        else:
            print("Temperature measurement not queued. OD thread queue is not empty.")

    def measure_temperature(self):
        temps = []
        for thermometer_port in [self.thermometer_vials, self.thermometer_board]:
            thermometer_port.write([0x04])
            time.sleep(0.06)
            data = thermometer_port.read_from(0x04, 2)
            digital_temp = ((data[0] << 8) | data[1]) >> 4
            celsius_temp = digital_temp * 0.0625
            temps += [celsius_temp]
        t_vials, t_board = temps
        self.log_temperature(t_vials=t_vials, t_board=t_board)
        return t_vials, t_board

    def log_temperature(self, t_vials, t_board):
        """
        logs temperature if device.directory exists
        """
        if os.path.exists(str(self.device.directory)):
            filepath = os.path.join(self.device.directory, "temperature.csv")
            if not os.path.exists(filepath):
                with open(filepath, "w+") as f:
                    f.write("time,temperature_vials,temperature_board\n")
            with open(filepath, "a") as f:
                f.write("%d,%.3f,%.3f\n" % (time.time(), t_vials, t_board))
