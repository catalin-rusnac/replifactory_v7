import math
import time

def split_bytes(value, n_bits, n_bytes):
    assert 0 <= value <= 1
    value = int(value * (2**n_bits - 1))
    value = max(1, value)
    assert value < 2**n_bits

    bytes_list = [0b00] * n_bytes
    for i in range(n_bytes):
        lsb = value & ((1 << 8) - 1)
        value = value >> 8
        bytes_list[i] = lsb
    bytes_list = bytes_list[::-1]
    return bytes_list


class Stepper:
    REGISTER_ABS_POS = 0x01  # Current position, 22 bits
    REGISTER_EL_POS = 0x02  # Electrical position, 9 bits
    REGISTER_MARK = 0x03  # Mark position, 22 bits
    REGISTER_SPEED = 0x04  # Current speed, 20 bits
    REGISTER_ACC = 0x05  # Acceleration, 12 bits
    REGISTER_DEC = 0x06  # Deceleration, 12 bits
    REGISTER_MAX_SPEED = 0x07  # Maximum speed, 10 bits
    REGISTER_MIN_SPEED = 0x08  # Minimum speed, 13 bits
    REGISTER_FS_SPD = 0x15  # Full-step speed, 10 bits
    REGISTER_KVAL_HOLD = 0x09  # Holding KVAL, 8 bits
    REGISTER_KVAL_RUN = 0x0A  # Constant speed KVAL, 8 bits
    REGISTER_KVAL_ACC = 0x0B  # Acceleration starting KVAL, 8 bits
    REGISTER_KVAL_DEC = 0x0C  # Deceleration starting KVAL, 8 bits
    REGISTER_INT_SPEED = 0x0D  # Intersect speed, 14 bits
    REGISTER_ST_SLP = 0x0E  # Start slope, 8 bits
    REGISTER_FN_SLP_ACC = 0x0F  # Acceleration final slope, 8 bits
    REGISTER_FN_SLP_DEC = 0x10  # Deceleration final slope, 8 bits
    REGISTER_K_THERM = 0x11  # Thermal compensation factor, 4 bits
    REGISTER_ADC_OUT = 0x12  # ADC output, 5 bits
    REGISTER_OCD_TH = 0x13  # OCD threshold, 4 bits
    REGISTER_STALL_TH = 0x14  # STALL threshold, 7 bits
    REGISTER_STEP_MODE = 0x16  # Step mode, 8 bits
    REGISTER_ALARM_EN = 0x17  # Alarm enable, 8 bits
    REGISTER_CONFIG = 0x18  # IC configuration, 16 bits
    REGISTER_STATUS = 0x19  # Status, 16 bits

    COMMAND_RESET_DEVICE = 0b11000000  # Device is reset to power-up conditions
    COMMAND_SOFT_STOP = 0b10110000  # Stops motor with a deceleration phase
    COMMAND_HARD_STOP = 0b10111000  # Stops motor immediately
    COMMAND_SOFT_HIZ = 0b10100000  # Puts the bridges into high impedance status after a deceleration phase
    COMMAND_HARD_HIZ = 0b10101000  # Puts the bridges into high impedance status immediately
    COMMAND_GET_STATUS = 0b11010000  # Returns the STATUS register value

    min_speed_rps = 0.01
    max_speed_rps = 4
    acceleration = 0.01
    deceleration = 0.01
    full_step_speed = 0.1
    stall_threshold = 0.5
    _kval_hold = 0
    _kval_run = 0.8
    _kval_acc = 0.57
    _kval_dec = 0.3

    def __init__(self, device, cs):
        self.device = device
        self.cs = cs
        self.port = None
        self.step_mode = None

    def reset_device(self):
        self.port.write([self.COMMAND_RESET_DEVICE])

    def soft_stop(self):
        self.port.write([self.COMMAND_SOFT_STOP])

    def hard_stop(self):
        self.port.write([self.COMMAND_HARD_STOP])

    def soft_hiz(self):
        self.port.write([self.COMMAND_SOFT_HIZ])

    def hard_hiz(self):
        self.port.write([self.COMMAND_HARD_HIZ])

    def get_status_command(self):
        self.port.write([self.COMMAND_GET_STATUS])
        # Assuming the status needs to be read back
        status = self.port.read(2)
        return status

    @property
    def kval_hold(self):
        return self._kval_hold

    @kval_hold.setter
    def kval_hold(self, value):
        assert 0 <= value <= 1
        self.write_register(self.REGISTER_KVAL_HOLD, value=value, n_bits=7, n_bytes=1)
        self._kval_hold = value

    @property
    def kval_acc(self):
        return self._kval_acc

    @kval_acc.setter
    def kval_acc(self, value):
        assert 0 <= value <= 1
        self.write_register(self.REGISTER_KVAL_ACC, value=value, n_bits=7, n_bytes=1)
        self._kval_acc = value

    @property
    def kval_dec(self):
        return self._kval_dec

    @kval_dec.setter
    def kval_dec(self, value):
        assert 0 <= value <= 1
        self.write_register(self.REGISTER_KVAL_DEC, value=value, n_bits=7, n_bytes=1)
        self._kval_dec = value

    @property
    def kval_run(self):
        return self._kval_run

    @kval_run.setter
    def kval_run(self, value):
        assert 0 <= value <= 1
        self.write_register(self.REGISTER_KVAL_RUN, value=value, n_bits=7, n_bytes=1)
        self._kval_run = value

    def set_stall_threshold_ma(self, current_ma):
        """
        set the stall threshold in mA
        """
        # 0000000 is 31.25 mA and 1111111 is 4000 mA
        value = current_ma / 4000
        assert 0 <= value <= 1
        self.stall_threshold = value
        self.write_register(self.REGISTER_STALL_TH, value=self.stall_threshold, n_bits=7, n_bytes=1)

    def detect_stall(self, verbose=False):
        status_register = self.read_register(self.REGISTER_STATUS, n_bytes=2)
        status_byte_high = status_register[0]  # First byte for bits 8-15

        step_loss_a = not (status_byte_high >> 5) & 0b1  # Bit 13
        step_loss_b = not (status_byte_high >> 6) & 0b1  # Bit 14
        if verbose:
            if step_loss_a:
                print("Stall detected on bridge A")
            elif step_loss_b:
                print("Stall detected on bridge B")
            else:
                print("No stall detected")
        return step_loss_a or step_loss_b

    def print_register_meanings(self):
        status_register = self.read_register(self.REGISTER_STATUS, n_bytes=2)
        status_byte_high = status_register[0]  # First byte for bits 8-15
        status_byte_low = status_register[1]  # Second byte for bits 0-7

        meanings = {
            0: ("HiZ", "True" if (status_byte_low >> 0) & 0b1 else "False"),
            1: ("BUSY", "True" if (status_byte_low >> 1) & 0b1 else "False"),
            2: ("SW_F", "Closed" if (status_byte_low >> 2) & 0b1 else "Open"),
            3: ("SW_EVN", "True" if (status_byte_low >> 3) & 0b1 else "False"),
            4: ("DIR", "Clockwise" if (status_byte_low >> 4) & 0b1 else "Counter-clockwise"),
            5: ("MOT_STATUS", "Active" if (status_byte_low >> 5) & 0b1 else "Inactive"),
            6: ("NOTPERF_CMD", "True" if (status_byte_low >> 6) & 0b1 else "False"),
            7: ("WRONG_CMD", "True" if (status_byte_low >> 7) & 0b1 else "False"),
            8: ("UVLO", "False" if (status_byte_high >> 0) & 0b1 else "True"),
            9: ("TH_WRN", "False" if (status_byte_high >> 1) & 0b1 else "True"),
            10: ("TH_SD", "False" if (status_byte_high >> 2) & 0b1 else "True"),
            11: ("OCD", "False" if (status_byte_high >> 3) & 0b1 else "True"),
            12: ("STEP_LOSS_A", "False" if (status_byte_high >> 5) & 0b1 else "True"),
            13: ("STEP_LOSS_B", "False" if (status_byte_high >> 6) & 0b1 else "True"),
            14: ("SCK_MOD", "True" if (status_byte_high >> 7) & 0b1 else "False"),
        }

        print("STATUS REGISTER MEANINGS:")
        print("-" * 30)

        for bit in range(16):
            if bit in meanings:
                bit_name, bit_value = meanings[bit]
                print(f"{bit_name}: {bit_value}")

        print("-" * 30)

    def reset_speeds(self):
        self.write_register(
            self.REGISTER_FS_SPD, value=self.full_step_speed, n_bits=10, n_bytes=2
        )  # k value const
        self.write_register(
            self.REGISTER_STALL_TH, value=self.stall_threshold, n_bits=6, n_bytes=1
        )

        self.kval_hold = self._kval_hold
        self.kval_acc = self._kval_acc
        self.kval_run = self._kval_run
        # self.write_register(self.REGISTER_KVAL_HOLD, value=self.kval_hold, n_bits=7, n_bytes=1)
        # self.write_register(self.REGISTER_KVAL_RUN, value=self.kval_run, n_bits=7, n_bytes=1)
        # self.write_register(self.REGISTER_KVAL_ACC, value=self.kval_acc, n_bits=7, n_bytes=1)

        self.set_min_speed(rot_per_sec=self.min_speed_rps)
        self.set_max_speed(rot_per_sec=self.max_speed_rps)
        self.set_acceleration(value=self.acceleration)
        self.set_deceleration(value=self.deceleration)


    def connect(self):
        self.port = self.device.spi.get_port(cs=self.cs, freq=1e4, mode=3)
        self.port.set_mode(3)
        self.reset_speeds()

    def set_acceleration(self, value=1e-4):
        self.write_register(self.REGISTER_ACC, value=value, n_bits=12, n_bytes=2)

    def set_deceleration(self, value=1e-3):
        self.write_register(self.REGISTER_DEC, value=value, n_bits=12, n_bytes=2)

    def set_min_speed(self, rot_per_sec=0.1):
        # steps_per_sec = integer * 2**-24/250e-9   # page 43 in L6470H datasheet
        correction_factor = 1.322
        rot_per_sec = rot_per_sec * correction_factor
        steps_per_sec = rot_per_sec * 2**22 / 25600
        integer = steps_per_sec * 250e-9 / 2**-24
        self.write_register(self.REGISTER_MIN_SPEED, value=integer / 2**12, n_bits=12, n_bytes=2)

    def set_max_speed(self, rot_per_sec=4.0):
        correction_factor = 1.322
        rot_per_sec = rot_per_sec * correction_factor
        steps_per_sec = rot_per_sec * 2**22 / 25600  # page 43 in L6470H datasheet
        integer = steps_per_sec * 250e-9 / 2**-18
        self.write_register(self.REGISTER_MAX_SPEED, value=integer / 2**10, n_bits=10, n_bytes=2)

    def write_register(self, reg, value, n_bits, n_bytes):
        lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
        if not lock_acquired:
            raise Exception("Could not acquire lock for writing stepper %d register %s" % (self.cs, reg))
        try:
            set_param = reg | 0b00000000
            self.port.write([set_param])  # do not use write_to_port here - lock is already acquired
            bytes_to_write = split_bytes(value, n_bits, n_bytes)
            # print("Writing to register %s: %s" % (reg, bytes_to_write))
            for b in bytes_to_write:
                self.port.write([b])
                time.sleep(0.001)
        finally:
            self.device.lock_ftdi.release()
        bytes_read = self.read_register(reg=reg, n_bytes=n_bytes)
        if not [bytes_to_write[i] == bytes_read[i] for i in range(n_bytes)]:
            print("WARNING: register %s not set correctly" % reg)

    def read_register(self, reg, n_bytes=3):
        lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
        if not lock_acquired:
            raise Exception("Could not acquire lock for reading stepper %d register %s" % (self.cs, reg))
        try:
            get_param = reg | 0b00100000
            self.port.write([get_param])
            res = []
            for b in range(n_bytes):
                res += self.port.read(1)
        finally:
            self.device.lock_ftdi.release()
        return res

    def move(self, n_rotations=1, rot_per_sec=None):
        """
        move the given number of rotations
        By default uses 1/128 microstepping to minimize noise and vibration.
        If number of required microsteps can not fit in the register (> 2^22),
        the step mode is decreased to 1/64 or lower.
        """
        # if n_rotations <= 1:
        #     self.set_max_speed(rot_per_sec=0.1)
        # else:
        #     self.set_max_speed(rot_per_sec=self.max_speed_rps)

        if rot_per_sec is None:
            rot_per_sec = self.max_speed_rps
        self.set_max_speed(rot_per_sec=rot_per_sec)

        if self.step_mode != 7:
            self.set_step_mode(7)
        assert not self.is_pumping(), "Pump %d is already running." % (self.cs + 1)
        if n_rotations >= 0:
            direction_bit = 0b1
        else:
            direction_bit = 0b0

        move_header_byte = 0b01000000 | direction_bit
        max_n_microsteps = 2**22 - 1  # 22 bit

        steps_per_rotation = 200
        microsteps_per_step = 2**self.step_mode
        n_microsteps = abs(n_rotations) * steps_per_rotation * microsteps_per_step

        if n_microsteps > max_n_microsteps:
            required_step_mode = (
                self.step_mode - 1 - int(math.log2(n_microsteps / max_n_microsteps))
            )
            self.set_step_mode(required_step_mode)
            microsteps_per_step = 2**self.step_mode
            n_microsteps = abs(n_rotations) * steps_per_rotation * microsteps_per_step

        write_bytes = split_bytes(n_microsteps / max_n_microsteps, 22, 3)
        lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
        if not lock_acquired:
            raise Exception("Could not acquire lock for moving stepper %d at time %s" % (self.cs, time.ctime()))
        try:
            self.port.write([move_header_byte])
            for b in write_bytes:
                self.port.write([b])
        finally:
            self.device.lock_ftdi.release()

    def get_abs_position(self):
        microsteps = int.from_bytes(self.read_register(self.REGISTER_ABS_POS), "big")
        return microsteps

    def run(self, speed=0.001):
        """
        run indefinitely at constant speed
        """
        if self.step_mode != 7:
            self.set_step_mode(7)

        if speed >= 0:
            direction_bit = 0b1
        else:
            direction_bit = 0b0
        speed = abs(speed)
        # steps_per_sec = speed*2e-28/250e-9
        run_header_byte = 0b01010000 | direction_bit
        write_bytes = split_bytes(speed, 20, 3)
        lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
        if not lock_acquired:
            raise Exception("Could not acquire lock for running stepper %d at time %s" % (self.cs, time.ctime()))
        try:
            self.port.write([run_header_byte])
            for b in write_bytes:
                self.port.write([b])
        finally:
            self.device.lock_ftdi.release()

    def is_busy(self):
        lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
        if not lock_acquired:
            raise Exception("Could not acquire lock for checking busy status of stepper %d at time %s" % (self.cs, time.ctime()))
        try:
            self.port.write([0b11010000])
        finally:
            self.device.lock_ftdi.release()
        msb, lsb = self.read_register(self.REGISTER_STATUS, n_bytes=2)
        busy = not (lsb >> 1 & 0b1)
        return busy

    def driver_is_responsive(self):
        if self.port is None:
            return False
        lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
        if not lock_acquired:
            raise Exception("Could not acquire lock for checking driver responsiveness of stepper %d" % self.cs)
        try:
            self.port.write([0x19])  # GetStatus command, resets warning flags
        except Exception:
            return False
        finally:
            self.device.lock_ftdi.release()

        msb, lsb = self.read_register(self.REGISTER_STATUS, n_bytes=2)
        return not (msb == 255 and lsb == 255)

    def write_to_port(self, data):
        lock_acquired = self.device.lock_ftdi.acquire(timeout=15)
        if not lock_acquired:
            raise Exception("Could not acquire lock for writing to stepper %d" % self.cs)
        try:
            self.port.write(data)
        finally:
            self.device.lock_ftdi.release()

    def is_pumping(self):
        if not self.driver_is_responsive():
            return False
        self.write_to_port([0b11010000])  # GetStatus command, resets warning flags
        msb, lsb = self.read_register(self.REGISTER_STATUS, n_bytes=2)
        status = lsb >> 5 & 0b11
        return status > 0

    def is_hiz(self):
        msb, lsb = self.read_register(self.REGISTER_STATUS, n_bytes=2)
        hiz = bool(lsb & 0b1)
        return hiz

    def stop(self):
        """
        decelerate with programmed deceleration value until the MIN_SPEED value
        is reached and then stop the motor
        """
        # self.port.write([0b10110000])
        self.write_to_port([0b10110000])

    def stop_hard(self):
        """
        stop the motor instantly, ignoring deceleration constraints
        """
        self.write_to_port([0b10111000])
        # self.port.write([0b10111000])

    def reset(self):
        # self.port.write([0b11000000])
        self.write_to_port([0b11000000])
        self.__init__(device=self.device, cs=self.cs)

    def set_step_mode(self, mode=7):
        """
        See page 48 in L6470H datasheet

        0: Full-step
        1: Half-step
        2: 1/4 microstep
        3: 1/8 microstep
        4: 1/16 microstep
        5: 1/32 microstep
        6: 1/64 microstep
        7: 1/128 microstep
        """
        assert mode in [0, 1, 2, 3, 4, 5, 6, 7]
        assert not self.is_pumping(), "can't set step mode while pumping"
        self.hard_hiz()
        # self.port.write([self.REGISTER_STEP_MODE])
        # self.port.write([mode])
        self.write_to_port([self.REGISTER_STEP_MODE])
        self.write_to_port([mode])
        read_mode = self.read_register(self.REGISTER_STEP_MODE)[0]
        if mode != read_mode:
            print("WARNING: step mode not set correctly")
            self.reset()
        self.step_mode = mode

    def get_status(self, verbose=False, reset=False):
        msb, lsb = self.read_register(self.REGISTER_STATUS, n_bytes=2)

        bits = [msb >> i & 1 for i in range(8)[::-1]]
        names = [
            "SCK_MOD",
            "STEP_LOSS_B",
            "STEP_LOSS_A",
            "OCD",
            "TH_SD",
            "TH_WRN",
            "UVLO",
            "WRONG_CMD",
        ]
        byte2 = dict(zip(names, bits))

        bits = [lsb >> i & 1 for i in range(8)[::-1]]
        names = [
            "NOTPERF_CMD",
            "MOT_STATUS1",
            "MOT_STATUS2",
            "DIR",
            "SW_EVN",
            "SW_F",
            "BUSY",
            "HiZ",
        ]
        byte1 = dict(zip(names, bits))

        # status = {0b00: "stopped",
        #           0b01: "accelerating",
        #           0b10: "decelerating",
        #           0b11: "moving at constant speed"}
        # motor_status_string = status[lsb >> 5 & 0b11]

        status_dict = {
            (False, False): "stopped",
            (False, True): "accelerating",
            (True, False): "decelerating",
            (True, True): "constant speed",
        }

        byte1["NOTPERF_CMD"] = bool(byte1["NOTPERF_CMD"])
        byte1["MOT_STATUS1"] = bool(byte1["MOT_STATUS1"])
        byte1["MOT_STATUS2"] = bool(byte1["MOT_STATUS2"])
        byte1["MOT_STATUS"] = status_dict[(byte1["MOT_STATUS1"], byte1["MOT_STATUS2"])]
        del byte1["MOT_STATUS1"]
        del byte1["MOT_STATUS2"]

        byte1["DIR"] = {1: "forward", 0: "reverse"}[byte1["DIR"]]
        byte1["SW_EVN"] = bool(byte1["SW_EVN"])
        byte1["SW_F"] = bool(byte1["SW_F"])
        byte1["BUSY"] = not bool(byte1["BUSY"])
        byte1["HiZ"] = bool(byte1["HiZ"])

        byte2["SCK_MOD"] = bool(byte2["SCK_MOD"])
        byte2["STEP_LOSS_B"] = not bool(byte2["STEP_LOSS_B"])
        byte2["STEP_LOSS_A"] = not bool(byte2["STEP_LOSS_A"])
        byte2["OCD"] = not bool(byte2["OCD"])
        byte2["TH_SD"] = not bool(byte2["TH_SD"])
        byte2["TH_WRN"] = not bool(byte2["TH_WRN"])
        byte2["UVLO"] = not bool(byte2["UVLO"])
        byte2["WRONG_CMD"] = bool(byte2["WRONG_CMD"])

        description = {
            "HiZ": "High Impedance",
            "BUSY": "Busy",
            # "SW_F": "external switch status",
            # "SW_EVN": "external switch turn-on event was detected",
            "DIR": "Direction ",
            "MOT_STATUS": "Motor status",
            "NOTPERF_CMD": "Command received by SPI cannot be performed",
            "WRONG_CMD": "Command received by SPI does not exist",
            "UVLO": "Undervoltage Lockout (8.2 ± 0.7V)",
            "TH_WRN": "Thermal warning (130°C)",
            "TH_SD": "Thermal shutdown (160°C)",
            "OCD": "Overcurrent detection",
            "STEP_LOSS_A": "Stall is detected on bridge A",
            "STEP_LOSS_B": "Stall is detected on bridge B",
            "SCK_MOD": "Working in Step-clock mode",
        }


        s = {}
        s.update({"CS": self.cs})
        s.update(byte1)
        s.update(byte2)
        if reset:
            # self.port.write([0b11010000])
            self.write_to_port([0b11010000])
        if verbose:
            text = ""
            for k in list(description.keys()):
                v = description[k]
                if s[k] is False:
                    color = bcolors.OKGREEN
                elif s[k] is True:
                    color = bcolors.FAIL
                else:
                    color = bcolors.OKBLUE
                text += color + "%s: %s" % (v, s[k]) + bcolors.ENDC + "\n"
            return text
        else:
            return s

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
