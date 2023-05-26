import pyftdi.i2c
import time


def set_bit(v, index, x):  # source: stackoverflow.com/questions/12173774/
    """Set the index:th bit of v to 1 if x is truthy, else to 0, and return the new value."""
    mask = 1 << index  # Compute mask, an integer with just bit 'index' set.
    v &= ~mask  # Clear the bit indicated by the mask (if x is False)
    if x:
        v |= mask  # If x was True, set the bit indicated by the mask.
    return v  # Return the result, we're done.


class Lasers:
    registers = {1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3}
    bits = {1: 1, 2: 3, 3: 5, 4: 7, 5: 1, 6: 3, 7: 5}

    def __init__(self, device):
        self.device = device
        self.multiplexer_port = None

        if self.device.is_connected():
            self.connect()

    def connect(self):
        try:
            self.multiplexer_port = self.device.i2c.get_port(
                self.device.PORT_GPIO_MULTIPLEXER_LASERS
            )
            self.multiplexer_port.write_to(6, [0x00])  # set all GPIO pins as output
            self.multiplexer_port.write_to(7, [0x00])  # set all GPIO pins as output
        except pyftdi.i2c.I2cNackError:
            print("PCA9555 laser multiplexer connection ERROR.")

    def switch_on(self, vial):
        register = self.registers[vial]
        bit = self.bits[vial]
        old_byte = self.multiplexer_port.read_from(register, 1)[
            0
        ]  # read which lasers are currently shining
        new_byte = set_bit(old_byte, bit, 0)
        self.multiplexer_port.write_to(register, [new_byte])

    def switch_off(self, vial):
        register = self.registers[vial]
        bit = self.bits[vial]
        old_byte = self.multiplexer_port.read_from(register, 1)[
            0
        ]  # read which lasers are currently shining
        new_byte = set_bit(old_byte, bit, 1)
        self.multiplexer_port.write_to(register, [new_byte])

    def switch_all_on(self):
        self.multiplexer_port.write_to(2, [0b00000000])
        self.multiplexer_port.write_to(3, [0b00000000])

    def switch_all_off(self):
        self.multiplexer_port.write_to(2, [0b11111111])
        self.multiplexer_port.write_to(3, [0b11111111])

    def blink(self):
        for i in range(7):
            self.switch_all_on()
            time.sleep(0.04)
            self.switch_all_off()
            time.sleep(0.04)
