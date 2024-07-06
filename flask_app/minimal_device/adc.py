import time

import pyftdi.i2c


class Photodiodes:
    def __init__(self, device):
        self.device = device
        self.adc_port = None
        self.multiplexer_port = None

        if self.device.is_connected():
            self.connect()

    def connect(self):
        lock_acquired = self.device.lock_ftdi.acquire(timeout=3)
        if not lock_acquired:
            raise Exception("Could not acquire lock to connect photodiodes at time %s" % time.ctime())

        try:
            self.adc_port = self.device.i2c.get_port(
                self.device.PORT_ADC
            )  # photodiodes ADC
            self.multiplexer_port = self.device.i2c.get_port(self.device.PORT_GPIO_MULTIPLEXER_ADC)
            self.multiplexer_port.write_to(6, [0x00])  # set all GPIO pins as output
            self.multiplexer_port.write_to(7, [0x00])  # set all GPIO pins as output
        except pyftdi.i2c.I2cNackError:
            print("Photodiode multiplexer or ADC connection ERROR.")
        finally:
            self.device.lock_ftdi.release()

    def switch_to_vial(self, vial):
        vial = vial - 1
        assert 0 <= vial <= 6
        self.multiplexer_port.write_to(3, [6 - vial])

    def measure(self, gain=8, bitrate=16, continuous_conversion=False):
        ready_bit = 0b10000000
        if continuous_conversion:
            conversion_mode = 0b00010000
        else:
            conversion_mode = 0b00000000  # One-shot conversion mode
        bitrate_bits = {12: 0b0000, 14: 0b0100, 16: 0b1000, 18: 0b1100}
        bitrate_to_samples_per_second = {
            12: 240,  # from MCP3421 datasheet
            14: 60,
            16: 15,
            18: 3.75,
        }
        gain_bits = {1: 0b00, 2: 0b01, 4: 0b10, 8: 0b11}

        write_byte = (
            ready_bit | conversion_mode | bitrate_bits[bitrate] | gain_bits[gain]
        )
        self.adc_port.write([write_byte])

        new_data_is_ready = False
        for _ in range(100):  # try reading until conversion ready
            samples_per_second = bitrate_to_samples_per_second[bitrate]
            seconds_per_sample = 1 / samples_per_second

            time.sleep(seconds_per_sample)
            response = self.adc_port.read(4)
            data = response[:2]
            config = response[3:]
            if bitrate == 18:
                data = response[:3]  # 3 bytes for 18bit

            new_data_is_ready = (
                config[0] < 128
            )  # if bit 7 (ready bit) is 1: NOT READY YET!
            if new_data_is_ready:
                break

        assert new_data_is_ready
        data_bits = "".join([bin(x)[2:].rjust(8, "0") for x in data])[-bitrate:]
        sign_bit = data_bits[0]
        digital_signal = sum(
            [2**i for i in range(len(data_bits)) if data_bits[::-1][i] == "1"]
        )
        if sign_bit == "1":
            digital_signal = digital_signal - 2**bitrate
        millivolts = 2 * 2.048 / 2**bitrate * digital_signal * 1000 / gain
        millivolts = round(millivolts, 10)
        lsb_mv = (
            2.048 * 2 / 2**bitrate * 1000 / gain
        )  # least significant bit millivolts
        return millivolts, lsb_mv
