import Vue from 'vue';
import Vuex from 'vuex';
import device from './deviceStore.js';
import experiment from './experimentStore.js';

Vue.use(Vuex);

export default new Vuex.Store({
  state:{deviceConnected: false,
  deviceControlEnabled: true,
  experimentRunning: null,
  },
  modules: {
    device,
    experiment,
  },
    mutations: {
        setDeviceConnected(state, value) {
            state.deviceConnected = value;
        }},
  actions: {
    async connectDevice({ dispatch, commit }) {
            try {
                const response = await dispatch('device/connect');
                if (response && response.data.success) {
                    await dispatch('device/getAllDeviceData');
                    commit('setDeviceConnected', true);
                } else {
                    commit('setDeviceConnected', false);
                }
            } catch (error) {
                console.log(error);
                commit('setDeviceConnected', false);
            }
        },
    },
});