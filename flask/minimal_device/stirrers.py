import time


class Stirrers:
    led_numbers = {stirrer: 7 - stirrer for stirrer in [1, 2, 3, 4, 5, 6, 7]}

    def __init__(self, device):
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
                accelerate_duty_cycle = self.device.device_data["stirrers"]["calibration"][vial]["high"]*1.2
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
                if speed == 0:
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


# def get_speed(vial_number=7,nbytes=4096,freq=1e5):
#     vial_number = 7 - vial_number
#     assert 0 <= vial_number <= 6
#     pm.slave_gpio_multiplexer.write_to(7, [0x00]) # 7 - port 1, 0x00 - output pin
#     pm.slave_gpio_multiplexer.write_to(2, [6 - vial_number])
#
#
#     fans.set_frequency(freq)
#     time.sleep(0.01)
#     res=fans.read(nbytes)
#
#     binstr="".join([bin(r)[2:].rjust(8,"0") for r in res])
#     binstr=binstr.replace("1110111", "1111111")
#     binstr=binstr.replace("11100111","11111111")
#
#     print(binstr,"\n")
#
#     sum(1 for i in binstr if i =="1")/(8*nbytes)
#
#     repeats = r'(.)\1+'
#
#     periods=[]
#     for match in re.finditer(repeats, binstr):
#         periods+=[len(match.group())]
#
#
#     periods=np.array(periods)
# #     print(periods)
#     if len(periods)>5:
#         periods=np.delete(periods,periods.argmin())
#         periods=np.delete(periods,periods.argmin())
#         periods=np.delete(periods,periods.argmin())
#     print("periods:",periods)
#
#     rpm=60*freq/periods.mean()/2
#     err=periods.std()/periods.mean()
#
# #     if err>0.06 or len(periods)<3:
# #         print('high error')
# #         time.sleep(3)
# #         if nbytes<=65280/5:
# #             nbytes*=2
# #         return get_speed(vial_number,nbytes,freq=freq)
#     print("Speed:",int(rpm),"RPM","±",int(err*rpm))
#     return rpm
