import os
import re
import time
import numpy as np

class Stirrers:
    led_numbers = {stirrer: 7 - stirrer for stirrer in [1, 2, 3, 4, 5, 6, 7]}

    def __init__(self, device):
        self.freq=1e5
        self.device = device
        self.pwm_controller = None
        self.multiplexer_port = None
        self.rpms = {vial: None for vial in range(1, 8)}

        if self.device.is_connected():
            self.connect()

    def connect(self):
        self.pwm_controller = self.device.pwm_controller
        if self.pwm_controller.port is not None:
            # for 3-pin fan speed feedback
            self.multiplexer_port = self.device.i2c.get_port(
                self.device.PORT_GPIO_MULTIPLEXER_STIRRERS
            )

            lock_acquired = self.pwm_controller.lock.acquire(timeout=3)
            if not lock_acquired:
                raise Exception("Could not acquire lock for connecting stirrers at time %s" % time.ctime())
            try:
                # all GPIO pins output
                self.multiplexer_port.write_to(6, [0x00])
                # all GPIO pins output
                self.multiplexer_port.write_to(7, [0x00])
            finally:
                self.pwm_controller.lock.release()
            # Initialize SPI port for fan monitoring
            self.fans_spi_port = self.device.spi.get_port(cs=4, freq=self.freq, mode=3)
            self.fans_spi_port.set_frequency(self.freq)

    def add_calibration_point(self, vial_number, speed, duty_cycle):
        assert speed in [0, 1, 2, 3]
        assert vial_number in [1, 2, 3, 4, 5, 6, 7]
        temp = self.device.calibration_fan_speed_to_duty_cycle
        temp[vial_number][speed] = duty_cycle
        self.device.calibration_fan_speed_to_duty_cycle = temp
        self.device.save()

    def _set_duty_cycle(self, vial, duty_cycle):
        assert 0 <= duty_cycle <= 1
        led_number = self.led_numbers[vial]
        self.pwm_controller.set_duty_cycle(led_number=led_number, duty_cycle=duty_cycle)

    def get_stirrer_duty_cycle(self, vial):
        led_number = self.led_numbers[vial]
        return self.pwm_controller.get_duty_cycle(led_number=led_number)

    def set_speed(self, vial, speed, accelerate=True):
        assert speed in ["stopped", "low", "high"]  # stopped, slow, fast
        self.check_calibration()
        if speed == "stopped":
            duty_cycle = 0
        else:
            duty_cycle = self.device.device_data["stirrers"]["calibration"][vial][speed]

        lock_acquired = self.pwm_controller.lock.acquire(timeout=3)
        if not lock_acquired:
            raise Exception("Could not acquire lock for setting stirrer speed at time %s" % time.ctime())
        try:
            if 0 < duty_cycle < 0.2 and accelerate:
                accelerate_duty_cycle = self.device.device_data["stirrers"]["calibration"][vial]["high"] * 1.2
                accelerate_duty_cycle = min(accelerate_duty_cycle, 1)
                self._set_duty_cycle(vial, accelerate_duty_cycle)
                time.sleep(0.1)

            self._set_duty_cycle(vial=vial, duty_cycle=duty_cycle)
        finally:
            self.pwm_controller.lock.release()

    def emergency_stop(self):
        lock_acquired = self.pwm_controller.lock.acquire(timeout=3)
        if not lock_acquired:
            raise Exception("Could not acquire lock for emergency stop at time %s" % time.ctime())
        try:
            for vial in range(1, 8):
                self._set_duty_cycle(vial, duty_cycle=0)
        finally:
            self.pwm_controller.lock.release()

    def set_speed_all(self, speed, accelerate=True):
        assert speed in ["stopped", "low", "high"]
        # self.check_calibration()
        lock_acquired = self.pwm_controller.lock.acquire(timeout=3)
        if not lock_acquired:
            raise Exception("Could not acquire lock for setting all stirrer speeds at time %s" % time.ctime())
        try:
            for vial in range(1, 8):
                if speed == "stopped":
                    duty_cycle = 0
                else:
                    duty_cycle = self.device.device_data["stirrers"]["calibration"][vial][speed]
                if 0 < duty_cycle < 0.2 and accelerate:
                    self._set_duty_cycle(vial=vial, duty_cycle=1)
                    time.sleep(0.1)
                self._set_duty_cycle(vial, duty_cycle=duty_cycle)
        finally:
            self.pwm_controller.lock.release()

    def check_calibration(self, vial=-1):
        if vial == -1:
            vials_list = [1, 2, 3, 4, 5, 6, 7]
        else:
            vials_list = [vial]
        for vial in vials_list:
            duty_cycle_slow = self.device.device_data["stirrers"]["calibration"][vial]["low"]
            duty_cycle_fast = self.device.device_data["stirrers"]["calibration"][vial]["high"]
            assert 0 <= duty_cycle_slow <= 1
            assert 0 <= duty_cycle_fast <= 1

    def _measure_rpm_no_lock(self, vial_number=7, estimated_rpm=None):
        if estimated_rpm is None:
            estimated_rpm = self.rpms[vial_number]
        if estimated_rpm is None:
            duty_cycle = self.get_stirrer_duty_cycle(vial_number)  # ftdi lock is checked here
            estimated_rpm = 2000 * duty_cycle
        if estimated_rpm < 10:
            return 0
        ms_per_rotation = 60 / estimated_rpm * 1000
        bits_per_minute = self.freq * 60
        ms_per_bit = 1 / self.freq * 1000
        bits_per_rotation = ms_per_rotation / ms_per_bit
        nbytes_per_rotation = bits_per_rotation / 8
        nbytes = int(nbytes_per_rotation * 0.8) + 16  # Safety factor to avoid overflow

        # Set up the multiplexer for the given vial
        # Read data from SPI port
        # get self.device.lock_ftdi lock
        ftdi_lock_acquired = self.device.lock_ftdi.acquire(timeout=3)
        if not ftdi_lock_acquired:
            raise Exception("Could not acquire lock for reading stirrer speed at time %s" % time.ctime())
        try:
            self.multiplexer_port.write_to(7, [0x00])  # Output pin
            self.multiplexer_port.write_to(2, [vial_number - 1])
            t0 = time.time()

            res = self.fans_spi_port.read(nbytes)
        finally:
            self.device.lock_ftdi.release()
        dt = time.time() - t0
        binstr = "".join([bin(r)[2:].rjust(8, "0") for r in res])

        # Clean up the binary string
        binstr = binstr.replace("1110111", "1111111").replace("11100111", "11111111")

        # Calculate the ratio of '1's in the binary data
        ones_ratio = sum(1 for i in binstr if i == "1") / (8 * nbytes)

        # Find repeated sequences in the binary string
        periods = [len(match.group()) for match in re.finditer(r'(0+|1+)', binstr)]
        periods = periods[1:-1]  # cut first and last incomplete sequences

        # Check if any periods were found
        if len(periods) < 1:
            if estimated_rpm > 400:
                time.sleep(4)
                return self._measure_rpm_no_lock(vial_number, estimated_rpm / 2)
            else:
                return 0

        periods = np.array(periods)

        if len(periods) > 5:
            # remove outliers
            periods = periods[abs(periods - np.median(periods)) < 2 * np.std(periods)]

        if periods[0] > 1000:
            rpm = 60 * self.freq / periods[0] / 4
        else:
            rpm = 60 * self.freq / np.median(periods) / 4
        return rpm

    def measure_rpm(self, vial_number=7):
        # if file db/skip_stirrer_speed_measurement exists, return 0
        if os.path.exists("db/skip_stirrer_speed_measurement"):
            return 0
        lock_acquired = self.pwm_controller.lock.acquire(timeout=3)
        if not lock_acquired:
            raise Exception("Could not acquire lock for measuring stirrer speed at time %s" % time.ctime())
        try:
            rpm = self._measure_rpm_no_lock(vial_number)
        finally:
            self.pwm_controller.lock.release()
        return rpm

    def measure_all_rpms(self, vials_to_measure=(1, 2, 3, 4, 5, 6, 7)):
        results = {vial_number: None for vial_number in range(1, 8)}
        for vial_number in vials_to_measure:
            results[vial_number] = self.measure_rpm(vial_number)
        for k,v in results.items():
            if v is not None:
                self.rpms[k] = v
        return results

    def get_calibration_curve(self, vial, n_points=10, time_sleep=2):
        min_duty_cycle = self.device.device_data["stirrers"]["calibration"][vial]["low"]
        max_duty_cycle = self.device.device_data["stirrers"]["calibration"][vial]["high"]
        rpm_dc = {}
        #accelerate to max duty cycle
        self._set_duty_cycle(vial, max_duty_cycle)
        time.sleep(3)
        # start measuring from max duty cycle to min duty cycle
        estimated_rpm = 3000
        duty_cycles_measured = np.linspace(min_duty_cycle, max_duty_cycle, n_points)[::-1]
        for i in range(len(duty_cycles_measured)):
            duty_cycle = duty_cycles_measured[i]
            if duty_cycle > 0:
                self._set_duty_cycle(vial, duty_cycle)
                time.sleep(time_sleep)
                rpm = self.measure_rpm(vial, estimated_rpm=estimated_rpm)
                rpm_dc[duty_cycle] = rpm
                estimated_rpm = rpm*duty_cycles_measured[i+1]/duty_cycles_measured[i] if i < len(duty_cycles_measured)-1 else rpm
        return rpm_dc