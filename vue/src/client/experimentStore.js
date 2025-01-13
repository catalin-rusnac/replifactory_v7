import api from '@/api';

export default {
  namespaced: true,
  state: {
    audioContext: null, // Delay initialization
    hostname: "replifactory_GUI",
    errorMessage: null,
    experiments: [],
    currentExperiment: {
      id: null,
      name: null,
      parameters: null,
      data: {},
    },
    selectedVials: {1: true, 2: true, 3: false, 4: false, 5: false, 6: false, 7: false},
    plot_data: {1: null, 2: null, 3: null, 4: null, 5: null, 6: null, 7: null},
    simulation_data: {1: null, 2: null, 3: null, 4: null, 5: null, 6: null, 7: null},
  },
  mutations: {
    setAudioContext(state, audioContext) {
      state.audioContext = audioContext;
    },
    setSelectedVials(state, selectedVials) {
        state.selectedVials = selectedVials;
    },
    setExperiments(state, experiments) {
      state.experiments = experiments;
    },
    setCurrentExperiment(state, experiment) {
      state.currentExperiment = experiment;
    },
    setExperimentPlotData(state, { data, vial }) {
      state.plot_data[vial] = data;
    },
    setSimulationPlotData(state, { data, vial }) {
      state.simulation_data[vial] = data;
    },
    setCurrentExperimentParameters(state, parameters) {
      state.currentExperiment.parameters = parameters;
    },
  },
  actions: {
    setSelectedVials({ commit }, selectedVials) {
        commit('setSelectedVials', selectedVials);
    },
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
    async fetchSimulationPlot({ commit, state }, vial) {
      console.log(`fetchSimulationPlot for vial ${vial}`);
      if (!state.plot_data) {
        console.log('Current experiment or its plot data is not defined');
        throw new Error('Current experiment or its plot data is not defined');
      }
      // if response is error then open popup with error message
      try {
        const response = await api.get(`/plot_simulation/${vial}`);
        const figure = response.data;
        commit('setSimulationPlotData', { data: JSON.parse(figure).data, vial }); // Parse the figure and extract data
        }
        catch (error) {
          console.error(error);
          alert(error.response.data.error);
        }
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
      commit('setCurrentExperimentParameters', parameters);
      await api.put(`/experiments/current/parameters`, {parameters: state.currentExperiment.parameters});
    },

    async fetchCurrentExperiment({ commit }) {
      const response = await api.get('/experiments/current');
      commit('setCurrentExperiment', response.data);
    },
    async reloadExperimentParameters({commit}) {
        const response = await api.get(`/experiments/current`);
        commit('setCurrentExperiment', response.data);
    },
    async startExperiment({ dispatch }) {
      try {
        const response = await api.put(`/experiments/current/status`, { status: 'running' });
        if (response.data.message) {
          // Handle success response
          dispatch('reloadExperimentParameters');
          dispatch('playStartingExperimentSound');

        } else if (response.data.error) {
          // Handle error response
          console.error(response.data.error);
          this.errorMessage = response.data.error;
          dispatch('playFailureSound');
        }
      } catch (error) {
        console.error(error);
        dispatch('playFailureSound');
        this.errorMessage = "An error occurred while starting the experiment.";
      }
    },
        playFailureSound({state}) {
        const frequency = 750;  // Set the frequency higher

        const oscillator = state.audioContext.createOscillator();
        oscillator.type = 'sine';

        const gainNode = state.audioContext.createGain();
        gainNode.gain.setValueAtTime(0.1, state.audioContext.currentTime);

        oscillator.connect(gainNode);
        gainNode.connect(state.audioContext.destination);

        oscillator.frequency.setValueAtTime(frequency, state.audioContext.currentTime);

        oscillator.start();

        // Ramp down the volume to create a decaying sound effect
        gainNode.gain.exponentialRampToValueAtTime(0.001, state.audioContext.currentTime + 0.5);

        oscillator.stop(state.audioContext.currentTime + 0.5); // Stops the oscillator after 0.5 seconds

        return oscillator;
    },
      playStartingExperimentSound({ state }) {
  const frequencies = [261.63, 329.63, 392.00, 523.25]; // Frequencies for C, E, G, and C'
  const durations = [0.25, 0.25, 0.25, 0.55]; // Durations for each note (in seconds)
  const delays = [0,0.2, 0.4, 0.6]; // Start delay for each note (in seconds)

  frequencies.forEach((frequency, i) => {
    setTimeout(() => {
      const oscillator = state.audioContext.createOscillator();
      oscillator.type = 'sine';

      const gainNode = state.audioContext.createGain();
      gainNode.gain.setValueAtTime(0.1, state.audioContext.currentTime);

      oscillator.connect(gainNode);
      gainNode.connect(state.audioContext.destination);

      oscillator.frequency.setValueAtTime(frequency, state.audioContext.currentTime);

      oscillator.start();
      gainNode.gain.exponentialRampToValueAtTime(0.001, state.audioContext.currentTime + durations[i]);

      oscillator.stop(state.audioContext.currentTime + durations[i]); // Stops the oscillator after the specified duration
    }, delays[i] * 1000);
  });
},




    async pauseExperiment({ dispatch,state }, ) {
        if (state.currentExperiment.status === 'stopped') {
            await api.put(`/experiments/current/status`, {status: 'running'});
        }
        await api.put(`/experiments/current/status`, {status: 'paused'});
        dispatch('reloadExperimentParameters');
    },
    async stopExperiment({ dispatch }, ) {
        await api.put(`/experiments/current/status`, {status: 'stopped'});
        dispatch('reloadExperimentParameters');
        dispatch('playStopExperimentSound');
    },


    playStopExperimentSound({ state }) {
  const frequencies = [523.25, 392.00, 329.63, 261.63]; // Frequencies for C', G, E, and C
  const durations = [0.25, 0.25, 0.25, 0.55]; // Durations for each note (in seconds)
  const delays = [0, 0.2, 0.4, 0.6]; // Start delay for each note (in seconds)

  frequencies.forEach((frequency, i) => {
    setTimeout(() => {
      const oscillator = state.audioContext.createOscillator();
      oscillator.type = 'sine';

      const gainNode = state.audioContext.createGain();
      gainNode.gain.setValueAtTime(0.1, state.audioContext.currentTime);

      oscillator.connect(gainNode);
      gainNode.connect(state.audioContext.destination);

      oscillator.frequency.setValueAtTime(frequency, state.audioContext.currentTime);

      oscillator.start();
      gainNode.gain.exponentialRampToValueAtTime(0.001, state.audioContext.currentTime + durations[i]);

      oscillator.stop(state.audioContext.currentTime + durations[i]); // Stops the oscillator after the specified duration
    }, delays[i] * 1000);
  });
},

  },
};
