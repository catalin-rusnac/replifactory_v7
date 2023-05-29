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
    errorMessage: null,
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
    setCurrentExperimentParameters(state, parameters) {
      state.currentExperiment.parameters = parameters;
    }
  },
  actions: {
    async fetchExperiments({ commit}) {
      console.log("fetchExperiments");
      const response = await flaskAxios.get('/experiments');
      commit('setExperiments', response.data);
    },
    async setCurrentExperimentAction({ commit, state }, experimentId) {
      console.log("setCurrentExperimentAction");
      if (experimentId !== state.currentExperiment.id) {
        const response = await flaskAxios.get(`/experiments/${experimentId}`);
        commit('setCurrentExperiment', response.data);
      }
    },
    async createExperiment({ dispatch}, experimentData) {
      console.log("createExperiment");
      const response = await flaskAxios.post('/experiments', experimentData);
      await dispatch('fetchExperiments');
      await dispatch('setCurrentExperimentAction', response.data.id);
      return response.data.id;
    },

    async fetchExperimentData({ commit }, experimentId) {
      const response = await flaskAxios.get(`/experiments/${experimentId}/data`);
      commit('setExperimentData', response.data);
    },

    async updateExperimentParameters({ commit, state }, {parameters }) {
      console.log("updateExperimentParameters", state.currentExperiment.id, parameters);
      commit('setCurrentExperimentParameters', parameters);
      await flaskAxios.put(`/experiments/${state.currentExperiment.id}/parameters`, {parameters: state.currentExperiment.parameters});
    },
    async fetchCurrentExperiment({ commit }) {
      console.log("fetchCurrentExperiment");
      const response = await flaskAxios.get('/experiments/current');
      commit('setCurrentExperiment', response.data);
    },
    async reloadExperimentParameters({commit,state}) {
        const response = await flaskAxios.get(`/experiments/${state.currentExperiment.id}`);
        commit('setCurrentExperiment', response.data);
    },
    async startExperiment({ dispatch }, experimentId) {
      console.log("startExperiment");
      try {
        const response = await flaskAxios.put(`/experiments/${experimentId}/status`, { status: 'running' });
        if (response.data.message) {
          // Handle success response
          console.log(response.data.message);
          dispatch('reloadExperimentParameters');
        } else if (response.data.error) {
          // Handle error response
          console.error(response.data.error);
          this.errorMessage = response.data.error;
        }
      } catch (error) {
        console.error(error);
        this.errorMessage = "An error occurred while starting the experiment.";
      }
    },


    async pauseExperiment({ dispatch,state }, experimentId) {
        if (state.currentExperiment.status === 'stopped') {
            await flaskAxios.put(`/experiments/${experimentId}/status`, {status: 'running'});
        }
        await flaskAxios.put(`/experiments/${experimentId}/status`, {status: 'paused'});
        dispatch('reloadExperimentParameters');
    },
    async stopExperiment({ dispatch }, experimentId) {
        await flaskAxios.put(`/experiments/${experimentId}/status`, {status: 'stopped'});
        dispatch('reloadExperimentParameters');
    },

  },
};
