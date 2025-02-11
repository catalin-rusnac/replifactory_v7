import api from '@/api.js';

export default {
  namespaced: true,
  state: {
    isFetchingCalibration: false,
    calibrationModeEnabled: false,
    valves: {states: {1: "open", 2: "open", 3: "open", 4: "open", 5: "open", 6: "open", 7: "open"}},

    pumps: {
      states: {1: "stopped", 2: "stopped", 3: "stopped"},
      volume: {1: null, 2: null, 3: null, 4: null},
      calibration: {
        1: {1: 0.2, 5: 0.19, 10: 0.18, 50: 0.17},
        2: {1: 0.2, 5: 0.19, 10: 0.18, 50: 0.17},
        3: {1: 0.2, 5: 0.19, 10: 0.18, 50: 0.17},
        4: {1: 0.2, 5: 0.19, 10: 0.18, 50: 0.17},
      }
    },
    stirrers: {
      states: {1: "stopped", 2: "high", 3: "low", 4: "stopped", 5: "stopped", 6: "stopped", 7: "stopped"},
      calibration: {
        1: {"low": 0.40, "high": 0.50},
        2: {"low": 0.40, "high": 0.50},
        3: {"low": 0.40, "high": 0.50},
        4: {"low": 0.40, "high": 0.50},
        5: {"low": 0.40, "high": 0.50},
        6: {"low": 0.40, "high": 0.50},
        7: {"low": 0.40, "high": 0.50}
      },
    },
    ods: {
      states: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6:0, 7:0},
    odsignals: {1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0},

        calibration_coefs: {1: [4,1,10,-0.5,4],
                              2: [4,1,10,-0.5,4],
                              3: [4,1,10,-0.5,4],
                              4: [4,1,10,-0.5,4],
                              5: [4,1,10,-0.5,4],
                              6: [4,1,10,-0.5,4],
                              7: [4,1,10,-0.5,4]},
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
      thermometers:
        {states: {1: 0, 2: 0}},
  },

mutations: {
    setIsFetchingCalibration(state, status) {
      state.isFetchingCalibration = status;
    },
    setPartCalibration(state, { devicePart, partIndex, newCalibration, coefs}) {
      state[devicePart].calibration[partIndex] = newCalibration;
     if (coefs) {
         state[devicePart].calibration_coefs[partIndex] = coefs;
     }

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
        state.leds = data.leds;
    },
    toggleCalibrationMode(state) {
      state.calibrationModeEnabled = !state.calibrationModeEnabled;
    },
    removeODCalibrationRow(state, oldOD) {
        const odsIndexes = Object.keys(state.ods.calibration); // Renamed to odsIndexes
        odsIndexes.forEach(odsIndex => {
            delete state.ods.calibration[odsIndex][oldOD];
        });
        // state.ods = { ...state.ods };
    },

    updateODCalibrationValue(state, {od, odsIndex, newValue}) {
        if (newValue === "") {
            delete state.ods.calibration[odsIndex][od]
        }
        else {
        state.ods.calibration[odsIndex][od]  = parseFloat(newValue);
        }
    },

    updateODCalibrationKey(state, {oldOD, newOD}) {
      // Loop over each item in the ods.calibration object
      // Check if the oldOD key exists before trying to replace it
        console.log(oldOD, newOD, "change")
        for (let i = 1; i <= 7; i++) {
            if (state.ods.calibration[i] && state.ods.calibration[i][oldOD]) {
                // Replace the oldOD key with the newOD key
                state.ods.calibration[i][newOD] = state.ods.calibration[i][oldOD];
                // Delete the oldOD key
                delete state.ods.calibration[i][oldOD];
            }
        }
    },
    setDeviceControlEnabled(state, newState) {
        state.deviceControlEnabled = newState;
    }


  },

  actions: {
    async fetchODCalibrationData({ commit, dispatch }) {
        commit('setIsFetchingCalibration', true);
        try {
            const response = await api.get('/run-ods-test');
            //   once the response is received, get dispatch the get all device data action
            if (response.data) {
                dispatch('getAllDeviceData').then(() => {
                    commit('setIsFetchingCalibration', false);
                });
            }
        } catch (error) {
        commit('setIsFetchingCalibration', false);
        console.error('Error fetching OD calibration data:', error);
        throw error;
        }
    },

    async fetchStirrerCalibrationData({ commit, dispatch }) {
        commit('setIsFetchingCalibration', true);
        try {
            const response = await api.get('/run-stirrer-test');
            //   once the response is received, get dispatch the get all device data action
            if (response.data) {
                dispatch('getAllDeviceData').then(() => {
                    commit('setIsFetchingCalibration', false);
                });
            }
        } catch (error) {
        commit('setIsFetchingCalibration', false);
        console.error('Error fetching stirrer calibration data:', error);
        throw error;
        }
    },
    setAllStirrersStateAction({ dispatch, state }, newState) {
        Object.keys(state.stirrers.states).forEach(stirrerIndex => {
          // Parse the stirrerIndex to an integer before passing to setPartStateAction
          dispatch('setPartStateAction', { devicePart: 'stirrers', partIndex: parseInt(stirrerIndex), newState: newState});
        });
        },
      async updateODCalibrationKeyAction({ dispatch, commit, state }, payload) {
        const { oldOD, newOD } = payload;
        await commit('updateODCalibrationKey', {oldOD, newOD}); // Assuming 'updateODCalibrationKey' mutation accepts an object as payload
          console.log(newOD, state.ods.calibration[1])
        for (let i = 1; i <= 7; i++) {
            await dispatch('setPartCalibrationAction', { devicePart: 'ods', partIndex: i, newCalibration: state.ods.calibration[i] })
            .catch(error => console.error(`Error dispatching setPartCalibrationAction:`, error));
        }
    },

      async updateODCalibrationValueAction({ dispatch, commit, state }, payload) {
        const i = payload.odsIndex;
        await commit('updateODCalibrationValue', payload);
        await dispatch('setPartCalibrationAction', { devicePart: 'ods', partIndex: i, newCalibration: state.ods.calibration[i] })
            .catch(error => console.error(`Error during updateODCalibrationValueAction:`, error));
    },

    async removeODCalibrationRowAction({ dispatch, commit, state }, oldOD) {
            try {
                commit('removeODCalibrationRow', oldOD);
                for (let i = 1; i <= 7; i++) {
                    await dispatch('setPartCalibrationAction', { devicePart: 'ods', partIndex: i, newCalibration: state.ods.calibration[i] });
                    console.log(state.ods.calibration[i],' setPartCalibrationAction***********************')
                }
            } catch (error) {
                console.error(`Error removing OD calibration row:`, error);
            }
        },
      setPartCalibrationAction({ commit }, payload) {
        const { devicePart, partIndex, newCalibration } = payload;
        const endpoint = `/set-${devicePart}-calibration`;
        for(let key in newCalibration){
            if(newCalibration[key] === null)
                delete newCalibration[key];
        }

        return new Promise((resolve, reject) => {
            api.post(endpoint, { partIndex, newCalibration })
            .then(response => {
            if (response.data.success) {
                console.log(response.data, "response.data from setpartcalibrationaction")
              commit('setPartCalibration', { devicePart, partIndex, newCalibration: response.data.newCalibration, coefs: response.data.coefs });

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
    measureODCalibrationAction({ dispatch }, payload) {
        const { odValue } = payload;
        const endpoint = `/measure-od-calibration`;

        return new Promise((resolve, reject) => {
            api.post(endpoint, { odValue: parseFloat(odValue) })
                .then(response => {
                    if (response.data.success) {
                        dispatch('getAllDeviceData').then(() => {
                            resolve();

                        })
                    }
                })
                .catch(error => {
                    console.error(`Error updating od calibration:`, error);
                    reject();
                }
            );
        });
    },
      startPumpCalibrationSequence({ dispatch }, payload) {
            const { pumpId, rotations, iterations } = payload;
            const devicePart = 'pumps';
            const endpoint = `/start-pump-calibration-sequence`;
            console.log("startPumpCalibrationSequence", payload);
            return new Promise((resolve, reject) => {
                api.post(endpoint, { pumpId, rotations, iterations })
                    .then(response => {
                        if (response.data.success) {
                            dispatch('setPartStateAction', { devicePart:devicePart, partIndex:pumpId, newState: "stopped" }).then(() => {
                                resolve();
                            });}
                        else {
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
      commit('setPartState', { devicePart, partIndex, newState: newState});

      return new Promise((resolve, reject) => {
        api.post(`${endpoint}`, { partIndex, newState, input })
          .then(response => {
            if (response.data.success) {
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

    connect() {
        return new Promise((resolve, reject) => {
            console.log("connect device request", api);
            api.post('/connect-device')
                .then(response => {
                    if (response.data.success) {
                        resolve(response); // Resolve the response so that it can be used in the connectDevice action
                    } else {
                        console.error('Error connecting device: server responded with error:', response);
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
            api.get('/get-all-device-data')
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
        api.post(endpoint, { partIndex })
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
    setLedColor({commit}, payload) {
        const { vial, red, green, blue } = payload;
        console.log("Setting LED color", {vial, red, green, blue});
        return new Promise((resolve, reject) => {
            api.post('/set-led-color', { vial:vial, red:red, green:green, blue:blue })
                .then(response => {
                    if (response.data.success) {
                        commit('setAllDeviceStates', response.data.device_states);
                        resolve();
                    } else {
                        console.error('Error setting LED color:', response.data.message);
                        reject();
                    }
                })
                .catch(error => {
                    console.error('Error setting LED color:', error);
                    reject(error);
                });
        });
    },

  },
};
