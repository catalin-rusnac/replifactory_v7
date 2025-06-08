// implement pinia store for device control

import { defineStore } from 'pinia'
import api from '@/api'

export const useDeviceStore = defineStore('device', {
  state: () => ({
    deviceConnected: false,
    deviceControlEnabled: false,
    calibrationModeEnabled: false,
    valves: {},
    pumps: {},
    stirrers: {},
    ods: {},
    thermometers: {},
    leds: {},
    isFetchingCalibration: false,
    errorMessage: null,
  }),
  actions: {
    async fetchDeviceData() {
      try {
        const response = await api.get('/get-all-device-data')
        if (response.data.success) {
          const data = response.data.device_states
          this.valves = data.valves
          this.pumps = data.pumps
          this.stirrers = data.stirrers
          this.ods = data.ods
          this.thermometers = data.temperatures
          this.leds = data.leds
          this.deviceConnected = true
          this.deviceControlEnabled = true
        } else {
          this.deviceConnected = false
          this.deviceControlEnabled = false
          this.errorMessage = 'Failed to fetch device data.'
        }
      } catch (error) {
        this.deviceConnected = false
        this.deviceControlEnabled = false
        this.errorMessage = 'Failed to fetch device data.'
      }
    },
    async setPartState(devicePart, partIndex, newState, input) {
      try {
        const response = await api.post(`/set-${devicePart}-state`, { partIndex, newState, input })
        if (response.data.success) {
          await this.fetchDeviceData()
        } else {
          this.errorMessage = `Failed to set ${devicePart} state.`
        }
      } catch (error) {
        this.errorMessage = `Failed to set ${devicePart} state.`
      }
    },
    async setLedColor(vial, red, green, blue) {
      try {
        const response = await api.post('/set-led-color', { vial, red, green, blue })
        if (response.data.success) {
          await this.fetchDeviceData()
        } else {
          this.errorMessage = 'Failed to set LED color.'
        }
      } catch (error) {
        this.errorMessage = 'Failed to set LED color.'
      }
    },
    async setPartCalibration(devicePart, partIndex, newCalibration) {
      try {
        const response = await api.post(`/set-${devicePart}-calibration`, { partIndex, newCalibration })
        if (response.data.success) {
          await this.fetchDeviceData()
        } else {
          this.errorMessage = `Failed to set ${devicePart} calibration.`
        }
      } catch (error) {
        this.errorMessage = `Failed to set ${devicePart} calibration.`
      }
    },
    async connectDevice() {
      try {
        const response = await api.post('/connect-device')
        if (response.data.success) {
          this.deviceConnected = true
          this.deviceControlEnabled = true
          await this.fetchDeviceData()
        } else {
          this.deviceConnected = false
          this.deviceControlEnabled = false
          this.errorMessage = 'Failed to connect device.'
        }
      } catch (error) {
        this.deviceConnected = false
        this.deviceControlEnabled = false
        this.errorMessage = 'Failed to connect device.'
      }
    },
    setDeviceControlEnabled(newState) {
      this.deviceControlEnabled = newState
    },
    setCalibrationModeEnabled(newState) {
      this.calibrationModeEnabled = newState
    },
    setErrorMessage(message) {
      this.errorMessage = message
    },
    async setPartStateAction(payload) {
      // payload: { devicePart, partIndex, newState, input }
      return this.setPartState(payload.devicePart, payload.partIndex, payload.newState, payload.input)
    },
    async setPartCalibrationAction(payload) {
      console.log("setPartCalibrationAction", payload)
      return this.setPartCalibration(payload.devicePart, payload.partIndex, payload.newCalibration)
    },
    toggleCalibrationMode() {
      this.calibrationModeEnabled = !this.calibrationModeEnabled
    },
    async measureDevicePart({ devicePart, partIndex }) {
      try {
        const response = await api.post(`/measure-${devicePart}`, { partIndex })
        if (response.data.success) {
          await this.fetchDeviceData()
        } else {
          this.errorMessage = `Failed to measure ${devicePart}.`
        }
      } catch (error) {
        this.errorMessage = `Failed to measure ${devicePart}.`
      }
    },
    async setAllStirrersStateAction(newState) {
      // Set all stirrers (1-7) to the given state in parallel
      const stirrerIds = [1,2,3,4,5,6,7];
      await Promise.all(stirrerIds.map(id => this.setPartState('stirrers', id, newState)));
      await this.fetchDeviceData();
    },
    async measureODCalibrationAction({ odValue }) {
      try {
        const response = await api.post('/measure-od-calibration', { odValue: parseFloat(odValue) });
        if (response.data.success) {
          await this.fetchDeviceData();
        } else {
          this.errorMessage = 'Failed to measure OD calibration.';
        }
      } catch (error) {
        this.errorMessage = 'Failed to measure OD calibration.';
      }
    },
    async measureAllODSignalsAction(payload) {
      try {
        const response = await api.post('/measure-all-od-signals', payload);
        if (response.data.success) {
          console.log("measured all od signals", response.data.device_states.ods.calibration)
          await this.fetchDeviceData();
        } else {
          this.errorMessage = 'Failed to measure all OD signals.';
        }
      } catch (error) {
        this.errorMessage = 'Failed to measure all OD signals.';
      }
    },
    async updateODCalibrationKeyAction({ oldOD, newOD }) {
      try {
        const response = await api.post('/update-od-calibration-key', { oldOD, newOD });
        if (response.data.success) {
          await this.fetchDeviceData();
        } else {
          this.errorMessage = 'Failed to update OD calibration key.';
        }
      } catch (error) {
        this.errorMessage = 'Failed to update OD calibration key.';
      }
    },
    async updateODCalibrationValueAction({ od, vial, newValue }) {
      try {
        const response = await api.post('/update-od-calibration-value', { od, vial, newValue });
        if (response.data.success) {
          await this.fetchDeviceData();
        } else {
          this.errorMessage = 'Failed to update OD calibration value.';
        }
      } catch (error) {
        this.errorMessage = 'Failed to update OD calibration value.';
      }
    },
    async removeODCalibrationRowAction(odValue) {
      try {
        const response = await api.post('/remove-od-calibration-row', { odValue });
        if (response.data.success) {
          await this.fetchDeviceData();
        } else {
          this.errorMessage = 'Failed to remove OD calibration row.';
        }
      } catch (error) {
        this.errorMessage = 'Failed to remove OD calibration row.';
      }
    },
    async saveCalibrationToBackend() {
      try {
        const response = await api.post('/save-calibration');
        if (response.data.success) {
          await this.fetchDeviceData();
        } else {
          this.errorMessage = 'Failed to save calibration.';
        }
      } catch (error) {
        this.errorMessage = 'Failed to save calibration.';
      }
    },
    async listDeviceConfigs() {
      try {
        const response = await api.get('/list-device-configs');
        return response.data.configs;
      } catch (error) {
        this.errorMessage = 'Failed to list device configs.';
      }
    },
    async loadDeviceConfig(filename) {
      try {
        const response = await api.post('/load-device-config', { filename });
        if (response.data.success) {
          await this.fetchDeviceData();
        } else {
          this.errorMessage = 'Failed to load device config.';
        }
      } catch (error) {
        this.errorMessage = 'Failed to load device config.';
      }
    },
    async startPumpCalibrationSequence(payload) {
      const { pumpId, rotations, iterations } = payload;
      const devicePart = 'pumps';
      const endpoint = `/start-pump-calibration-sequence`;
      try {
        const response = await api.post(endpoint, { pumpId, rotations, iterations });
        if (response.data.success) {
          await this.setPartStateAction({ devicePart, partIndex: pumpId, newState: "stopped" });
          return true;
        } else {
          this.errorMessage = `Error updating ${devicePart} calibration: ${response.data.message}`;
          throw new Error(this.errorMessage);
        }
      } catch (error) {
        this.errorMessage = `Error updating ${devicePart} calibration: ${error.message || error}`;
        throw error;
      }
    }
  }
})
