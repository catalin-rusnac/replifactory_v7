import { defineStore } from 'pinia'
import api from '@/api'

export const useExperimentStore = defineStore('experiment', {
  state: () => ({
    experiments: [],
    currentExperiment: null,
    selectedExperimentId: null,
    errorMessage: null,
    simulation_data: {},
    plot_data: {},
    selectedVials: {},
  }),
  actions: {
    async fetchExperiments() {
      const response = await api.get('/experiments')
      this.experiments = response.data
    },
    async createExperiment({ name, parameters }) {
      const response = await api.post('/experiments', { name, parameters })
      await this.fetchExperiments()
      await this.selectExperiment(response.data.id)
      return response.data.id
    },
    async selectExperiment(experimentId) {
      const response = await api.put('/experiments/select', { experiment_id: experimentId })
      this.selectedExperimentId = response.data.selected_experiment_id
      await this.fetchCurrentExperiment()
    },
    async fetchCurrentExperiment() {
      const selectedIdResp = await api.get('/experiments/current')
      if (selectedIdResp.data) {
        this.currentExperiment = selectedIdResp.data
      } else {
        this.currentExperiment = null
      }
    },
    async updateExperimentStatus(status) {
      try {
        const response = await api.put('/experiments/current/status', { status })
        if (response.data.message) {
          await this.fetchCurrentExperiment()
        } else if (response.data.detail) {
          this.errorMessage = response.data.detail
        }
      } catch (error) {
        this.errorMessage = 'An error occurred while updating experiment status.'
      }
    },
    async startExperiment() {
      await this.updateExperimentStatus('running')
    },
    async stopExperiment() {
      await this.updateExperimentStatus('stopped')
    },
    setErrorMessage(message) {
      this.errorMessage = message
    },
    async fetchCurrentExperimentParameters() {
      const response = await api.get('/experiments/current/parameters')
      if (this.currentExperiment) {
        this.currentExperiment.parameters = response.data
      }
      return response.data
    },
    async updateCurrentExperimentParameters(parameters) {
      await api.put('/experiments/current/parameters', { parameters })
      await this.fetchCurrentExperiment()
    },
    async fetchCurrentGrowthParameters() {
      const response = await api.get('/experiments/current/growth_parameters')
      if (this.currentExperiment && this.currentExperiment.parameters) {
        this.currentExperiment.parameters.growth_parameters = response.data
      }
      return response.data
    },
    async updateCurrentGrowthParameters(growth_parameters) {
      await api.put('/experiments/current/growth_parameters', growth_parameters)
      await this.fetchCurrentExperiment()
    },
    async updateExperimentParameters({ parameters }) {
      await this.updateCurrentExperimentParameters(parameters)
    },
    async fetchSimulationPlot(vial) {
      try {
        const response = await api.get(`/plot/${vial}/simulation`)
        if (!this.simulation_data) this.simulation_data = {};
        this.simulation_data[vial] = response.data.data;
      } catch (error) {
        this.errorMessage = 'Failed to fetch simulation plot.';
      }
    },
    async fetchCulturePlot(vial) {
      try {
        const response = await api.get(`/plot/${vial}`);
        if (!this.plot_data) this.plot_data = {};
        this.plot_data[vial] = response.data.data;
      } catch (error) {
        this.errorMessage = 'Failed to fetch culture plot.';
      }
    },
    setSelectedVials(selectedVials) {
      this.selectedVials = selectedVials;
    },
    async plotAllData() {
      if (!this.currentExperiment) return;
      for (let vial of this.filteredVials) {
        await this.fetchCulturePlot(vial);
      }
    },
    get filteredVials() {
      if (!this.selectedVials) return [];
      return Object.keys(this.selectedVials).filter(vial => this.selectedVials[vial]);
    }
  }
}) 