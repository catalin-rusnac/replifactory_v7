#%%
import os
import sys
sys.path.append('./flask_app/')
import importlib
import minimal_device
from minimal_device.base_device import BaseDevice

importlib.reload(minimal_device)
dev = BaseDevice()
dev.connect()
# dev.hello()
#%%
[dev.stirrers._set_duty_cycle(v, 0) for v in range(1,8)]
speeds = dev.stirrers.measure_all_rpms()
#%%
import numpy as np
import re
import time
import matplotlib.pyplot as plt
speeds={1:0.4,
 2:0.4,
 3:0.49,
 4:0.46,
 5:0.39,
 6:0.38,
 7:0.4}
[dev.stirrers._set_duty_cycle(v, speeds[v]) for v in range(1,8)]
#%%
#%%
dev.stirrers._set_duty_cycle(7, 0.4)
import time
import re
import numpy as np
import matplotlib.pyplot as plt
#%%
rpm=3000
for i in range(8):
    rpm=dev.stirrers.measure_rpm(7, estimated_rpm=1000)
    print(rpm)
    time.sleep(0.5)
#%%
dev.device_data["stirrers"]["calibration"][vial_number]={'high': 1, 'low': 0.1}

#%%
vial_number=7
rpm_dc={}
dev.stirrers.get_calibration_curve(vial_number, n_points=5)
#%%
plt.plot(list(rpm_dc.keys()),list(rpm_dc.values()),"ro-")
plt.title("Vial %d RPM vs Duty Cycle"%vial_number)
plt.xlabel("Duty Cycle")
plt.ylabel("RPM")
plt.show()
#%%
results = []
estimated_rpm = 1000
for _ in range(9):
    results += [dev.stirrers.measure_rpm(vial_number, estimated_rpm=estimated_rpm)]
    estimated_rpm = results[-1]
    plt.plot(results)
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
