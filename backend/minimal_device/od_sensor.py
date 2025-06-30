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
    try:
        # Validate inputs for NaN, infinity, or invalid values
        if not np.isfinite(sig) or not np.isfinite(blank) or not np.isfinite(scaling):
            logger.error(f"Invalid input values: sig={sig}, blank={blank}, scaling={scaling}")
            return 0.0
        
        # Check for division by zero or negative/zero values in log
        if blank <= 0:
            logger.error(f"Invalid blank signal {blank} (must be positive)")
            return 0.0
            
        if sig <= 0:
            logger.warning(f"Invalid signal {sig} (must be positive), returning 0 OD")
            return 0.0
            
        if scaling <= 0:
            logger.error(f"Invalid scaling factor {scaling} (must be positive)")
            return 0.0
            
        ratio = sig / blank
        if ratio <= 0:
            logger.warning(f"Invalid signal/blank ratio {ratio} (must be positive), returning 0 OD")
            return 0.0
            
        result = -np.log10(ratio) * scaling
        
        # Validate the result
        if not np.isfinite(result):
            logger.error(f"BeerLambertScaled produced invalid result: {result} from sig={sig}, blank={blank}, scaling={scaling}")
            return 0.0
            
        return float(result)
    except Exception as e:
        logger.error(f"Exception in BeerLambertScaled: {e} - sig={sig}, blank={blank}, scaling={scaling}")
        return 0.0

def BeerLambertScaledInverse(od, blank, scaling):
    """convert optical density to signal using Beer-Lambert law and scaling factor"""
    try:
        # Convert inputs to numpy arrays for consistent handling
        od = np.asarray(od)
        blank = np.asarray(blank)
        scaling = np.asarray(scaling)
        
        # Validate inputs for NaN, infinity, or invalid values
        if not np.all(np.isfinite(od)) or not np.all(np.isfinite(blank)) or not np.all(np.isfinite(scaling)):
            logger.error(f"Invalid input values: od={od}, blank={blank}, scaling={scaling}")
            return np.zeros_like(od) if od.shape else 0.0
            
        if np.any(blank <= 0):
            logger.error(f"Invalid blank signal {blank} (must be positive)")
            return np.zeros_like(od) if od.shape else 0.0
            
        if np.any(scaling <= 0):
            logger.error(f"Invalid scaling factor {scaling} (must be positive)")
            return np.zeros_like(od) if od.shape else 0.0
            
        result = blank * 10**(-od / scaling)
        
        # Validate the result
        if not np.all(np.isfinite(result)):
            logger.error(f"BeerLambertScaledInverse produced invalid result: {result} from od={od}, blank={blank}, scaling={scaling}")
            return np.zeros_like(od) if od.shape else 0.0
            
        # Return scalar if input was scalar, array if input was array
        if result.shape == ():
            return float(result)
        else:
            return result.astype(float)
            
    except Exception as e:
        logger.error(f"Exception in BeerLambertScaledInverse: {e} - od={od}, blank={blank}, scaling={scaling}")
        od = np.asarray(od)
        return np.zeros_like(od) if od.shape else 0.0


class OdSensor:
    def __init__(self, device, vial_number):
        self.device = device
        self.vial_number = vial_number

    def mv_to_od(self, mv):
        # Validate input
        if not np.isfinite(mv):
            logger.error(f"Invalid mv value {mv} for vial {self.vial_number}")
            return 0.0
            
        coefs = self.device.device_data['ods']['calibration_coefs'][self.vial_number]
        if len(coefs) > 3:
            self.fit_calibration_function()
            print("fit calibration function with beer-lambert scaled because there were too many calibration coefficients")
            coefs = self.device.device_data['ods']['calibration_coefs'][self.vial_number]
            
        # Validate coefficients
        if len(coefs) < 2:
            logger.error(f"Insufficient calibration coefficients for vial {self.vial_number}: {coefs}")
            return 0.0
            
        blank_signal, scaling = coefs
        
        # Validate coefficients for NaN/infinity
        if not np.isfinite(blank_signal) or not np.isfinite(scaling):
            logger.error(f"Invalid calibration coefficients for vial {self.vial_number}: blank={blank_signal}, scaling={scaling}")
            return 0.0
            
        # if the minimum value in calibration is equal to 0 or 0.0, use it as blank
        try:
            calibration_keys = list(self.device.device_data['ods']['calibration'][self.vial_number].keys())
            if calibration_keys:  # Check if there are any calibration points
                lowest_od_in_calibration = min(calibration_keys)
                if float(lowest_od_in_calibration) == 0.0:
                    blank_from_calibration = self.device.device_data['ods']['calibration'][self.vial_number][lowest_od_in_calibration]
                    if np.isfinite(blank_from_calibration):
                        blank_signal = blank_from_calibration
            else:
                logger.info(f"No calibration data available for vial {self.vial_number} yet")
        except (ValueError, KeyError) as e:
            logger.warning(f"Could not check for OD=0 calibration point for vial {self.vial_number}: {e}")
            
        result = BeerLambertScaled(mv, blank_signal, scaling)
        
        # Final validation of result
        if not np.isfinite(result):
            logger.error(f"mv_to_od produced invalid result {result} for vial {self.vial_number}")
            return 0.0
            
        return result

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
        
        # Handle problematic signal values that would cause NaN/inf in OD calculation
        if signal <= 0:
            logger.warning(f"Vial {self.vial_number}: Signal is {signal} (transmitted={transmitted}, background={background}). Setting to small positive value to avoid log(0).")
            signal = 0.001  # Small positive value to avoid log(0) = -inf
        
        # Validate signal is finite
        if not np.isfinite(signal):
            logger.error(f"Vial {self.vial_number}: Non-finite signal {signal}. Setting to 0.001.")
            signal = 0.001
            
        return signal

    def measure_od(self):
        signal = self.measure_signal()
        
        # Validate signal measurement
        if not np.isfinite(signal):
            logger.error(f"Invalid signal measurement {signal} for vial {self.vial_number}")
            signal = 0.0
            
        od = self.mv_to_od(signal)
        
        # Ensure od is a valid float
        try:
            od = float(od)
            if not np.isfinite(od):
                logger.error(f"Invalid OD calculation {od} for vial {self.vial_number}, using 0.0")
                od = 0.0
        except (ValueError, TypeError) as e:
            logger.error(f"Could not convert OD to float for vial {self.vial_number}: {e}, using 0.0")
            od = 0.0
            
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
        
        # Count valid calibration points
        num_points = len(calibration_od)
        logger.info(f"calibration_od: {calibration_od}")
        logger.info(f"calibration_mv: {calibration_mv}")
        logger.info(f"Number of calibration points for vial {self.vial_number}: {num_points}")

        try:
            blank_signal = calibration_mv[calibration_od == 0.0][0]
            blank_bounds = (blank_signal - 0.00001, blank_signal + 0.00001)
        except:
            logger.info(f"no 0.0 in calibration for vial {self.vial_number}, using default bounds")
            blank_signal = 40
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

        # Check if we have exactly 1 calibration point and a custom scaling factor
        if num_points == 1:
            # For 1 point, use custom scaling factor if available
            custom_scaling = None
            try:
                custom_scaling = self.device.device_data['ods']['default_scaling_factor'][self.vial_number]
                logger.info(f"Using custom scaling factor {custom_scaling} for vial {self.vial_number} with 1 calibration point")
            except (KeyError, TypeError):
                logger.info(f"No custom scaling factor found for vial {self.vial_number}, using default of 2.0")
                custom_scaling = 2.0
            
            # With 1 point, handle the blank signal calculation properly
            # If the single calibration point is OD=0, use its signal as blank
            if 0.0 in calibration_od:
                blank_from_calibration = calibration_mv[calibration_od == 0.0][0]
                logger.info(f"Using blank signal {blank_from_calibration} from OD=0 calibration point")
                coefs = [blank_from_calibration, custom_scaling]
            else:
                # If no OD=0 point, we can't determine blank reliably with just 1 point
                # Use the existing blank_signal estimate and warn
                logger.warning(f"Single calibration point for vial {self.vial_number} is not OD=0. Using estimated blank {blank_signal}")
                coefs = [blank_signal, custom_scaling]
        else:
            # For 2+ points, calculate scaling factor automatically using curve fitting
            logger.info(f"Fitting calibration curve for vial {self.vial_number} with {num_points} calibration points")
            
            try:
                # Validate calibration data before curve fitting
                if any(not np.isfinite(od) for od in calibration_od):
                    logger.error(f"Invalid OD values in calibration data for vial {self.vial_number}: {calibration_od}")
                    raise ValueError("Invalid OD values")
                    
                if any(not np.isfinite(mv) for mv in calibration_mv):
                    logger.error(f"Invalid mv values in calibration data for vial {self.vial_number}: {calibration_mv}")
                    raise ValueError("Invalid mv values")
                
                # coefficients for fitting beer lambert scaled are blank and scaling factor
                # blank bounds are 0.5-200, scaling factor bounds are 1-3
                # initial guess is 50mV for blank and 1.0 for scaling factor
                coefs, _ = curve_fit(
                    BeerLambertScaledInverse,
                    calibration_od,
                    calibration_mv,
                    maxfev=5000,
                    p0=(blank_signal, 1.0),
                    bounds=[(blank_bounds[0], 0.1), (blank_bounds[1], 5)],
                    sigma=calibration_mv_err,
                )
            except Exception as e:
                logger.error(f"Curve fitting failed for vial {self.vial_number}: {e}")
                # Use fallback coefficients
                coefs = [blank_signal, 2.0]  # Use the estimated blank and default scaling
                logger.warning(f"Using fallback coefficients for vial {self.vial_number}: {coefs}")
        
        # Validate coefficients before saving
        if any(not np.isfinite(c) for c in coefs):
            logger.error(f"Curve fitting produced invalid coefficients for vial {self.vial_number}: {coefs}")
            # Use fallback values
            blank_signal = 40.0  # Default blank signal
            scaling = 2.0  # Default scaling factor
            coefs = [blank_signal, scaling]
            logger.warning(f"Using fallback calibration coefficients for vial {self.vial_number}: {coefs}")
        else:
            coefs = [round(i, 4) for i in coefs]
            coefs = [float(i) for i in coefs]
            
        blank_signal, scaling = coefs
        
        # Final validation of coefficients
        if blank_signal <= 0 or scaling <= 0 or not np.isfinite(blank_signal) or not np.isfinite(scaling):
            logger.error(f"Invalid calibration coefficients for vial {self.vial_number}: blank={blank_signal}, scaling={scaling}")
            # Use safe fallback values
            blank_signal = 40.0
            scaling = 2.0
            coefs = [blank_signal, scaling]
            logger.warning(f"Using safe fallback calibration coefficients for vial {self.vial_number}: {coefs}")
            
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
        blank_signal, scaling = self.device.device_data['ods']['calibration_coefs'][self.vial_number]
        plt.plot(x, y, "b:", label="function fit")
        plt.title(
            "Beer-Lambert scaled: blank=%.2f mV, scaling=%.2f"
            % (blank_signal, scaling),
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
