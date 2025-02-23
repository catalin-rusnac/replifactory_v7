import time


class Valves:
    VALVE_OPEN_TIME = 1.5
    VALVE_CLOSE_TIME = 1.5
    DUTY_CYCLE_OPEN = 0.03
    DUTY_CYCLE_CLOSED = 0.12
    led_numbers = {valve: valve + 7 for valve in [1, 2, 3, 4, 5, 6, 7, 8]}

    def __init__(self, device):
        self.device = device
        self.pwm_controller = device.pwm_controller
        self.is_open = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None}

    def connect(self):
        self.set_frequency_multiplier()
        for valve in range(1, 8):
            if self.device.device_data["valves"]["states"][valve] == "open":
                self.open(valve)
            elif self.device.device_data["valves"]["states"][valve] == "closed":
                self.close(valve)

    def set_frequency_multiplier(self, frequency_multiplier=None):
        if frequency_multiplier is None:
            if "frequency_multiplier" not in self.device.device_data:
                self.device.device_data["frequency_multiplier"] = 1
        else:
            self.device.device_data["frequency_multiplier"] = frequency_multiplier
        frequency = 50 * self.device.device_data["frequency_multiplier"]
        self.pwm_controller.set_frequency(frequency)
        self.device.eeprom.save_config_to_eeprom()

    def sync_is_open_to_pwm(self):
        # creates is_open dict from pwm controller
        for v in range(1, 8):
            status = self.get_is_open(v)
            if status == 1:
                self.is_open[v] = True
            elif status == 0:
                self.is_open[v] = False
            else:
                self.is_open[v] = None

    def sync_pwm_to_is_open(self):
        # sets pwm controller to is_open dict
        for v in range(1, 8):
            status = self.is_open[v]
            if status is True:
                self.open(v)
            elif status is False:
                self.close(v)
            else:
                self.open(v)

    def get_fully_open_valves(self):
        return [v for v in range(1, 8) if self.get_is_open(v) == 1]

    def get_fully_closed_valves(self):
        return [v for v in range(1, 8) if self.get_is_open(v) == 0]

    def get_is_open(self, valve_number):
        return self.get_percent_open_pwm(valve=valve_number)

    def all_closed(self):
        closed_valves = [self.device.device_data["valves"]["states"][i] == "closed" for i in range(1, 8)]
        return all(closed_valves)

    def not_all_closed(self):
        return not self.all_closed()

    def set_duty_cycle(self, valve, duty_cycle):
        """
        sets the duty cycle of the pwm signal for the valve.
        Stops pwm controller while changing value, to prevent the motor from
        moving after writing the first byte.
        """
        led_number = self.led_numbers[valve]
        if duty_cycle == self.DUTY_CYCLE_OPEN:
            timeout = 15
        else:
            timeout = 45
        lock_acquired = self.pwm_controller.lock.acquire(timeout=timeout)
        if not lock_acquired:
            raise Exception("Could not acquire lock to set duty cycle for valve %d at time %s" % (valve, time.ctime()))
        try:
            # self.pwm_controller.stop_all()
            self.pwm_controller.set_duty_cycle(
                led_number=led_number, duty_cycle=duty_cycle
            )
            # self.pwm_controller.start_all()
            time.sleep(0.04)
        finally:
            self.pwm_controller.lock.release()

    def open(self, valve):
        self.set_duty_cycle(valve=valve, duty_cycle=self.DUTY_CYCLE_OPEN)
        time.sleep(self.VALVE_OPEN_TIME)
        self.is_open[valve] = True
        self.device.device_data["valves"]['states'][valve] = "open"
        self.device.eeprom.save_config_to_eeprom()

    def get_percent_open_pwm(self, valve):
        if self.pwm_controller.is_sleeping():
            return -1
        led_number = self.led_numbers[valve]
        duty_cycle = self.pwm_controller.get_duty_cycle(led_number=led_number)
        duty_cycle = round(duty_cycle, 3)
        op, cl = self.DUTY_CYCLE_OPEN, self.DUTY_CYCLE_CLOSED
        percent_closed = (duty_cycle - op) / (cl - op)
        percent_open = 1 - percent_closed
        return percent_open

    def close(self, valve):
        open_valves = [v for v in range(1, 8) if self.is_open[v]]
        remaining_open_valves = [v for v in open_valves if v != valve]
        if len(remaining_open_valves) < 1:
            assert (not self.device.is_pumping()), "can't close last valve while pumping"
        self.set_duty_cycle(valve=valve, duty_cycle=self.DUTY_CYCLE_CLOSED)
        time.sleep(self.VALVE_CLOSE_TIME)
        self.is_open[valve] = False
        self.device.device_data["valves"]['states'][valve] = "closed"
        self.device.eeprom.save_config_to_eeprom()

    def open_all(self):
        open_valves = self.get_fully_open_valves()
        for valve in range(1, 8):
            if valve not in open_valves:
                self.open(valve=valve)

    def close_all(self):
        assert not self.device.is_pumping(), "can't close last valve while pumping"
        closed_valves = self.get_fully_closed_valves()
        for valve in range(1, 8):
            if valve not in closed_valves:
                self.close(valve=valve)

    def close_all_except(self, valve):
        for v in range(1, 8):
            if v != valve and v not in self.get_fully_closed_valves():
                self.close(valve=v)

    def set_state(self, valve, is_open=False):
        assert is_open in [True, False]
        if is_open:
            self.open(valve)
        else:
            self.close(valve)
