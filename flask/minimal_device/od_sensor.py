import os
import time


def measure_od_all(device, vials_to_measure=(1, 2, 3, 4, 5, 6, 7)):
    available_vials = []
    for v in vials_to_measure:
        if device.locks_vials[v].acquire(blocking=False):
            available_vials += [v]

    od_values = {}
    if len(available_vials) > 0:
        # Stop stirrers completely and wait 10 seconds for vortex to settle bubbles to raise above laser level.
        # Waiting enough time for the smallest bubbles to raise improves the measurement precision.
        # for vial in available_vials:
        #     device.stirrers.set_speed(vial=vial, speed=3)
        # time.sleep(2)
        # Stir at minimum speed (without forming vortex) to homogenize turbidity and prevent precipitation
        for vial in available_vials:
            device.stirrers.set_speed(vial=vial, speed=0)
        time.sleep(4)
        # for vial in available_vials:
        #     device.stirrers.set_speed(vial=vial, speed=1)
        # time.sleep(3)
        # for vial in available_vials:
        #     device.stirrers.set_speed(vial=vial, speed=0)
        # time.sleep(1)
        for vial in available_vials:
            od = device.od_sensors[vial].measure_od()
            od_values[vial] = od
        for vial in available_vials:
            device.stirrers.set_speed(vial=vial, speed=2)
        # time.sleep(2)
        # for vial in available_vials:
        #     device.stirrers.set_speed(vial=vial, speed=3)
        # time.sleep(5)
        # for vial in available_vials:
        #     device.stirrers.set_speed(vial=vial, speed=2)
        # for vial in available_vials:
        #     device.stirrers.set_speed(vial=vial, speed=3)
        # time.sleep(2)
        # for vial in available_vials:
        #     device.stirrers.set_speed(vial=vial, speed=2)
        # time.sleep(1)
        for v in available_vials:
            device.locks_vials[v].release()

        # assign values to culture.od parameter, which writes to csv file and calculates mu
        for v in od_values.keys():
            device.cultures[v].od = od_values[v]
    return od_values


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
        # self.coefs = ()
        # self.fit_calibration_function()

    # @property
    # def coefs(self):
    #     return self.device.device_data['ods']['calibration_coefs'][self.vial_number]

    # @coefs.setter
    # def coefs(self, value):
    #     self.device.calibration_coefs_od[self.vial_number] = list(value)
    #     try:
    #         self.device.save()
    #     except Exception:
    #         pass

    def calibration_function(self, mv):
        coefs = self.device.device_data['ods']['calibration_coefs'][self.vial_number]
        if len(coefs) < 5:
            return None
        else:
            a, b, c, d, g = coefs
            return od_calibration_function(mv, a, b, c, d, g)

    @property
    def calibration_od_to_mv(self):
        return self.device.calibration_od_to_mv[self.vial_number]

    @calibration_od_to_mv.setter
    def calibration_od_to_mv(self, value):
        value = float(value)
        self.device.calibration_od_to_mv[self.vial_number] = value
        # self.fit_calibration_function()
        self.device.save()

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
        return signal

    def measure_od(self):
        signal = self.measure_signal()
        od = self.calibration_function(signal)
        return od

    def check(self):
        assert self.calibration_function is not None
        v = self.vial_number
        signal = self.device.od_sensors[v].measure_signal()
        if signal >= 15:
            color = bcolors.OKGREEN
        elif 10 < signal < 15:
            color = bcolors.WARNING
        else:
            color = bcolors.FAIL
        print("vial %d OD sensor: " % v + color + "%.2f mV" % signal + bcolors.ENDC)

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
