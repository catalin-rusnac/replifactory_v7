<template>
  <div v-if = this.currentExperiment.parameters>
    <div class="container-wrapper">
    <div class="tables-container">
      <TableComponent
          class="control-parameters"
        :key="currentExperiment.id"
        :fetchData="fetchCulturesData"
        :updateData="updateCulturesData"
        tableTitle="Culture Control Parameters"
        :columnHeaders="['Vial 1', 'Vial 2', 'Vial 3', 'Vial 4', 'Vial 5', 'Vial 6', 'Vial 7']"
        rowHeaderLabel="Parameter"
        :rowHeaderWidth="270"
      />
      <GrowthParameters class="growth-parameters" />
    </div>
    </div>

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
</div>
  <div v-else class="no-experiment-selected">
    <p>No experiment selected</p>
  </div>
</template>

<script>
import Plotly from 'plotly.js';
import { mapActions, mapState } from 'vuex';
import { CButton } from "@coreui/vue";
import TableComponent from "@/client/components/PredictionTab/TableComponent.vue";
import GrowthParameters from "./GrowthParameters.vue";

export default {
  components: {
    GrowthParameters,
    TableComponent,
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
    ...mapActions('experiment', ['fetchSimulationPlot', 'updateExperimentParameters']),
    fetchCulturesData() {
      const cultures = this.currentExperiment.parameters.cultures;
      const keys = Object.keys(cultures[1]);
      const data = keys.map(key => Object.keys(cultures).map(vial => cultures[vial][key]));

      return { data, keys };
    },
    async updateCulturesData(data) {
      const rowNames = Object.keys(this.currentExperiment.parameters.cultures[1]);
      const columnNames = Object.keys(this.currentExperiment.parameters.cultures);
      for (let v = 0; v < columnNames.length; v++) {
        for (let r = 0; r < rowNames.length; r++) {
          this.currentExperiment.parameters.cultures[columnNames[v]][rowNames[r]] = data[r][v];
        }
      }
      await this.updateExperimentParameters({
        experimentId: this.currentExperiment.id,
        parameters: this.currentExperiment.parameters,
      });
    },
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
  margin: 10px 10px;
}

.graph-container {
  width: 90vw;
  height: 80vh;
  display: flex;
  justify-content: center;
  flex-direction: column;
  align-items: center;
}

.no-experiment-selected {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.form-select {
  width: 100px;
}

.container-wrapper {
  display: flex;
  justify-content: center;
  width: 100%;
  margin-top: 10px;
  min-width: 924px;
}

.tables-container {
  display: flex;
  justify-content: center; /* Centers the split horizontally */
  align-items: flex-start; /* Aligns tables at the top */
  gap: 20px; /* Adds a 20px gap between the tables */
  max-width: 100%; /* Prevents the tables from stretching too far apart */
  flex-wrap: wrap; /* Allows tables to wrap if needed */
  min-width: 8  24px; /* Adjust this to your table's minimum width */
}

.control-parameters, .growth-parameters {
  flex: 1; /* Allows tables to grow and shrink as needed */
  min-width: 724px; /* Adjust this to your table's minimum width */
}



</style>
