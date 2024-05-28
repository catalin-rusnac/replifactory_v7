<template>
  <div id="SimulationPlot">
    <div class="controls-container">
      <CButton color="success" @click="plotSelectedVial" class="control-button">Plot Predicted Experiment</CButton>
      <select v-model="selectedVial" class="form-select control-dropdown">
        <option v-for="vial in vials" :key="vial" :value="vial">
          Vial {{ vial }}
        </option>
      </select>
    </div>
    <div class="graph-container" v-if="selectedVial" :id="`simulation-vial-${selectedVial}`"></div>
  </div>
</template>

<script>
import Plotly from 'plotly.js';
import { mapActions, mapState } from 'vuex';
import { CButton } from "@coreui/vue";

export default {
  components: {
    CButton,
  },
  computed: {
    ...mapState('experiment', ['simulation_data', 'currentExperiment']),
  },
  data() {
    return {
      vials: Array.from({ length: 7 }, (_, i) => i + 1), // Example: 7 vials
      selectedVial: 1,
    };
  },
  methods: {
    ...mapActions('experiment', ['fetchSimulationPlot']),

    async plotSelectedVial() {
      if (!this.currentExperiment || !this.selectedVial) {
        return;
      }
      await this.fetchSimulationPlot(this.selectedVial);
      this.plotData(this.selectedVial);
    },

    plotData(vial) {
      const data = this.simulation_data[vial] || [];

      const layout = {
        title: `Simulation Vial ${vial}`,
        xaxis: {
          title: 'Time',
        },
        yaxis: {
          title: 'Optical Density',
          automargin: true,
        },
        yaxis2: {
          title: 'Generation',
          overlaying: 'y',
          side: 'right',
          automargin: true,
        },
        yaxis3: {
          title: 'Concentration',
          overlaying: 'y',
          side: 'right',
          position: 0.92,
          automargin: true,
        },
        yaxis4: {
          title: 'Growth Rate',
          overlaying: 'y',
          side: 'left',
          position: 0.08,
          automargin: true,
        },
        yaxis5: {
          title: 'RPM',
          overlaying: 'y',
          side: 'right',
          position: 0.1,
          automargin: true,
        },
      };

      const graphDiv = document.getElementById(`simulation-vial-${vial}`);
      if (graphDiv) {
        Plotly.react(`simulation-vial-${vial}`, data, layout);
      }
    },
  },
}
</script>

<style scoped>
#SimulationPlot {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.controls-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.control-button,
.control-dropdown {
  margin: 0 10px;
}

.graph-container {
  width: 90vw;
  height: 80vh;
  display: flex;
  justify-content: center;
  flex-direction: column;
  align-items: center;
}

.form-select {
  width: 100px;
}
</style>
