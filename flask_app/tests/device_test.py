#%%
import sys
sys.path.append('./flask_app/')
from minimal_device.base_device import BaseDevice
import time

dev = BaseDevice()
dev.connect()
dev.stirrers._set_duty_cycle(1, 0.6)
time.sleep(3)

rpm=dev.stirrers.measure_rpm(1)
print(rpm)
quit()