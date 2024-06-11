#%%
import sys
sys.path.append('./flask_app/')
from minimal_device.base_device import BaseDevice

dev = BaseDevice()
dev.connect()
dev.hello()
quit()