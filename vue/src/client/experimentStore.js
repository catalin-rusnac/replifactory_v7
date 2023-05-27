import Vue from 'vue';
import axios from 'axios';

let baseURL = window.location.origin + '/flask';

if (process.env.NODE_ENV === 'development') {
    baseURL = 'http://localhost:5000';
}

const flaskAxios = axios.create({
  baseURL: baseURL
});

export default {
  namespaced: true,
  state: {
    experiments: [],
    currentExperiment: null,
    experimentStatus: {},
  },
  mutations: {
    SET_EXPERIMENTS(state, experiments) {
      state.experiments = experiments;
    },
    SET_CURRENT_EXPERIMENT(state, experiment) {
      console.log('SET_CURRENT_EXPERIMENT called with', experiment);
      state.currentExperiment = experiment;
    },
    SET_EXPERIMENT_STATUS(state, { id, status }) {
      Vue.set(state.experimentStatus, id, status);
    },
  },
  actions: {
    resetCurrentExperiment({ commit }) {
      commit('SET_CURRENT_EXPERIMENT', null);
    },
    async fetchExperiments({ commit }) {
      const response = await flaskAxios.get('/experiments');
      commit('SET_EXPERIMENTS', response.data);
    },
    async setCurrentExperiment({ commit }, experimentId) {
      console.log('setCurrentExperiment called with', experimentId);

      if (experimentId !== null) {
        const response = await flaskAxios.get(`/experiments/${experimentId}`);
        console.log(response.data, 'experiment data');
        commit('SET_CURRENT_EXPERIMENT', response.data);
      } else {
        commit('SET_CURRENT_EXPERIMENT', null);
      }
    },
    async createExperiment({ dispatch }, experimentData) {
      const response = await flaskAxios.post('/experiments', experimentData);
      dispatch('fetchExperiments');
      return response.data.id;
    },
    async updateExperimentStatus({ commit, dispatch }, { id, status }) {
      await flaskAxios.put(`/experiments/${id}/status`, { status });
      commit('SET_EXPERIMENT_STATUS', { id, status });
      dispatch('fetchExperiments');
    },
    async fetchExperimentStatus({ commit }, id) {
      const response = await flaskAxios.get(`/experiments/${id}/status`);
      commit('SET_EXPERIMENT_STATUS', { id, status: response.data.status });
    },
  },
  getters: {
    selectedExperimentParameters: state => state.currentExperiment ? state.currentExperiment.parameters : null,
    currentExperimentStatus: state => (state.currentExperiment && state.experimentStatus[state.currentExperiment.id]) || null,
  }
};
