import { defineStore } from 'pinia'
import api from '@/api'
import { toast } from 'vue3-toastify'

export const useExperimentStore = defineStore('experiment', {
  state: () => ({
    experiments: [],
    currentExperiment: null,
    selectedExperimentId: null,
    errorMessage: null,
    simulation_data: {},
    plot_data: {},
    selectedVials: {},
    ws: null,
    progressMessages: [],
  }),
  actions: {
    async fetchExperiments() {
      const response = await api.get('/experiments')
      this.experiments = response.data
    },
    async createExperiment({ name }) {
      const response = await api.post('/experiments', { name })
      await this.fetchExperiments()
      await this.selectExperiment(response.data.id)
      return response.data.id
    },
    async selectExperiment(experimentId) {
      await api.put('/experiments', { experiment_id: experimentId })
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
    async startExperiment() {
      try {
        const response = await api.post('/experiments/current/status', { status: 'running' });
        return response.data; // success
      } catch (error) {
        // error.response.data.detail is the error message from FastAPI
        throw new Error(error.response?.data?.detail || 'Failed to start experiment');
      }
    },
    async stopExperiment() {
      try {
        const response = await api.post('/experiments/current/status', { status: 'stopped' });
        return response.data;
      } catch (error) {
        throw new Error(error.response?.data?.detail || 'Failed to stop experiment');
      }
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
    },
    connectWebSocket() {
      if (this.ws) {
        console.log('WebSocket already connected');
        return;
      }
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = window.location.host;
      const wsPath = '/api/ws';
      this.ws = new WebSocket(`${wsProtocol}//${wsHost}${wsPath}`);
      this.ws.onopen = () => {
        console.log('WebSocket connected');
      };
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.message) {
            if (data.type === 'success') {
              toast(data.message, { type: 'success' });
            } else {
              toast(data.message, { type: 'info' });
            }
          }
          if (data.type === 'progress') {
            console.log(`[WS progress] ${data.message}`);
            this.progressMessages.push(data.message);
          }
        } catch (e) {
          console.log('WS message (non-JSON):', event.data);
        }
      };
      this.ws.onclose = () => {
        console.log('WebSocket closed');
        this.ws = null;
      };
      this.ws.onerror = (event) => {
        console.error('WebSocket error', event);
      };
    },
    disconnectWebSocket() {
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }
    },
  }
}) 