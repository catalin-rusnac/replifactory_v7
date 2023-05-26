import math

# import matplotlib.pyplot as plt
# import numpy as np
# import pandas as pd
# import scipy.optimize
from scipy.optimize import fsolve

from .stepper import Stepper


# def calibrate_pump(device, pump_number):
#     p = device.pumps[pump_number]
#     n_rotations = float(input("How many rotations?"))
#     n_repetitions = float(input("How many repetitions?"))
#     assert n_repetitions % 1 == 0
#     n_repetitions = int(n_repetitions)
#     total_volume = n_rotations * n_repetitions * 0.1
#     p.fit_calibration_function()
#     if callable(p.calibration_function):
#
#         def opt_function(volume):
#             return p.calibration_function(volume) - n_rotations
#
#         predicted_mls = fsolve(opt_function, 1)[0]
#         predicted_total_mls = predicted_mls * n_repetitions
#         print("Predicted %.2f mls from existing calibration data" % predicted_total_mls)
#         total_volume = predicted_total_mls
#     q = input(
#         "Are ~%d ml available? \nZero the scale and press ENTER; q to exit"
#         % round(total_volume)
#     )
#     if q == "":
#         for i in range(n_repetitions):
#             p.move(n_rotations)
#             print("%d/%d" % (i + 1, n_repetitions), end="\t\r")
#             while p.is_pumping():
#                 time.sleep(0.1)
#             time.sleep(1)
#         ml = float(input("How many mls?"))
#         ml = ml / n_repetitions
#         device.calibration_pump_rotations_to_ml[pump_number][n_rotations] = round(ml, 3)
#         device.save()


def pump_calibration_function(x, a, b, c):
    """
    converts pumped volume (x) to motor rotations(y)
    """
    y = a * x + b * x * math.exp(-c * x)
    return y


class Pump(Stepper):
    def __init__(self, device, cs):
        super().__init__(device=device, cs=cs)

        self.device = device
        self.cs = cs
        self.pump_number = cs + 1
        # self.calibration_function = None

    # @property
    # def coefs(self):
    #     return self.device.calibration_coefs_pumps[self.pump_number]

    # @coefs.setter
    # def coefs(self, value):
    #     self.device.calibration_coefs_pumps[self.pump_number] = list(value)
    #     try:
    #         self.device.save()
    #     except Exception:
    #         pass

    # def calibration_function(self, mL):
    #     if len(self.coefs) < 3:
    #         return None
    #     else:
    #         a, b, c = self.coefs
    #         return pump_calibration_function(mL, a, b, c)

    def show_parameters(self):
        print("pump_number %d stock volume:" % self.pump_number, self.stock_volume)
        print(
            "pump_number %d stock concentration:" % self.pump_number,
            self.stock_concentration,
        )
        # self.calibration_curve()
        # plt.show()

    @property
    def stock_concentration(self):
        return self.device.pump_stock_concentrations[self.pump_number]

    @stock_concentration.setter
    def stock_concentration(self, value):
        value = float(value)
        self.device.pump_stock_concentrations[self.pump_number] = value
        self.device.save()

    @property
    def stock_volume(self):
        return self.device.pump_stock_volumes[self.pump_number]

    @stock_volume.setter
    def stock_volume(self, value):
        value = float(value)
        self.device.pump_stock_volumes[self.pump_number] = value
        self.device.save()

    def calculate_rotations(self, volume):
        # Get the coefficients for the given pumpId
        coefficients = self.device.device_data['pumps']['calibration'][self.pump_number]
        # Convert the coefficients into a list of (rotations, coefficient) pairs and sort
        points = sorted([(int(rot), coef) for rot, coef in coefficients.items()])

        # If volume is larger than the largest known, use the largest coefficient
        if volume >= points[-1][0] * points[-1][1]:
            return volume / points[-1][1]

        # Find the two points surrounding the given volume
        lower_point = points[0]
        upper_point = points[-1]
        for i in range(len(points) - 1):
            if volume >= points[i][0] * points[i][1] and volume <= points[i + 1][0] * points[i + 1][1]:
                lower_point = points[i]
                upper_point = points[i + 1]
                break

        # Calculate the interpolation factor
        lower_volume = lower_point[0] * lower_point[1]
        upper_volume = upper_point[0] * upper_point[1]
        factor = (volume - lower_volume) / (upper_volume - lower_volume)

        # Interpolate the coefficient
        interpolated_coefficient = lower_point[1] + (upper_point[1] - lower_point[1]) * factor

        # Calculate the rotations
        rotations = volume / interpolated_coefficient

        return rotations

    def calculate_volume(self, rotations):
        coefficients = self.device.device_data['pumps']['calibration'][self.pump_number]

        if rotations <= min(coefficients.keys()):
            correction_coefficient = coefficients[min(coefficients.keys())]
        else:
            for i in range(len(coefficients) - 1):
                if list(coefficients.keys())[i] <= rotations < list(coefficients.keys())[i + 1]:
                    correction_coefficient = coefficients[list(coefficients.keys())[i]] + \
                                             (rotations - list(coefficients.keys())[i]) * \
                                             (coefficients[list(coefficients.keys())[i + 1]] - coefficients[
                                                 list(coefficients.keys())[i]]) / \
                                             (list(coefficients.keys())[i + 1] - list(coefficients.keys())[i])
                    break
            else:
                correction_coefficient = coefficients[max(coefficients.keys())]
        volume = rotations * correction_coefficient
        return round(volume, 2)

    def pump(self, volume, rot_per_sec=None):
        rotations = self.calculate_rotations(abs(volume))
        if volume < 0:
            rotations *= -1
        if volume != 0:
            if rot_per_sec is None:
                rot_per_sec = self.max_speed_rps
            self.move(n_rotations=rotations, rot_per_sec=rot_per_sec)

    def get_pumped_volume(self):
        microsteps = self.get_abs_position()
        n_rotations = microsteps / 25600
        vol = self.calculate_volume(n_rotations)
        return vol

    # def add_calibration_point(self, rotations, volume):
    #     temp = self.calibration_rotations_to_ml
    #     temp[rotations] = volume
    #     self.calibration_rotations_to_ml = temp

    # def calibrate(self, rotations_to_ml=None, dummy_data=False):
    #     self.device.save()
    #     self.calibration_rotations_to_ml = rotations_to_ml
    #     if rotations_to_ml is None and dummy_data:
    #         self.calibration_rotations_to_ml = {
    #             1: 0.145,
    #             5: 0.563,
    #             10: 1.012,
    #             20: 2.14,
    #             50: 5.14,
    #             100: 9.21,
    #         }

    # def fit_calibration_function(self):
    #     calibration_n_rotations = sorted(list(self.calibration_rotations_to_ml.keys()))
    #     calibration_volumes = sorted(list(self.calibration_rotations_to_ml.values()))
    #     if calibration_n_rotations is not None:
    #         if len(calibration_n_rotations) >= 4:
    #             coefs, _ = scipy.optimize.curve_fit(
    #                 pump_calibration_function,
    #                 calibration_volumes,
    #                 calibration_n_rotations,
    #                 p0=(10, -10, 1),
    #                 bounds=[(-50, -50, 0.1), (50, 50, 1)],
    #                 sigma=np.array(calibration_volumes) * 0.1,
    #             )
    #             self.coefs = coefs
    #             a, b, c = self.coefs
    #             return a, b, c

    # def calibration_curve(self):
    #     calibration_n_rotations = sorted(list(self.calibration_rotations_to_ml.keys()))
    #     calibration_volumes = sorted(list(self.calibration_rotations_to_ml.values()))
    #     if len(calibration_n_rotations) < 4:
    #         print(
    #             "PUMP %d: NOT ENOUGH CALIBRATION POINTS (%d/4)"
    #             % (self.pump_number, len(calibration_n_rotations))
    #         )
    #     else:
    #         a, b, c = self.fit_calibration_function()
    #         plt.figure(figsize=[6, 4], dpi=100)
    #         x = np.linspace(0, 20, 101)
    #         y = [self.calibration_function(vol) for vol in x]
    #         plt.plot(calibration_volumes, calibration_n_rotations, "bs")
    #         plt.plot(x, y, "k:")
    #         plt.xlabel("pumped volume [mL]")
    #         plt.ylabel("motor rotations")
    #         plt.title(
    #             "Pump %d calibration\n a (slope): %.3f    b: %.3f    c: %.3f"
    #             % (self.pump_number, a, b, c)
    #         )
            # plt.show()

    # def check(self):
    #     # test_failed = False
    #     driver = bcolors.WARNING + "driver, " + bcolors.ENDC
    #     calibration = bcolors.WARNING + "calibration, " + bcolors.ENDC
    #     volume = bcolors.WARNING + "volume, " % self.stock_volume + bcolors.ENDC
    #     concentration = bcolors.WARNING + "concentration" + bcolors.ENDC
    #     if not self.driver_is_responsive():
    #         driver = bcolors.FAIL + "driver not responsive" + bcolors.ENDC
    #         # test_failed = True
    #         print("Pump %d:" % self.pump_number, driver)
    #         return
    #
    #     else:
    #         driver = bcolors.OKGREEN + "driver OK," + bcolors.ENDC
    #         if len(self.coefs) == 0 or pd.isnull(self.calibration_function(1)):
    #             calibration = bcolors.FAIL + "not calibrated," + bcolors.ENDC
    #         else:
    #             calibration = bcolors.OKGREEN + "calibration OK," + bcolors.ENDC
    #             # test_failed = True
    #
    #         if pd.isnull(self.stock_volume):
    #             volume = bcolors.FAIL + "volume unknown," + bcolors.ENDC
    #             # test_failed = True
    #         else:
    #             volume = bcolors.OKGREEN + "%d ml," % self.stock_volume + bcolors.ENDC
    #
    #         if not pd.isnull(self.stock_concentration):
    #             concentration = (
    #                 bcolors.OKGREEN
    #                 + "concentration: %.2f" % self.stock_concentration
    #                 + bcolors.ENDC
    #             )
    #             # test_failed = True
    #         else:
    #             concentration = bcolors.FAIL + "concentration unknown" + bcolors.ENDC
    #
    #     # if not test_failed:
    #     #     print("Pump %d " % self.pump_number + bcolors.OKGREEN + "OK" + bcolors.ENDC)

        # print(
        #     "Pump %d:" % self.pump_number,
        #     driver,
        #     calibration,
        #     volume,
        #     concentration,
        # )
