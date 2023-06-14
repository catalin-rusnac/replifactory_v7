import os
import time

import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


def od_calibration_function(x, a, b, c, d, g):
    """
    converts signal mV to optical density
    4 Parameter logistic function
    adapted from:
    https://weightinginbayesianmodels.github.io/poctcalibration/calib_tut4_curve_background.html

    :param x: signal voltage in millivolts
    :param a: On the scale of y; horizontal asymptote as x goes to infinity.
    :param b: Hill coefficient
    :param c: Inflection point.
    :param d: On the scale of y; horizontal asymptote as x goes, in theory, to negative infinity,
              but, in practice, to zero.
    :return: y - optical density
    """
    y = d + (a - d) / ((1 + (x / c) ** b) ** g)
    return y


def od_calibration_function_inverse(y, a, b, c, d, g):
    """
    converts optical density to signal mV

    Inverse of 4 Parameter logistic function
    adapted from:
    https://weightinginbayesianmodels.github.io/poctcalibration/calib_tut4_curve_background.html

    :param y: optical density
    :param a: On the scale of y; horizontal asymptote as x goes to infinity.
    :param b: Hill coefficient
    :param c: Inflection point.
    :param d: On the scale of y; horizontal asymptote as x goes, in theory, to negative infinity,
              but, in practice, to zero.
    :return: x - signal voltage in millivolts
    """
    x = c * (((a - d) / (y - d)) ** (1 / g) - 1) ** (1 / b)
    return x


class OdSensor:
    def __init__(self, device, vial_number):
        self.device = device
        self.vial_number = vial_number

    def mv_to_od(self, mv):
        coefs = self.device.device_data['ods']['calibration_coefs'][self.vial_number]
        a, b, c, d, g = coefs
        return od_calibration_function(mv, a, b, c, d, g)

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
        background = self.measure_background_intensity()[0]
        transmitted = self.measure_transmitted_intensity()[0]
        if self.device.directory is not None:
            self.log_mv(background=background, transmitted=transmitted)
        signal = transmitted - background
        if signal < 0:
            signal = 0
        return signal

    def measure_od(self):
        signal = self.measure_signal()
        od = self.mv_to_od(signal)
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
        coefs, _ = curve_fit(
            od_calibration_function_inverse,
            calibration_od,
            calibration_mv,
            maxfev=5000,
            p0=(20, 5, 0.07, -0.2, 1),
            bounds=[(3, 0, 0, -0.5, 0), (200, 10, 20, 0.1, 5)],
            sigma=calibration_mv_err,
        )
        coefs = [round(i, 3) for i in coefs]
        print(coefs)
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
