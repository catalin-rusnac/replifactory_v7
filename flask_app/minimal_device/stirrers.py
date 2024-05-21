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

        if self.device.is_connected():
            self.connect()

    def connect(self):
        self.pwm_controller = self.device.pwm_controller
        if self.pwm_controller.port is not None:
            # for 3-pin fan speed feedback
            self.multiplexer_port = self.device.i2c.get_port(
                self.device.PORT_GPIO_MULTIPLEXER_STIRRERS
            )
            # all GPIO pins output
            self.multiplexer_port.write_to(6, [0x00])
            # all GPIO pins output
            self.multiplexer_port.write_to(7, [0x00])

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

    def _get_duty_cycle(self, vial):
        led_number = self.led_numbers[vial]
        return self.pwm_controller.get_duty_cycle(led_number=led_number)

    def set_speed(self, vial, speed, accelerate=True):
        assert speed in ["stopped", "low", "high"]  # stopped, slow, fast
        self.check_calibration()
        if speed == "stopped":
            duty_cycle = 0
        else:
            duty_cycle = self.device.device_data["stirrers"]["calibration"][vial][speed]

        assert self.pwm_controller.lock.acquire(timeout=60)
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
        assert self.pwm_controller.lock.acquire(timeout=1)
        try:
            for vial in range(1, 8):
                self._set_duty_cycle(vial, duty_cycle=0)
        finally:
            self.pwm_controller.lock.release()

    def set_speed_all(self, speed, accelerate=True):
        assert speed in ["stopped", "low", "high"]
        # self.check_calibration()
        assert self.pwm_controller.lock.acquire(timeout=60)
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
            assert 0 <= duty_cycle_slow <= duty_cycle_fast <= 1

    def get_speed(self, vial_number=7, estimated_rpm=3000):
        ## develop this function while running device_test.py
        # print("estimated_rps: ", estimated_rpm / 60)
        # print("ms per rotation estimated: %.2f" % (1000 / estimated_rpm * 60))
        ms_per_rotation = 60 / estimated_rpm * 1000
        bits_per_minute = self.freq * 60
        ms_per_bit = 1 / self.freq * 1000
        bits_per_rotation = ms_per_rotation / ms_per_bit
        nbytes_per_rotation = bits_per_rotation / 8
        nbytes = int(nbytes_per_rotation*0.8)+16  # Safety factor to avoid overflow

        # print("ms measured total:", ms_per_bit * nbytes * 8)

        # Set up the multiplexer for the given vial
        self.multiplexer_port.write_to(7, [0x00])  # Output pin
        self.multiplexer_port.write_to(2, [vial_number-1])
        t0 = time.time()
        # Read data from SPI port
        res = self.fans_spi_port.read(nbytes)
        # print("Time taken:", time.time() - t0)
        binstr = "".join([bin(r)[2:].rjust(8, "0") for r in res])

        # Clean up the binary string
        binstr = binstr.replace("1110111", "1111111").replace("11100111", "11111111")

        # Calculate the ratio of '1's in the binary data
        ones_ratio = sum(1 for i in binstr if i == "1") / (8 * nbytes)

        # Find repeated sequences in the binary string
        periods = [len(match.group()) for match in re.finditer(r'(0+|1+)', binstr)]
        periods = periods[1:-1] # cut first and last incomplete sequences

        # Check if any periods were found
        if len(periods) < 1:
            print("No periods found")
            print(binstr)
            print("New estimation:", estimated_rpm / 2)
            time.sleep(3)
            if estimated_rpm > 300:
                return self.get_speed(vial_number, estimated_rpm / 2)
            else:
                return 0

        periods = np.array(periods)
        if periods[0] < 100:
            rpm = 60 * self.freq / periods.mean() / 4
        else:
            rpm = 60 * self.freq / periods[0] / 4
        err = periods.std() / periods.mean()

        # Print the results
        # print("Bits:", len(binstr), "%.2f %%"% ones_ratio, "periods:", len(periods), periods)
        # print("Speed:", int(rpm), "RPM ±", int(err * rpm), "Error: %.1f%%" % (err * 100))
        # print("ms per rotation actual: %.3f" % (1000 / (rpm / 60)))
        return rpm

    def get_all_speeds(self):
        duty_cycles = {vial_number: self._get_duty_cycle(vial_number) for vial_number in range(1, 8)}
        results = {vial_number: 0 for vial_number in range(1, 8)}
        for vial_number, duty_cycle in duty_cycles.items():
            if duty_cycle > 0:
                results[vial_number] = self.get_speed(vial_number, estimated_rpm=2000*duty_cycle)
        estimated_rpms = {vial_number: 4000 * duty_cycle for vial_number, duty_cycle in duty_cycles.items()}
        return results

    def get_calibration_curve(self, vial, n_points=10, time_sleep=2):
        min_duty_cycle = self.device.device_data["stirrers"]["calibration"][vial]["low"]
        max_duty_cycle = self.device.device_data["stirrers"]["calibration"][vial]["high"]
        rpm_dc = {}
        import matplotlib.pyplot as plt
        #accelerate to max duty cycle
        self._set_duty_cycle(vial, max_duty_cycle)
        time.sleep(3)
        # start measuring from max duty cycle to min duty cycle
        estimated_rpm = 3000
        for duty_cycle in np.linspace(min_duty_cycle, max_duty_cycle, n_points)[::-1]:
            self._set_duty_cycle(vial, duty_cycle)
            time.sleep(time_sleep)
            rpm = self.get_speed(vial, estimated_rpm=estimated_rpm)
            rpm_dc[duty_cycle] = rpm
            estimated_rpm = rpm
        plt.plot(list(rpm_dc.keys()), list(rpm_dc.values()), "ro-")
        plt.title("Vial %d RPM vs Duty Cycle" % vial)
        plt.xlabel("Duty Cycle")
        plt.ylabel("RPM")
        plt.ylim(0, 5000)
        plt.xlim(0, 1.05)
        plt.show()

        return rpm_dc