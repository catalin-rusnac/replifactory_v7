
import axios from 'axios';

let flaskport = "3000/flask";
if (process.env.NODE_ENV === 'development') {
    flaskport = 5000;
}
let baseURL = `http://127.0.0.1:${flaskport}`;

const flaskAxios = axios.create({
  baseURL: baseURL,
});

export default {
  namespaced: true,
  state: {
      deviceConnected: false,
      deviceControlEnabled: true,
    calibrationModeEnabled: false,
    valves: {states: {1: "open", 2: "open", 3: "open", 4: "open", 5: "open", 6: "open", 7: "open"}},

    pumps: {
      states: {1: "stopped", 2: "stopped", 3: "stopped"},
      volume: {1: 0, 2: 0, 3: 0},
      calibration: {
        1: {1: 0.2, 5: 0.19, 10: 0.18, 50: 0.17},
        2: {1: 0.2, 5: 0.19, 10: 0.18, 50: 0.17},
        3: {1: 0.2, 5: 0.19, 10: 0.18, 50: 0.17}
      }
    },
    stirrers: {
      states: {1: "stopped", 2: "high", 3: "low", 4: "stopped", 5: "stopped", 6: "stopped", 7: "stopped"},
      calibration: {
        1: {"low": 40, "high": 50},
        2: {"low": 40, "high": 50},
        3: {"low": 40, "high": 50},
        4: {"low": 40, "high": 50},
        5: {"low": 40, "high": 50},
        6: {"low": 40, "high": 50},
        7: {"low": 40, "high": 50}
      },
    },
    ods: {
      states: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6:0, 7:0},
      calibration: {
        1: {0.00788: 40.375,
            0.0158: 39.781,
            0.0315: 38.664,
            0.0630: 36.508,
            0.126: 32.789,
            0.252: 26.750,
            0.504: 18.367,
            1.01: 9.719,
            2.02: 3.961,
            4.03: 1.648},
        2: {0.00788: 40.375,
            0.0158: 39.781,
            0.0315: 38.664,
            0.0630: 36.508,
            0.126: 32.789,
            0.252: 26.750,
            0.504: 18.367,
            1.01: 9.719,
            2.02: 3.961,
            4.03: 1.648},
        3: {0.00788: 40.375,
            0.0158: 39.781,
            0.0315: 38.664,
            0.0630: 36.508,
            0.126: 32.789,
            0.252: 26.750,
            0.504: 18.367,
            1.01: 9.719,
            2.02: 3.961,
            4.03: 1.648},
        4: {0.00788: 40.375,
            0.0158: 39.781,
            0.0315: 38.664,
            0.0630: 36.508,
            0.126: 32.789,
            0.252: 26.750,
            0.504: 18.367,
            1.01: 9.719,
            2.02: 3.961,
            4.03: 1.648},
        5: {0.00788: 40.375,
            0.0158: 39.781,
            0.0315: 38.664,
            0.0630: 36.508,
            0.126: 32.789,
            0.252: 26.750,
            0.504: 18.367,
            1.01: 9.719,
            2.02: 3.961,
            4.03: 1.648},
        6: {0.00788: 40.375,
            0.0158: 39.781,
            0.0315: 38.664,
            0.0630: 36.508,
            0.126: 32.789,
            0.252: 26.750,
            0.504: 18.367,
            1.01: 9.719,
            2.02: 3.961,
            4.03: 1.648},
        7: {0.00788: 40.375,
            0.0158: 39.781,
            0.0315: 38.664,
            0.0630: 36.508,
            0.126: 32.789,
            0.252: 26.750,
            0.504: 18.367,
            1.01: 9.719,
            2.02: 3.961,
            4.03: 1.648}
      },
    },
      odsignals: {1:40, 2:40, 3:40, 4:40, 5:40, 6:40, 7:40},
      temperatures:
        {states: {1: 0, 2: 0}},
  },

mutations: {
    setPartCalibration(state, { devicePart, partIndex, newCalibration }) {
      state[devicePart].calibration[partIndex] = newCalibration;
    },
    setPartState(state, { devicePart, partIndex, newState }) {
      state[devicePart].states[partIndex] = newState;
    },
    setAllDeviceStates(state, data) {
        state.valves = data.valves;
        state.pumps = data.pumps;
        state.stirrers = data.stirrers;
        state.ods = data.ods;
        state.odsignals = data.odsignals;
        state.temperatures = data.temperatures;
    },
    toggleCalibrationMode(state) {
      state.calibrationModeEnabled = !state.calibrationModeEnabled;
    },
    addODCalibrationRow(state, newOD) {
      const odsIndexes = Object.keys(state.ods.calibration); // Renamed to odsIndexes
        // console.log(odsIndexes);
      odsIndexes.forEach(odsIndex => {
        state.ods.calibration[odsIndex][newOD] = null;
      });
      state.ods = { ...state.ods };
    },
    setDeviceControlEnabled(state, newState) {
        state.deviceControlEnabled = newState;
    }


  },

  actions: {
    setAllStirrersStateAction({ dispatch, state }, newState) {
        Object.keys(state.stirrers.states).forEach(stirrerIndex => {
          // Parse the stirrerIndex to an integer before passing to setPartStateAction
          dispatch('setPartStateAction', { devicePart: 'stirrers', partIndex: parseInt(stirrerIndex), newState: newState});
        });
        },
    setPartCalibrationAction({ commit }, payload) {
        const { devicePart, partIndex, newCalibration } = payload;
        const endpoint = `/set-${devicePart}-calibration`;

        return new Promise((resolve, reject) => {
            flaskAxios.post(endpoint, { partIndex, newCalibration })
            .then(response => {
            if (response.data.success) {
              commit('setPartCalibration', { devicePart, partIndex, newCalibration: response.data.newCalibration });
              resolve();
            } else {
              console.error(`Error updating ${devicePart} calibration:`, response.data.message);
              reject();
            }
          })
          .catch(error => {
            console.error(`Error updating ${devicePart} calibration:`, error);
            reject();
          });
      });
    },

    setPartStateAction({ commit }, payload) {
      const { devicePart, partIndex, newState, input } = payload;
      const endpoint = `/set-${devicePart}-state`;

      return new Promise((resolve, reject) => {
        flaskAxios.post(`${endpoint}`, { partIndex, newState, input })
          .then(response => {
            if (response.data.success) {
              commit('setPartState', { devicePart, partIndex, newState: response.data.newState});
              resolve();
            } else {
              reject();
            }
          })
          .catch(error => {
            console.error(`Error updating ${devicePart} state:`, error);
            reject();
          });
      });
    },

    connectDevice({ dispatch }) {
      return new Promise((resolve, reject) => {
          console.log("connect device request", flaskAxios, baseURL);
        flaskAxios.post('/connect-device')
          .then(response => {
              console.log("connect device response: ", response.data);
            if (response.data.success) {
              dispatch('getAllDeviceData')
                .then(() => {
                  resolve();
                })
                .catch(() => {
                  reject();
                });
            } else {
              console.error('Error connecting device: server responded with an error');
              reject();
            }
          })
          .catch(error => {
            console.error('Error connecting device:', error);
            reject(error);
          });
      });
    },

    getAllDeviceData({ commit }) {
        return new Promise((resolve, reject) => {
            flaskAxios.get('/get-all-device-data')
            .then(response => {
                if (response.data.success) {
                    commit('setAllDeviceStates', response.data.device_states);
                    resolve();
                } else {
                    console.error('Error fetching device data: server responded with an error');
                    reject();
                }
            })
            .catch(error => {
                console.error('Error fetching device data:', error);
                reject(error);
            });
        });
    },
    measureDevicePart({ commit }, payload) {
      const { devicePart, partIndex } = payload;
      const endpoint = `/measure-${devicePart}`;

      return new Promise((resolve, reject) => {
        flaskAxios.post(endpoint, { partIndex })
          .then(response => {
            if (response.data.success) {
                commit('setAllDeviceStates', response.data.device_states);
                resolve();
            } else {
              console.error(`Error measuring ${devicePart}:`, response.data.message);
              reject();
            }
          })
          .catch(error => {
            console.error(`Error measuring ${devicePart}:`, error);
            reject();
          });
      });
    },
  },
};
