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
dev.valves.close(1)

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
