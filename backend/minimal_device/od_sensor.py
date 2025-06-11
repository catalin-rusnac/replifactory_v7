import os
import time

import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from logger.logger import logger


# def od_calibration_function(x, a, b, c, d, g):
#     """
#     converts signal mV to optical density
#     4 Parameter logistic function
#     adapted from:
#     https://weightinginbayesianmodels.github.io/poctcalibration/calib_tut4_curve_background.html

#     :param x: signal voltage in millivolts
#     :param a: On the scale of y; horizontal asymptote as x goes to infinity.
#     :param b: Hill coefficient
#     :param c: Inflection point.
#     :param d: On the scale of y; horizontal asymptote as x goes, in theory, to negative infinity,
#               but, in practice, to zero.
#     :return: y - optical density
#     """
#     y = d + (a - d) / ((1 + (x / c) ** b) ** g)
#     return y


# def od_calibration_function_inverse(y, a, b, c, d, g):
#     """
#     converts optical density to signal mV

#     Inverse of 4 Parameter logistic function
#     adapted from:
#     https://weightinginbayesianmodels.github.io/poctcalibration/calib_tut4_curve_background.html

#     :param y: optical density
#     :param a: On the scale of y; horizontal asymptote as x goes to infinity.
#     :param b: Hill coefficient
#     :param c: Inflection point.
#     :param d: On the scale of y; horizontal asymptote as x goes, in theory, to negative infinity,
#               but, in practice, to zero.
#     :return: x - signal voltage in millivolts
#     """
#     x = c * (((a - d) / (y - d)) ** (1 / g) - 1) ** (1 / b)
#     return x

def BeerLambertScaled(sig, blank, scaling):
    """convert signal to optical density using Beer-Lambert law and scaling factor"""
    return -np.log10(sig / blank) * scaling

def BeerLambertScaledInverse(od, blank, scaling):
    """convert optical density to signal using Beer-Lambert law and scaling factor"""
    return blank * 10**(-od / scaling)


class OdSensor:
    def __init__(self, device, vial_number):
        self.device = device
        self.vial_number = vial_number

    def mv_to_od(self, mv):
        coefs = self.device.device_data['ods']['calibration_coefs'][self.vial_number]
        if len(coefs) > 3:
            self.fit_calibration_function()
            print("fit calibration function with beer-lambert scaled because there were too many calibration coefficients")
            coefs = self.device.device_data['ods']['calibration_coefs'][self.vial_number]
        blank_signal, scaling = coefs
        # if the minimum value in calibration is equal to 0 or 0.0, use it as blank
        lowest_od_in_calibration = min(self.device.device_data['ods']['calibration'][self.vial_number].keys())
        if float(lowest_od_in_calibration) == 0.0:
            blank_signal = self.device.device_data['ods']['calibration'][self.vial_number][lowest_od_in_calibration]
        return BeerLambertScaled(mv, blank_signal, scaling)

    def assign_blank(self, value):
        """assign a blank value to the vial, assuming known scaling factor"""
        try: 
            self.device.device_data['ods']['blank'][self.vial_number]['0'] = value
        except:
            self.device.device_data['ods']['blank'] = {self.vial_number: {'0': value}}
        if self.device.is_connected():
            self.device.eeprom.save_config_to_eeprom()
    
    def measure_transmitted_intensity(self):
        """
        returns the intensity of the transmitted light
        :return:
        """
        self.device.photodiodes.switch_to_vial(vial=self.vial_number)
        self.device.lasers.switch_on(vial=self.vial_number)
        time.sleep(0.02)
        mv, err = self.device.photodiodes.measure(gain=8, bitrate=16)
        self.device.lasers.switch_off(vial=self.vial_number)
        return mv, err

    def measure_background_intensity(self):
        """
        returns the intensity of the background light (no laser)
        :return:
        """
        self.device.photodiodes.switch_to_vial(vial=self.vial_number)
        mv, err = self.device.photodiodes.measure(gain=8, bitrate=16)
        return mv, err

    def log_mv(self, background, transmitted):
        directory = os.path.join(self.device.directory, "vial_%d" % self.vial_number)
        if not os.path.exists(directory):
            os.mkdir(directory)

        filepath = os.path.join(directory, "photodiode_millivolts.csv")
        if not os.path.exists(filepath):
            with open(filepath, "w+") as f:
                f.write("time,transmitted,background\n")
        with open(filepath, "a") as f:
            data_string = "%d,%.4f,%.4f\n" % (int(time.time()), transmitted, background)
            f.write(data_string)

    def measure_signal(self):
        lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
        if not lock_acquired:
            raise Exception("Could not acquire lock to measure OD signal at time %s" % time.ctime())
        try:
            background = self.measure_background_intensity()[0]
            transmitted = self.measure_transmitted_intensity()[0]
        finally:
            self.device.lock_ftdi.release()
        if self.device.directory is not None:
            self.log_mv(background=background, transmitted=transmitted)
        signal = transmitted - background
        if signal < 0:
            signal = 0
        return signal

    def measure_od(self):
        signal = self.measure_signal()
        od = self.mv_to_od(signal)
        od = float(od)
        self.device.device_data["ods"]['states'][self.vial_number] = od
        self.device.device_data["ods"]['odsignals'][self.vial_number] = signal
        return od, signal

    def measure_od_calibration(self, odValue):
        sig = self.measure_signal()
        self.device.device_data['ods']['calibration'][self.vial_number][odValue] = sig

    def check(self):
        v = self.vial_number
        signal = self.device.od_sensors[v].measure_signal()
        if signal >= 15:
            color = bcolors.OKGREEN
        elif 10 < signal < 15:
            color = bcolors.WARNING
        else:
            color = bcolors.FAIL
        print("vial %d OD sensor: " % v + color + "%.2f mV" % signal + bcolors.ENDC)

    def fit_calibration_function(self):
        calibration_od = np.array(list(self.device.device_data['ods']['calibration'][self.vial_number].keys()))
        calibration_mv = np.array(list(self.device.device_data['ods']['calibration'][self.vial_number].values()))

        mask = np.array([item is not None for item in calibration_mv])
        calibration_mv = calibration_mv[mask]
        calibration_od = calibration_od[mask]
        calibration_od = np.array([float(i) for i in calibration_od])
        logger.info(f"calibration_od: {calibration_od}")
        logger.info(f"calibration_mv: {calibration_mv}")
        try:
            blank_signal = calibration_mv[calibration_od == 0.0][0]
            blank_bounds = (blank_signal - 0.00001, blank_signal + 0.00001)
        except:
            logger.info(f"no 0.0 in calibration for vial {self.vial_number}, using default bounds")
            blank_signal = 50
            blank_bounds = (0.5, 200)

        if len(calibration_mv.shape)==1:
            calibration_mv = np.array([[i,i,i] for i in calibration_mv])
        max_len = len(max(calibration_mv, key=len))
        calibration_mv_filled = np.array(
            [list(i) + [np.nan] * (max_len - len(i)) for i in calibration_mv]
        )
        print(calibration_mv_filled)
        calibration_mv_err = np.nanstd(calibration_mv_filled, 1)
        print(calibration_mv_err)
        # calibration_mv = np.array(list(self.calibration_od_to_mv.values())).mean(1)
        calibration_mv = np.nanmean(calibration_mv_filled, 1)

        calibration_mv_err += 0.01  # allows curve fit with single measurements
        # coefficients for fitting beer lambert scaled are blank and scaling factor
        # blank bounds are 0.5-200, scaling factor bounds are 1-3
        # initial guess is 50mV for blank and 1.6 for scaling factor
        
        
        coefs, _ = curve_fit(
            BeerLambertScaledInverse,
            calibration_od,
            calibration_mv,
            maxfev=5000,
            p0=(blank_signal, 1.6),
            bounds=[(blank_bounds[0], 0.1), (blank_bounds[1], 5)],
            sigma=calibration_mv_err,
        )
        coefs = [round(i, 4) for i in coefs]
        coefs = [float(i) for i in coefs]
        blank_signal, scaling = coefs
        logger.info(f"fitted calibration function for vial {self.vial_number} with blank {blank_signal} and scaling {scaling}")
        # a, b, c, d, g = coefs
        self.device.device_data['ods']['calibration_coefs'][self.vial_number] = coefs
        if self.device.is_connected():
            self.device.eeprom.save_config_to_eeprom()
        # self.plot_calibration_curve()

    def plot_calibration_curve(self):

        plt.figure(figsize=[4, 2], dpi=150)

        calibration_od = np.array(list(self.device.device_data['ods']['calibration'][self.vial_number].keys()))
        calibration_mv = np.array(list(self.device.device_data['ods']['calibration'][self.vial_number].values()))
        if len(calibration_mv.shape)==1:
            calibration_mv = np.array([[i,i+0.1,i-0.1] for i in calibration_mv])
        max_len = len(max(calibration_mv, key=len))
        calibration_mv_filled = np.array(
            [list(i) + [np.nan] * (max_len - len(i)) for i in calibration_mv]
        )
        calibration_mv_err = np.nanstd(calibration_mv_filled, 1)
        calibration_mv = np.nanmean(calibration_mv_filled, 1)

        xmin = 0
        xmax = max(max(calibration_mv),140) + 10
        x = np.linspace(xmin, xmax, 501)
        y = self.mv_to_od(x)
        a, b, c, d, g = self.device.device_data['ods']['calibration_coefs'][self.vial_number]
        plt.plot(x, y, "b:", label="function fit")
        plt.title(
            "od_max:%.2f slope: %.2f mv_inflec: %.2f od_min: %.2f, g: %.2f"
            % (a, b, c, d, g),
            fontsize=8,
        )
        #     plt.plot(calibration_mv, calibration_od, "r.")
        plt.errorbar(
            calibration_mv,
            calibration_od,
            xerr=calibration_mv_err,
            fmt="b.",
            label="calibration data",
        )
        plt.xlabel("signal[mV] (background-subtracted)")
        plt.ylabel("OD")
        # plt.ylim([-1, 5])
        plt.axhline(0, ls="--", c="k", lw=0.5)
        # plt.title("Vial %d OD calibration" % self.vial_number, fontsize=8)

        plt.legend()
        plt.show()

    def measure_optical_signals(self):
        red_intensities = {vial: {i: None for i in np.linspace(0, 1, 11)} for vial in range(1, 8)}
        green_intensities = {vial: {i: None for i in np.linspace(0, 1, 11)} for vial in range(1, 8)}
        blue_intensities = {vial: {i: None for i in np.linspace(0, 1, 11)} for vial in range(1, 8)}
        laser_intensity = {vial: None for vial in range(1, 8)}
        self.device.rgb_leds.set_flicker_frequency(1024)
        for vial in range(1, 8):
            self.device.photodiodes.switch_to_vial(vial)
            for red in np.linspace(0, 1, 11):
                self.device.rgb_leds.set_led(led_number=vial, red=red, green=0, blue=0)
                red_intensities[vial][red] = [self.device.photodiodes.measure()[0] for _ in range(10)]
                self.device.rgb_leds.set_led(led_number=vial, red=0, green=0, blue=0)
            for green in np.linspace(0, 1, 11):
                self.device.rgb_leds.set_led(led_number=vial, red=0, green=green, blue=0)
                green_intensities[vial][green] = [self.device.photodiodes.measure()[0] for _ in range(10)]
                self.device.rgb_leds.set_led(led_number=vial, red=0, green=0, blue=0)
            for blue in np.linspace(0, 1, 11):
                self.device.rgb_leds.set_led(led_number=vial, red=0, green=0, blue=blue)
                blue_intensities[vial][blue] = [self.device.photodiodes.measure()[0] for _ in range(10)]
                self.device.rgb_leds.set_led(led_number=vial, red=0, green=0, blue=0)
            self.device.lasers.switch_on(vial=vial)
            laser_intensity[vial] = [self.device.photodiodes.measure()[0] for _ in range(10)]
            self.device.lasers.switch_off(vial=vial)
        return red_intensities, green_intensities, blue_intensities, laser_intensity

    def measure_optical_signal_max(self):
        """
        Measure the maximum signal for each LED color and laser.
        returns dictionary with vial number as key and maximum signal as value for each color and laser
        :return: red_max_signal, green_max_signal, blue_max_signal, laser_signal

        """
        red_max_signal = {v: None for v in range(1, 8)}
        green_max_signal = {v: None for v in range(1, 8)}
        blue_max_signal = {v: None for v in range(1, 8)}
        laser_signal = {v: None for v in range(1, 8)}
        for vial in range(1, 8):
            self.device.photodiodes.switch_to_vial(vial)
            self.device.rgb_leds.set_led(led_number=vial, red=1, green=0, blue=0)
            red_max_signal[vial] = self.device.photodiodes.measure()[0]
            self.device.rgb_leds.set_led(led_number=vial, red=0, green=1, blue=0)
            green_max_signal[vial] = self.device.photodiodes.measure()[0]
            self.device.rgb_leds.set_led(led_number=vial, red=0, green=0, blue=1)
            blue_max_signal[vial] = self.device.photodiodes.measure()[0]
            self.device.rgb_leds.set_led(led_number=vial, red=0, green=0, blue=0)
            self.device.lasers.switch_on(vial=vial)
            laser_signal[vial] = self.device.photodiodes.measure()[0]
            self.device.lasers.switch_off(vial=vial)
        self.device.device_data["ods"]["max_signal"] = {
            "red": red_max_signal,
            "green": green_max_signal,
            "blue": blue_max_signal,
            "laser": laser_signal,
        }
        return red_max_signal, green_max_signal, blue_max_signal, laser_signal


    @staticmethod
    def plot_optical_signals(red_intensities, green_intensities, blue_intensities, laser_intensity):
        """
        Generate a bar chart for optical signals.

        :param red_intensities: Dictionary of red LED intensities {vial: measurement}
        :param green_intensities: Dictionary of green LED intensities {vial: measurement}
        :param blue_intensities: Dictionary of blue LED intensities {vial: measurement}
        :param laser_intensity: Dictionary with single intensity for the laser {vial: measurement}
        """
        import plotly.graph_objects as go
        fig = go.Figure()

        colors = {
            'red': 'rgba(255, 0, 0, 1)',
            'green': 'rgba(0, 255, 0, 1)',
            'blue': 'rgba(0, 0, 255, 1)',
            'laser': 'rgba(139, 0, 0, 1)'  # Dark red for laser
        }
        fig.add_trace(go.Bar(
            x=list(laser_intensity.keys()),
            y=[np.mean(laser_intensity[k]) for k in laser_intensity.keys()],
            name="Laser (nominal power)",
            marker=dict(color=colors['laser']),
        ))

        fig.add_trace(go.Bar(
            x=list(red_intensities.keys()),
            y=[np.mean(red_intensities[k]) for k in red_intensities.keys()],
            name="Red LED (max power)",
            marker=dict(color=colors['red']),
        ))

        fig.add_trace(go.Bar(
            x=list(green_intensities.keys()),
            y=[np.mean(green_intensities[k]) for k in green_intensities.keys()],
            name="Green LED (max power)",
            marker=dict(color=colors['green']),
        ))

        fig.add_trace(go.Bar(
            x=list(blue_intensities.keys()),
            y=[np.mean(blue_intensities[k]) for k in blue_intensities.keys()],
            name="Blue LED (max power)",
            marker=dict(color=colors['blue']),
        ))

        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        fig.update_layout(
            title="Optical Signals at %s" % current_time,
            xaxis_title="Vial",
            yaxis_title="Signal [mV]",
            barmode="group",  # Group bars together
            bargap=0.2,  # Space between bars
            bargroupgap=0.1)


        # Save as an interactive HTML file
        fig.write_html("optical_signals.html")

        return fig


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
