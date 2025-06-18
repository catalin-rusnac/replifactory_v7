<template>
  <div v-if="currentExperiment.parameters">
    <div class="preconfigured-wrapper">
      <DilutionControls @settings-updated="refreshControlParams" />
    </div>
    
    <div class="container-wrapper">
      <div class="tables-container">
        <div class="table-wrapper">
          <ControlParameters :key="controlParamsKey" @refresh-table="refreshControlParams" />
        </div>
        <div class="table-wrapper">
          <GrowthParameters :key="growthParamsKey" />
        </div>
      </div>
    </div>



    <div class="simulation-wrapper">
      <ExperimentSimulation />
    </div>

    <div id="SimulationPlot">
      <div class="plot-buttons-container">
        <h3>Plot Predicted Experiment</h3>
        <div class="vial-buttons-row">
          <v-btn
            v-for="vial in vials"
            :key="vial"
            color="info"
            class="vial-plot-button"
            @click="plotVial(vial)"
            :disabled="isPlotting || !!simulationHoursError"
          >
            <template v-if="isPlotting && selectedVial === vial">
              <v-progress-circular
                indeterminate
                color="white"
                size="20"
                class="mr-2"
              />
            </template>
            Vial {{ vial }}
          </v-btn>
        </div>
      </div>
      <div v-if="selectedVial" class="plot-area">
        <div v-if="plotError" class="error-panel">
          <v-icon color="error" size="large" class="error-icon">mdi-alert-circle</v-icon>
          <div class="error-content">
            <h4>Plot Error</h4>
            <p>{{ plotError }}</p>
            <v-btn 
              color="error" 
              variant="outlined" 
              @click="plotVial(selectedVial)"
              :disabled="isPlotting || !!simulationHoursError"
            >
              <v-icon left>mdi-refresh</v-icon>
              Retry
            </v-btn>
          </div>
        </div>
        <div v-else class="plot-wrapper">
          <VialPlot :vial="selectedVial" :data="simulation_data[selectedVial]" />
          <div v-if="isPlotting" class="plot-loading-overlay">
            <div class="loading-content">
              <v-progress-circular
                indeterminate
                color="primary"
                size="64"
              ></v-progress-circular>
              <span class="loading-text">Simulating Vial {{ selectedVial }}...</span>
            </div>
          </div>
        </div>
      </div>
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
import ExperimentSimulation from "@/client/components/ExperimentTab/ExperimentSimulation.vue";

const experimentStore = useExperimentStore();

const vials = Array.from({ length: 7 }, (_, i) => i + 1); // Example: 7 vials
const selectedVial = ref(1);
const controlParamsKey = ref(0);
const growthParamsKey = ref(0);

const currentExperiment = computed(() => experimentStore.currentExperiment || {});
const simulation_data = computed(() => experimentStore.simulation_data || {});

const isPlotting = ref(false);
const plotError = ref(null);

// Validation for simulation hours
const simulationHoursError = computed(() => {
  const hours = experimentStore.simulationHours
  if (hours < 1) {
    return 'Simulation hours must be at least 1'
  }
  if (hours > 240) {
    return 'Simulation hours cannot exceed 240 (10 days)'
  }
  return null
})

function refreshControlParams() {
  controlParamsKey.value = Date.now();
  growthParamsKey.value = Date.now();
}

async function plotVial(vial) {
  if (!currentExperiment.value) {
    return;
  }
  
  // Check for validation errors
  if (simulationHoursError.value) {
    plotError.value = `Invalid simulation hours: ${simulationHoursError.value}`;
    return;
  }
  
  selectedVial.value = vial;
  isPlotting.value = true;
  plotError.value = null;
  
  // Clear any previous error message
  experimentStore.errorMessage = null;
  
  try {
    if (experimentStore.fetchSimulationPlot) {
      await experimentStore.fetchSimulationPlot(vial, experimentStore.simulationHours);
      
      // Check if there was an error in the store
      if (experimentStore.errorMessage) {
        plotError.value = `Simulation Error. Please adjust parameters\n\n${experimentStore.errorMessage}`;
        return;
      }
      
      // Check if we actually got data
      if (!simulation_data.value[vial] || simulation_data.value[vial].length === 0) {
        plotError.value = "Simulation Error. Please adjust parameters\n\nNo data received";
        return;
      }
    }
  } catch (error) {
    console.error('Error plotting vial:', error);
    plotError.value = `Simulation Error. Please adjust parameters\n\n${error.message || 'Unknown error'}`;
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

.plot-buttons-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.plot-buttons-container h3 {
  color: #fff;
  margin-bottom: 16px;
  font-size: 1.2em;
}

.vial-buttons-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.vial-plot-button {
  min-width: 120px;
  height: 40px;
}

.no-experiment-selected {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.preconfigured-wrapper {
  display: flex;
  justify-content: center;
  width: 100%;
  margin-top: 10px;
  margin-bottom: 20px;
  min-width: 924px;
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

.simulation-wrapper {
  display: flex;
  justify-content: center;
  width: 100%;
  margin-top: 30px;
  min-width: 924px;
}

.plot-area {
  width: 100%;
  min-height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.plot-wrapper {
  position: relative;
  display: inline-block;
}

.plot-wrapper :deep(.js-plotly-plot) {
  position: relative;
}

.plot-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(45, 45, 45, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 40px;
  background: rgba(45, 45, 45, 0.9);
  border-radius: 8px;
}

.loading-text {
  color: #fff;
  font-size: 1.1em;
}

.error-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(244, 67, 54, 0.1);
  border: 2px solid #f44336;
  border-radius: 8px;
  padding: 40px;
  min-height: 300px;
  gap: 20px;
}

.error-icon {
  flex-shrink: 0;
}

.error-content {
  text-align: left;
  color: #fff;
}

.error-content h4 {
  color: #f44336;
  margin: 0 0 12px 0;
  font-size: 1.3em;
}

.error-content p {
  margin: 0 0 20px 0;
  font-size: 14px;
  line-height: 1.2;
  white-space: pre;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  letter-spacing: 0;
  word-spacing: 0;
  tab-size: 8;
}
</style>
