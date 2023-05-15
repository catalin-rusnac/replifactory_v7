import time


class Testing:
    def __init__(self, device):
        self.device = device
        self.stop_test = False

    def test_laser_signals(self):
        self.device.od_sesor.check()

    def stop(self):
        self.stop_test = True

    def check_stop(self):
        if self.stop_test:
            self.device.emergency_stop()
            raise RuntimeError("Test stopped")

    def background_visual_test_pump(self, main_gui=None, pump_number=1):
        def queued_function():
            try:
                main_gui.device_tab.testing_tab.pump_test_button.icon = "fa-spinner"
                main_gui.device_tab.testing_tab.pump_test_button.disabled = True
                self.visual_test_pump(pump_number=pump_number)
            finally:
                main_gui.device_tab.testing_tab.pump_test_button.icon = "fa-tint"
                main_gui.device_tab.testing_tab.pump_test_button.disabled = False

        self.device.dilution_worker.queue.put(queued_function)

    def visual_test_pump(self, pump_number=1, reverse=False):
        self.stop_test = False
        print("Starting fluid test: closing valves")
        self.check_stop()
        self.device.valves.close_all()
        self.check_stop()

        first_vial = 1
        if self.device.is_lagoon_device() and pump_number == 2:
            first_vial = 2

        self.device.valves.open(first_vial)
        self.check_stop()
        if reverse:
            exec("self.device.pump%d.move(-150)" % pump_number)
        else:
            exec("self.device.pump%d.move(150)" % pump_number)
        self.check_stop()
        print("pump %d pumping to vial 1" % pump_number)
        for i in range(6):
            time.sleep(0.5)
            self.check_stop()

        for v in range(first_vial, 7):
            self.check_stop()
            self.device.valves.open(v + 1)
            self.check_stop()
            print("pump %d pumping to vial %d and %d" % (pump_number, v, v + 1))
            self.device.valves.close(v)
            print("pump %d pumping to vial %d" % (pump_number, v + 1))
            self.check_stop()
            time.sleep(1)
            self.check_stop()
        exec("self.device.pump%d.stop()" % pump_number)
        # self.device.pump1.stop()
        self.check_stop()
        time.sleep(2)

        if not self.device.is_pumping():
            self.device.valves.close(7)
        else:
            print("valve 7 left open")
        print("FINISHED")
        print("test passed if no leakage was observed")
