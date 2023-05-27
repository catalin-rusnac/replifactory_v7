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
    currentExperiment: {
      id: null,
      name: null,
      parameters: null,
      data: null,
    },
  },
  mutations: {
    setExperiments(state, experiments) {
      state.experiments = experiments;
    },
    setCurrentExperiment(state, experiment) {
      state.currentExperiment = experiment;
    },
    setExperimentData(state, data) {
      state.currentExperiment.data = data;
    },
  },
  actions: {
    async fetchExperiments({ commit, dispatch}) {
      const response = await flaskAxios.get('/experiments');
      commit('setExperiments', response.data);
      console.log("dispatching fetchCurrentExperiment");
      dispatch('fetchCurrentExperiment')
    },
    async setCurrentExperimentAction({ commit }, experimentId) {
      if (experimentId != null) {
        const response = await flaskAxios.get(`/experiments/${experimentId}`);
        commit('setCurrentExperiment', response.data);
      }
    },
    async createExperiment({ dispatch }, experimentData) {
      const response = await flaskAxios.post('/experiments', experimentData);
      dispatch('fetchExperiments');
      return response.data.id;
    },
    async fetchExperimentData({ commit }, experimentId) {
      const response = await flaskAxios.get(`/experiments/${experimentId}/data`);
      commit('setExperimentData', response.data);
    },
    async fetchCurrentExperiment({ dispatch }) {
      const response = await flaskAxios.get('/experiments/current');
      dispatch('setCurrentExperimentAction', response.data.id);
      console.log("dispatched setCurrentExperimentAction", response.data.id);
    }

  },
};
