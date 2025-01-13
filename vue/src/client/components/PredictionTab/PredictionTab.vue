<template>
  <div v-if="currentExperiment.parameters">
    <div class="container-wrapper">
      <div class="tables-container">
        <div class="table-wrapper">
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
        </div>
        <div class="table-wrapper">
          <GrowthParameters class="growth-parameters" />
        </div>
      </div>
    </div>

    <div id="SimulationPlot">
    <div class="controls-container">
      <v-btn color="info" class="control-button" height="60px" @click="plotSelectedVial" style="align-self: flex-start;">Plot Predicted Experiment</v-btn>
      <v-select
        v-model="selectedVial"
        :items="vials"
        class="control-dropdown"
        label="Vial"
        width="70px"
        style="align-self: flex-start;"
      ></v-select>
    </div>
      <VialPlot v-if="selectedVial" :vial="selectedVial" :data="simulation_data[selectedVial]" />
    </div>
  </div>
  <div v-else class="no-experiment-selected">
    <p>No experiment selected</p>
  </div>
</template>


<script>
import { mapActions, mapState } from 'vuex';
import TableComponent from "@/client/components/PredictionTab/TableComponent.vue";
import GrowthParameters from "./GrowthParameters.vue";
import VialPlot from "@/client/components/ExperimentTab/VialPlot.vue";

export default {
  components: {
    GrowthParameters,
    TableComponent,
    VialPlot,
  },
  data() {
    return {
      vials: Array.from({ length: 7 }, (_, i) => i + 1), // Example: 7 vials
      selectedVial: 1,
      errorMessage: 'This is a test error message.', // Example error message
    };
  },
  computed: {
    ...mapState('experiment', ['simulation_data', 'currentExperiment']),
  },
  methods: {
    ...mapActions('experiment', ['fetchSimulationPlot', 'updateExperimentParameters']),
    fetchCulturesData() {
      const cultures = this.currentExperiment.parameters.cultures;
      const keys = Object.keys(cultures[1]);
      const customOrder = [
        'name', 'description',
        'volume_vial',
        'pump1_stock_drug_concentration',
        'pump2_stock_drug_concentration', // Setup parameters
        'dose_initialization',
        'dilution_factor',
        'od_dilution_threshold', // Initialization parameters
        'delay_dilution_max_hours',
        'dilution_number_first_drug_addition',
        'dose_first_drug_addition',
        'dose_increase_factor',
        'dose_increase_amount',
        'delay_stress_increase_min_generations',
        'threshold_od_min_increase_stress',
        'threshold_growth_rate_increase_stress',
        'threshold_growth_rate_decrease_stress',
      ];

      const sortKeys = (keys) => {
        const customOrderSet = new Set(customOrder);
        const customOrderedKeys = customOrder.filter(key => keys.includes(key));
        const remainingKeys = keys.filter(key => !customOrderSet.has(key)).sort();
        return [...customOrderedKeys, ...remainingKeys];
      };

      const sortedKeys = sortKeys(keys);
      const sortedData = sortedKeys.map(key => Object.keys(cultures).map(vial => cultures[vial][key]));

      return { data: sortedData, keys: sortedKeys };
    },
    async updateCulturesData(data) {
      const sortedKeys = this.fetchCulturesData().keys;
      const columnNames = Object.keys(this.currentExperiment.parameters.cultures);
      const rowNames = sortedKeys;

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
    },
  },
};
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

.no-experiment-selected {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
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
  justify-content: center;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
}

.control-parameters,
.growth-parameters {
  flex: 1;
  min-width: 724px;
}
</style>
