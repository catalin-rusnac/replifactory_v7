<template>
  <div v-if="currentExperiment.parameters">
    <div class="container-wrapper">
      <div class="tables-container">
        <div class="table-wrapper">
          <ControlParameters :key="controlParamsKey" />
        </div>
        <div class="table-wrapper">
          <GrowthParameters />
        </div>
        <div class="table-wrapper">
          <DilutionControls @settings-updated="refreshControlParams" />
        </div>
      </div>
    </div>

    <div id="SimulationPlot">
    <div class="controls-container">
      <v-btn
        color="info"
        class="control-button"
        height="60px"
        @click="plotSelectedVial"
        style="align-self: flex-start;"
        :disabled="isPlotting"
      >
        <template v-if="isPlotting">
          <v-progress-circular
            indeterminate
            color="white"
            size="24"
            class="mr-2"
          />
          Calculating...
        </template>
        <template v-else>
          Plot Predicted Experiment
        </template>
      </v-btn>
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

<script setup>
import { ref, computed } from 'vue';
import { useExperimentStore } from '@/client/stores/experiment';
import ControlParameters from './ControlParameters.vue';
import GrowthParameters from './GrowthParameters.vue';
import DilutionControls from './DilutionControls.vue';
import VialPlot from "@/client/components/ExperimentTab/VialPlot.vue";

const experimentStore = useExperimentStore();

const vials = Array.from({ length: 7 }, (_, i) => i + 1); // Example: 7 vials
const selectedVial = ref(1);
const controlParamsKey = ref(0);

const currentExperiment = computed(() => experimentStore.currentExperiment || {});
const simulation_data = computed(() => experimentStore.simulation_data || {});

const isPlotting = ref(false);

function refreshControlParams() {
  controlParamsKey.value = Date.now();
}

async function plotSelectedVial() {
  if (!currentExperiment.value || !selectedVial.value) {
    return;
  }
  isPlotting.value = true;
  try {
    if (experimentStore.fetchSimulationPlot) {
      await experimentStore.fetchSimulationPlot(selectedVial.value);
    }
  } finally {
    isPlotting.value = false;
  }
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
  max-height: 100%;
}

.dilution-controls {
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin-top: 20px;
  padding: 0 20px;
}

.dilution-button {
  width: 130px; /* Match the column width from TableComponent */
}
</style>
