
import threading
import time
import pyftdi.i2c


class RGBLedController:
    """Controller for RGB LEDs using PCA9685 on two I2C addresses."""

    def __init__(self, device, frequency=1000):
        """
        Initialize the RGB LED controller.
        :param device: Device object with an I2C interface
        :param frequency: PWM frequency (default: 50Hz)
        """
        self.device = device
        self.frequency = frequency
        self.lock = threading.Lock()

        # Ports for the two PCA9685 controllers
        self.port_rgb_pwm1 = None  # LEDs 1-5
        self.port_rgb_pwm2 = None  # LEDs 6-7

        if self.device.is_connected():
            self.connect()

    def connect(self):
        """Establish connections to the PCA9685 controllers and configure them."""
        try:
            # Connect to the first PCA9685 (LEDs 1-5)
            self.port_rgb_pwm1 = self.device.i2c.get_port(self.device.PORT_RGB_PWM1)
            self._initialize_pwm_controller(self.port_rgb_pwm1)

            # Connect to the second PCA9685 (LEDs 6-7)
            self.port_rgb_pwm2 = self.device.i2c.get_port(self.device.PORT_RGB_PWM2)
            self._initialize_pwm_controller(self.port_rgb_pwm2)

            print("Connected to both PCA9685 RGB controllers")
        except Exception as e:
            print("Error connecting to PCA9685 controllers:", e)

    def _initialize_pwm_controller(self, port):
        """Initialize a PCA9685 controller."""
        self._set_frequency(port, self.frequency)
        self._set_all_leds(port, 0, 0, 0)  # Turn off all LEDs initially

    def set_flicker_frequency(self, frequency):
        # min and max value from pca9685 datasheet: 24Hz to 1526Hz
        if frequency < 24 or frequency > 1526:
            raise ValueError("Frequency must be between 24 and 1526 Hz")
        """Set the PWM frequency for flickering effect."""
        self.frequency = frequency
        self._set_frequency(self.port_rgb_pwm1, frequency)
        self._set_frequency(self.port_rgb_pwm2, frequency)

    def _set_frequency(self, port, frequency):
        """Set the PWM frequency on a specific PCA9685 port."""
        pre_scale = round(25000000 / (4096 * frequency)) - 1
        with self.lock:
            port.write_to(0x00, [0x10])  # Enter sleep mode
            port.write_to(0xFE, [pre_scale])  # Set frequency
            port.write_to(0x00, [0x80])  # Restart in normal mode

    def set_led(self, led_number, red, green, blue):
        """
        Set the brightness of an RGB LED.
        :param led_number: LED index (starting from 1)
        :param red: Brightness for red (0-1)
        :param green: Brightness for green (0-1)
        :param blue: Brightness for blue (0-1)
        """
        assert 1 <= led_number <= 7
        assert 0 <= red <= 1 and 0 <= green <= 1 and 0 <= blue <= 1

        if 1 <= led_number <= 5:
            port = self.port_rgb_pwm1
            base_pin = (led_number - 1) * 3
        else:
            port = self.port_rgb_pwm2
            base_pin = (led_number - 6) * 3

        self._set_rgb_pwm(port, base_pin, red, green, blue)

    def _set_rgb_pwm(self, port, base_pin, red, green, blue):
        """Set the PWM values for an RGB LED."""
        self._set_pwm(port, base_pin + 1, red)
        self._set_pwm(port, base_pin + 2, green)
        self._set_pwm(port, base_pin, blue)

    def _set_pwm(self, port, pin, duty_cycle):
        """Set the PWM duty cycle for a specific pin on a given port."""
        msb, lsb = divmod(round(4095 * duty_cycle), 0x100)
        with self.lock:
            # port.write_to(0x06 + pin * 4, [0x00])  # ON low byte
            # port.write_to(0x07 + pin * 4, [0x00])  # ON high byte
            port.write_to(0x08 + pin * 4, [lsb])   # OFF low byte
            port.write_to(0x09 + pin * 4, [msb])   # OFF high byte

    def set_all_leds(self, red, green, blue):
        """
        Set all RGB LEDs to the same color.
        :param red: Brightness for red (0-1)
        :param green: Brightness for green (0-1)
        :param blue: Brightness for blue (0-1)
        """
        self._set_all_leds(self.port_rgb_pwm1, red, green, blue)  # LEDs 1-5
        self._set_all_leds(self.port_rgb_pwm2, red, green, blue)  # LEDs 6-7

    def _set_all_leds(self, port, red, green, blue):
        """Set all LEDs connected to a specific port to the same color."""
        for i in range(5 if port == self.port_rgb_pwm1 else 2):
            base_pin = i * 3
            self._set_rgb_pwm(port, base_pin, red, green, blue)

    def blink_hello(self):
        """Blink green LEDs."""
        self.set_all_leds(1, 0, 0) # red
        self.set_all_leds(0, 1, 0) # green
        self.set_all_leds(0, 0, 1) # blue
        self.set_all_leds(1, 1, 1) # white
        time.sleep(0.2)
        self.set_all_leds(0, 0, 0) # off
        time.sleep(0.2)

    def turn_off_all(self):
        """Turn off all LEDs."""
        self.set_all_leds(0, 0, 0)

# Usage example:
# device = BaseDevice()
# rgb_controller = RGBLedController(device)
# rgb_controller.set_led(1, 1, 0, 0)  # Set LED 1 to red
# rgb_controller.set_led(6, 0, 1, 0)  # Set LED 6 to green
# rgb_controller.set_all_leds(0, 0, 1)  # Set all LEDs to blue
