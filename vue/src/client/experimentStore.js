import api from '@/api';

export default {
  namespaced: true,
  state: {
    hostname: "replifactory_GUI",
    errorMessage: null,
    experiments: [],
    currentExperiment: {
      id: null,
      name: null,
      parameters: null,
      data: {},
    },
    plot_data: {1: null, 2: null, 3: null, 4: null, 5: null, 6: null, 7: null},

  },
  mutations: {
    setExperiments(state, experiments) {
      state.experiments = experiments;
    },
    setCurrentExperiment(state, experiment) {
      state.currentExperiment = experiment;
    },
    setExperimentPlotData(state, { data, vial }) {
      console.log(data,vial,"data,vial replacing current:", state.plot_data[vial])
    state.plot_data[vial] = data;
    },
    setCurrentExperimentParameters(state, parameters) {
      state.currentExperiment.parameters = parameters;
    },
  },
  actions: {
    async fetchExperiments({ commit}) {
      console.log("fetchExperiments");
      const response = await api.get('/experiments');
      commit('setExperiments', response.data);
    },
    async fetchCulturePlot({ commit, state }, vial) {
      console.log(`fetchCulturePlot for vial ${vial}`);
      if (!state.plot_data) {
        console.log('Current experiment or its plot data is not defined');
        return;
      }
      const response = await api.get(`/plot/${vial}`);
      const figure = response.data;
      commit('setExperimentPlotData', { data: JSON.parse(figure).data, vial }); // Parse the figure and extract data
    },


    async setCurrentExperimentAction({ commit, state }, experimentId) {
      console.log("setCurrentExperimentAction");
      if (experimentId !== state.currentExperiment.id) {
        const response = await api.get(`/experiments/${experimentId}`);
        commit('setCurrentExperiment', response.data);
      }
    },
    async createExperiment({ dispatch}, experimentData) {
      console.log("createExperiment");
      const response = await api.post('/experiments', experimentData);
      await dispatch('fetchExperiments');
      await dispatch('setCurrentExperimentAction', response.data.id);
      return response.data.id;
    },

    async updateExperimentParameters({ commit, state }, {parameters }) {
      console.log("updateExperimentParameters", state.currentExperiment.id, parameters);
      commit('setCurrentExperimentParameters', parameters);
      await api.put(`/experiments/${state.currentExperiment.id}/parameters`, {parameters: state.currentExperiment.parameters});
    },
    async fetchCurrentExperiment({ commit }) {
      console.log("fetchCurrentExperiment");
      const response = await api.get('/experiments/current');
      commit('setCurrentExperiment', response.data);
    },
    async reloadExperimentParameters({commit,state}) {
        const response = await api.get(`/experiments/${state.currentExperiment.id}`);
        commit('setCurrentExperiment', response.data);
    },
    async startExperiment({ dispatch }, experimentId) {
      console.log("startExperiment");
      try {
        const response = await api.put(`/experiments/${experimentId}/status`, { status: 'running' });
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
            await api.put(`/experiments/${experimentId}/status`, {status: 'running'});
        }
        await api.put(`/experiments/${experimentId}/status`, {status: 'paused'});
        dispatch('reloadExperimentParameters');
    },
    async stopExperiment({ dispatch }, experimentId) {
        await api.put(`/experiments/${experimentId}/status`, {status: 'stopped'});
        dispatch('reloadExperimentParameters');
    },

  },
};
