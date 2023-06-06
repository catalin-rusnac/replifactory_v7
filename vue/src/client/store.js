import Vue from 'vue';
import Vuex from 'vuex';
import device from './deviceStore.js';
import experiment from './experimentStore.js';

Vue.use(Vuex);

import axios from 'axios';

let baseURL = window.location.origin + '/flask';

if (process.env.NODE_ENV === 'development') {
  baseURL = 'http://localhost:5000';
}

const flaskAxios = axios.create({
  baseURL: baseURL
});

export default new Vuex.Store({
  state:{deviceConnected: false,
  deviceControlEnabled: true,
  experimentRunning: null,
  hostname: "replifactory_GUI",
  },
  modules: {
    device,
    experiment,
  },
    mutations: {
        setExperiments(state, experiments) {
            state.experiments = experiments;
            },
        setDeviceConnected(state, value) {
            state.deviceConnected = value;
        },
        setHostname(state, hostname) {
            state.hostname = hostname;
        }
        },
  actions: {
      async fetchHostname({ commit }) {
        const response = await flaskAxios.get('/hostname');
        commit('setHostname', response.data.hostname);
    },
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