import sys
sys.path.append('./flask/')

from minimal_device.base_device import BaseDevice
dev = BaseDevice(connect=True)
dev.hello()
#%%
dev.eeprom.read_config_from_device()
#%%
from minimal_device.device_data import device_data
print(device_data)
dev.device_data = device_data
import time
t=time.time()
dev.eeprom.save_config_to_eeprom()
print(dev.device_data)
print(time.time()-t)

dev.stirrers.set_speed(1, "stopped")
dev.stirrers._get_duty_cycle(1)
#%%
dev.disconnect_all()