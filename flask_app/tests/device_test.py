#%%
import os
print(os.getcwd())
#%%
import sys
sys.path.append('./flask_app/')
import importlib
import minimal_device
from minimal_device.base_device import BaseDevice

importlib.reload(minimal_device)
dev = BaseDevice()
dev.connect()
dev.hello()
#%%
import numpy as np
import re
import time
import matplotlib.pyplot as plt


#%%
import time
import re
import numpy as np
import matplotlib.pyplot as plt


def get_speed(vial_number=7, estimated_rpm=3000):

    # Set the frequency to 10kHz
    freq = 1e5  # Hz

    # Calculate the estimated milliseconds per rotation
    ms_per_rotation = 60 / estimated_rpm * 1000

    # Calculate bits per minute and per rotation
    bits_per_minute = freq * 60
    bits_per_rotation = bits_per_minute / estimated_rpm

    # Calculate milliseconds per bit
    ms_per_bit = 1 / freq * 1000

    # Print estimated RPM and time calculations for debugging
    print("Estimated RPM:", estimated_rpm)
    print("ms per rotation:", ms_per_rotation, "ms per bit:", ms_per_bit)

    # Adjust bits per rotation based on measured rotation time
    bits_per_rotation = ms_per_rotation / ms_per_bit
    nbytes_per_rotation = bits_per_rotation / 8
    nbytes = int(nbytes_per_rotation*0.8)+16  # Safety factor to avoid overflow

    # Print measured total time for debugging
    print("ms measured total:", ms_per_bit * nbytes * 8)

    # Determine the pin number for the vial
    pin_number = 7 - vial_number

    # Set up the multiplexer for the given vial
    dev.stirrers.multiplexer_port.write_to(7, [0x00])  # Output pin
    dev.stirrers.multiplexer_port.write_to(2, [6 - pin_number])

    # Initialize SPI port for fans
    fans_spi_port = dev.spi.get_port(cs=4, freq=freq, mode=3)
    fans_spi_port.set_frequency(freq)
    time.sleep(0.3)

    # Read data from SPI port
    res = fans_spi_port.read(nbytes)
    binstr = "".join([bin(r)[2:].rjust(8, "0") for r in res])

    # Clean up the binary string
    binstr = binstr.replace("1110111", "1111111").replace("11100111", "11111111")

    # Calculate the ratio of '1's in the binary data
    ones_ratio = sum(1 for i in binstr if i == "1") / (8 * nbytes)
    print("Data length:", len(binstr), "Ones ratio: %.2f" % ones_ratio)

    # Find repeated sequences in the binary string
    periods = [len(match.group()) for match in re.finditer(r'(0+|1+)', binstr)][1:-1]

    # Check if any periods were found
    if len(periods) < 1:
        print("No periods found")
        print(binstr)
        print("New estimation:", estimated_rpm / 2)
        time.sleep(3)
        return get_speed(vial_number, estimated_rpm / 2)

    periods = np.array(periods)
    rpm = 60 * freq / periods.mean() / 2
    err = periods.std() / periods.mean()

    # Print the results
    print("Number of periods:", len(periods))
    print("Periods:", periods)
    print("Speed:", int(rpm), "RPM ±", int(err * rpm), "Error: %.1f%%" % (err * 100))
    print("ms per rotation actual: %.3f" % (1000 / (rpm / 60)))
    # print(binstr)
    return rpm


vial_number = 3
duty_cycle = 0.4
dev.stirrers._set_duty_cycle(vial_number, duty_cycle)

#%%
results = [get_speed(vial_number, estimated_rpm=1000) for _ in range(10)]
#%%
results = []
estimated_rpm = 1000
for _ in range(9):
    results += [dev.stirrers.get_speed(vial_number,estimated_rpm=estimated_rpm)]
    estimated_rpm = results[-1]
    plt.plot(results)
    # plt.ylim(min(results)*0.9, max(results)*1.1)
    # axhline for 95% confidence interval
    plt.axhline(np.mean(results) - 2*np.std(results), color='r', linestyle='--')
    plt.axhline(np.mean(results) + 2*np.std(results), color='r', linestyle='--')
    plt.show()
    time.sleep(2)
#%%
print(dev.device_data['valves']['states'][1])
#%%
vial=1
minimal_device.od_sensor.OdSensor.fit_calibration_function(dev.od_sensors[vial])
print(dev.device_data['ods']['calibration'][vial])
dev.od_sensors[vial].mv_to_od(10)
dev.od_sensors[vial].plot_calibration_curve()
#%%
import sys
sys.path.append('./flask/')

from minimal_device.base_device import BaseDevice
dev = BaseDevice(connect=True)
dev.hello()
#%%
dev.eeprom.read_config_from_device()
#%%
from minimal_device.device_data import default_device_data
print(default_device_data)
dev.device_data = default_device_data
import time
t=time.time()
dev.eeprom.save_config_to_eeprom()
print(dev.device_data)
print(time.time()-t)

dev.stirrers.set_speed(7, "high")
dev.stirrers._get_duty_cycle(1)
time.sleep(2)
dev.stirrers.set_speed(1, "stopped")
dev.stirrers._get_duty_cycle(1)
dev.stirrers.set_speed(1, "stopped")
dev.stirrers._get_duty_cycle(1)
#%%
dev.disconnect_all()
#%%
