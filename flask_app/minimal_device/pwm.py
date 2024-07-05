import threading
import time
import traceback

import pyftdi.i2c


class PwmController:
    """PCA9685 PWM controller"""

    def __init__(self, device, frequency=50):
        self.device = device
        self.frequency = frequency
        self.lock = (threading.Lock())  # valves and stirrers can be used on different threads
        self.port = None
        self.lock_port = threading.Lock()
        if self.device.is_connected():
            self.connect()

    def connect(self):
        """
        Establish I2C connection to the PWM controller.
        :return:
        """
        try:
            for i in range(3):
                try:
                    self.port = self.device.i2c.get_port(self.device.PORT_PWM)
                    break
                except Exception as e:
                    traceback.print_exc()
                    print("PCA9685 PWM controller connection ERROR:", e)
                    time.sleep(1)
            print("Connected to PCA9685 PWM controller port", self.port)
            self.set_frequency(self.frequency)
            self.stop_all()
            all_led_on_l = 250
            all_led_on_h = 251

            self.port.write_to(all_led_on_l, [0x0])
            self.port.write_to(all_led_on_h, [0x00])

            self.stop_all()
            self.set_duty_cycle_all(0)
            self.set_frequency(self.frequency)
        except pyftdi.i2c.I2cNackError:
            self.port = None
            print("PCA9685 PWM controller connection ERROR. exiting connect()")

    def set_frequency(self, frequency):
        """
        Set the PWM frequency.
        :param frequency:
        :return:
        """
        pre_scale = round(25000000 / (4096 * frequency)) - 1

        port_lock_acquired = self.lock_port.acquire(timeout=2)
        if not port_lock_acquired:
            raise Exception("Could not acquire i2c port lock for set_frequency at time %s" % time.ctime())
        try:
            try:
                self.port.write_to(0x00, [0b00010001])  # sleep mode
            except Exception:
                time.sleep(0.5)
                self.port.write_to(0x00, [0b0])  # reset
                print("Reset PWM driver")
                self.port.write_to(0x00, [0b00010001])  # sleep mode
            self.port.write_to(0xFE, [pre_scale])  # SET_PWM_FREQUENCY
            self.port.write_to(0x00, [0b10000001])  # restart mode
        finally:
            self.lock_port.release()

    def get_duty_cycle(self, led_number):
        """
        Get the duty cycle of a given pin number.
        :param led_number:
        :return:
        """
        led_off_l = led_number * 4 + 8
        led_off_h = led_number * 4 + 9

        port_lock_acquired = self.lock_port.acquire(timeout=2)
        if not port_lock_acquired:
            raise Exception("Could not acquire i2c port lock for get_duty_cycle at time %s" % time.ctime())
        try:
            lsbr = self.port.read_from(led_off_l, 1)[0]
            msbr = self.port.read_from(led_off_h, 1)[0]
            duty_cycle_read = ((msbr << 8) + lsbr) / 4095
            return duty_cycle_read
        finally:
            self.lock_port.release()

    def set_duty_cycle(self, led_number, duty_cycle):
        """
        Set the duty cycle of a given pin number.
        :param led_number:
        :param duty_cycle:
        :return:
        """
        assert 0 <= led_number <= 15
        assert 0 <= duty_cycle <= 1
        msb, lsb = divmod(
            round(4095 * duty_cycle), 0x100
        )  # most and least significant bytes
        led_off_l = led_number * 4 + 8
        led_off_h = led_number * 4 + 9

        port_lock_acquired = self.lock_port.acquire(timeout=2)
        if not port_lock_acquired:
            raise Exception("Could not acquire i2c port lock for set_duty_cycle at time %s" % time.ctime())
        try:
            self.port.write_to(led_off_l, [lsb])
            self.port.write_to(led_off_h, [msb])
        finally:
            self.lock_port.release()

    def set_duty_cycle_all(self, duty_cycle):
        """
        Set the duty cycle of all pins.
        :param duty_cycle: 0-1
        """
        msb, lsb = divmod(
            round(4095 * duty_cycle), 0x100
        )  # most and least significant bytes
        all_led_off_l = 252
        all_led_off_h = 253

        port_lock_acquired = self.lock_port.acquire(timeout=2)
        if not port_lock_acquired:
            raise Exception("Could not acquire i2c port lock for set_duty_cycle_all at time %s" % time.ctime())
        try:
            self.port.write_to(all_led_off_l, [lsb])
            self.port.write_to(all_led_off_h, [msb])
        finally:
            self.lock_port.release()

    def stop_all(self):
        """
        Stop all PWM signals.
        :return:
        """
        port_lock_acquired = self.lock_port.acquire(timeout=2)
        if not port_lock_acquired:
            raise Exception("Could not acquire i2c port lock for stop_all at time %s" % time.ctime())
        try:
            self.port.write_to(0x00, [0b10001])
        finally:
            self.lock_port.release()

    def start_all(self):
        """
        Start all PWM signals.
        :return:
        """
        port_lock_acquired = self.lock_port.acquire(timeout=2)
        if not port_lock_acquired:
            raise Exception("Could not acquire i2c port lock for start_all at time %s" % time.ctime())
        try:
            self.port.write_to(0x00, [0b00001])
            time.sleep(0.002)
            self.port.write_to(0x00, [0b10000001])
        finally:
            self.lock_port.release()

    def is_sleeping(self):
        """
        Check if the PWM controller is sleeping.
        :return:
        """
        port_lock_acquired = self.lock_port.acquire(timeout=2)
        if not port_lock_acquired:
            raise Exception("Could not acquire i2c port lock for is_sleeping at time %s" % time.ctime())
        try:
            mode1_register = self.port.read_from(0x00, 1)[0]
        finally:
            self.lock_port.release()
        is_sleeping = bool(int(bin(mode1_register)[2:].rjust(8, "0")[-5]))  # sleep bit
        return is_sleeping

    def play_turn_on_sound(self):
        """
        Play the turn on sound.
        :return:
        """
        base_freq = self.frequency
        self.stop_all()
        self.set_duty_cycle_all(0.01)
        self.set_frequency(261.63)
        self.start_all()
        # self.device.lasers.switch_all_on()
        # i = 0
        time.sleep(0.1)
        for freq in [329.63, 392, 523.25]:
            self.set_frequency(freq)
            # i += 1
            # if i % 2 == 0:
            # self.device.lasers.switch_all_on()
            # else:
            # self.device.lasers.switch_all_off()
            time.sleep(0.15)
        time.sleep(0.15)
        # self.device.lasers.switch_all_off()
        self.stop_all()
        self.set_duty_cycle_all(0)
        self.set_frequency(base_freq)
