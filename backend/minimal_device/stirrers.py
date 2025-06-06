import os
import re
import time
import numpy as np

class Stirrers:
    led_numbers = {stirrer: 7 - stirrer for stirrer in [1, 2, 3, 4, 5, 6, 7]}
    cooling_fan_led_number = 7

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

    def set_cooling_fan_duty_cycle(self, duty_cycle):
        assert 0 <= duty_cycle <= 1
        self.pwm_controller.set_duty_cycle(led_number=self.cooling_fan_led_number, duty_cycle=1-duty_cycle)

    def get_stirrer_duty_cycle(self, vial):
        led_number = self.led_numbers[vial]
        return self.pwm_controller.get_duty_cycle(led_number=led_number)

    def set_speed(self, vial, speed, accelerate=False):
        assert speed in ["stopped", "low", "high"]  # stopped, slow, fast
        self.check_calibration()
        if speed == "stopped":
            duty_cycle = 0
        else:
            duty_cycle = self.device.device_data["stirrers"]["calibration"][vial][speed]

        if 0 < duty_cycle < 0.5 and accelerate:
            accelerate_duty_cycle = self.device.device_data["stirrers"]["calibration"][vial]["high"] * 1.5
            accelerate_duty_cycle = min(accelerate_duty_cycle, 1)
            self._set_duty_cycle(vial, accelerate_duty_cycle)
            time.sleep(0.01)

        self._set_duty_cycle(vial=vial, duty_cycle=duty_cycle)

    def emergency_stop(self):
        for vial in range(1, 8):
            self._set_duty_cycle(vial, duty_cycle=0)

    def set_speed_all(self, speed, accelerate=False):
        assert speed in ["stopped", "low", "high"]
        for vial in range(1, 8):
            if speed == "stopped":
                duty_cycle = 0
            else:
                duty_cycle = self.device.device_data["stirrers"]["calibration"][vial][speed]
            if 0 < duty_cycle < 0.2 and accelerate:
                self._set_duty_cycle(vial=vial, duty_cycle=duty_cycle*2)
                time.sleep(0.05)
            self._set_duty_cycle(vial, duty_cycle=duty_cycle)

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
            estimated_rpm = 10000 * duty_cycle
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
        ftdi_lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
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

    def measure_rpm(self, vial_number=7, estimated_rpm=None):
        # if file db/skip_stirrer_speed_measurement exists, return 0
        if os.path.exists("db/skip_stirrer_speed_measurement"):
            return 0
        rpm = self._measure_rpm_no_lock(vial_number, estimated_rpm=estimated_rpm)
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
        """
        Generate a calibration curve by mapping duty cycles to measured RPM for a given stirrer vial.

        This function first accelerates the stirrer to its maximum duty cycle, then iterates
        from the maximum down to the minimum duty cycle, measuring the RPM at each step.
        An estimated RPM for the next duty cycle is also calculated for informational purposes.

        Parameters:
            vial (str/int): The identifier for the stirrer vial.
            n_points (int): Number of measurement points between min and max duty cycles.
            time_sleep (float): Time (in seconds) to wait after setting a duty cycle before measuring RPM.

        Returns:
            dict: A dictionary mapping each duty cycle (float) to its measured RPM (float).
        """
        # Retrieve minimum and maximum duty cycle values from device calibration data.
        calibration_data = self.device.device_data["stirrers"]["calibration"][vial]
        min_duty_cycle = calibration_data["low"]
        max_duty_cycle = calibration_data["high"]

        # Dictionary to store RPM measurements keyed by duty cycle.
        rpm_by_duty = {}

        # Accelerate the stirrer to the maximum duty cycle to ensure full speed.
        self._set_duty_cycle(vial, max_duty_cycle)
        time.sleep(3)

        # Generate an array of duty cycles from maximum to minimum.
        duty_cycles = np.linspace(min_duty_cycle, max_duty_cycle, n_points)[::-1]

        print("\nStarting stirrer calibration measurements:")
        print("-" * 50)
        for i, duty_cycle in enumerate(duty_cycles):
            # Skip any invalid or zero duty cycles.
            if duty_cycle <= 0:
                continue

            # Set the current duty cycle and wait for stabilization.
            self._set_duty_cycle(vial, duty_cycle)
            time.sleep(time_sleep)

            # Measure the RPM at this duty cycle.
            rpm = self.measure_rpm(vial)
            rpm_by_duty[duty_cycle] = rpm

            # Calculate an estimated RPM for the next duty cycle (if available).
            if i < len(duty_cycles) - 1:
                next_duty = duty_cycles[i + 1]
                estimated_rpm = rpm * next_duty / duty_cycle
            else:
                estimated_rpm = rpm

            # Display the measurement results in a nicely formatted output.
            # print(
            #     f"Duty Cycle: {duty_cycle:6.4f} | Measured RPM: {rpm:8.2f} | Estimated Next RPM: {estimated_rpm:8.2f}")

        print("-" * 50)
        print("Calibration complete.\n")
        return rpm_by_duty

    def get_all_calibration_curves(self, n_points=4, n_repeats=3):
        """
        Generate calibration curves for all stirrers by mapping duty cycles to measured RPM.

        Procedure:
          1. Upward sweep:
             - For each stirrer, start at 0.26 duty cycle.
             - Increase linearly to min(1, calibration_data["high"] * 1.2).
             - At each step, take several RPM measurements.
          2. Pause:
             - Stop all stirrers (set duty cycle to 0) and wait for 5 seconds.
          3. Downward sweep:
             - For each stirrer, start at 0.24 duty cycle.
             - Decrease linearly to calibration_data["low"] * 0.8.
             - At each step, take several RPM measurements.
          4. Plot:
             - For each stirrer, average the RPM values at each duty cycle.
             - Plot the calibration data sorted by duty cycle.
        """
        curves = {vial: {} for vial in range(1, 8)}

        # For each vial, calculate the duty cycle sweep values for the upward and downward sweeps.
        up_sweeps = {}
        down_sweeps = {}
        for vial in range(1, 8):
            calib = self.device.device_data["stirrers"]["calibration"][vial]
            low_duty = calib["low"]
            high_duty = calib["high"]
            # Upward sweep: from 0.26 up to min(1, high_duty*1.2)
            up_end = min(1, high_duty * 1.02)
            up_sweeps[vial] = np.linspace(0.26, up_end, n_points)
            # Downward sweep: from 0.24 down to low_duty*0.8 (np.linspace will produce descending values if 0.24 > low_duty*0.8)
            down_end = low_duty * 0.5
            down_sweeps[vial] = np.linspace(0.24, down_end, n_points)

        # === Upward Sweep ===
        # print("Starting upward sweep calibration...")
        for point in range(n_points):
            # Set the duty cycle for each vial to the current upward value.
            for vial in range(1, 8):
                duty = up_sweeps[vial][point]
                self._set_duty_cycle(vial, duty)
            time.sleep(5)
            # Take multiple RPM measurements at this duty cycle.
            for _ in range(n_repeats):
                for vial in range(1, 8):
                    duty = up_sweeps[vial][point]
                    rpm = self.measure_rpm(vial)
                    duty = float(f"{duty:.3f}")
                    rpm = float(f"{rpm:.2f}")
                    curves[vial].setdefault(duty, []).append(rpm)
                    print(f"Vial: {vial}, Upward Duty Cycle: {duty}, RPM: {rpm}")
                time.sleep(2)

        # === Pause: Stop stirrers at 0 duty cycle for 5 seconds ===
        # print("Pausing: Setting stirrers to 0 duty cycle for 5 seconds...")
        for vial in range(1, 8):
            self._set_duty_cycle(vial, 0)
        time.sleep(5)

        # === Downward Sweep ===
        # print("Starting downward sweep calibration...")
        # set
        for point in range(n_points):
            # Set the duty cycle for each vial to the current downward value.
            for vial in range(1, 8):
                duty = down_sweeps[vial][point]
                self._set_duty_cycle(vial, duty)
            time.sleep(5)
            # Take multiple RPM measurements at this duty cycle.
            for _ in range(n_repeats):
                for vial in range(1, 8):
                    duty = down_sweeps[vial][point]
                    rpm = self.measure_rpm(vial)
                    curves[vial].setdefault(duty, []).append(rpm)
                    # print(f"Vial: {vial}, Downward Duty Cycle: {duty:.3f}, RPM: {rpm:.2f}")
                time.sleep(2)

        # Optionally, turn off the stirrers at the end.
        for vial in range(1, 8):
            self._set_duty_cycle(vial, 0)
        # save to file
        self.device.device_data["stirrers"]["speed_profiles"] = curves
        self.device.eeprom.save_config_to_eeprom()
        return curves

    @staticmethod
    def plot_stirrer_calibration_curves(data):
        import plotly.graph_objects as go
        fig = go.Figure()
        for stirrer in data:
            d = data[stirrer]
            x = list(d.keys())
            x = sorted(x)
            y = [np.mean(d[k]) for k in x]
            yerr = [np.std(d[k]) for k in x]
            fig.add_trace(go.Scatter(x=x, y=y, mode='markers+lines', name=f'Stirrer {stirrer}',
                                     error_y=dict(type='data', array=yerr)))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        fig.update_layout(title='Stirrer calibration curves at {}'.format(current_time),
                          xaxis_title='Duty Cycle', yaxis_title='RPM')
        fig.write_html("stirrer_calibration_curves.html")



