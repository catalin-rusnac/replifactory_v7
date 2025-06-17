<template>
  <h2>
    Culture Growth Parameters
    <span 
      class="info-icon" 
      @click="toast.info('Growth parameters are used to predict the growth of the culture in the simulation. They do not affect the flow of the experiment but correct values are important for the accuracy of the prediction, helping adjust control parameters.', { position: 'top-right', autoClose: 8000 })"
      style="cursor: pointer; margin-left: 8px; font-size: 0.8em;"
    >
      ⓘ
    </span>
  </h2>
  <div v-if="Object.keys(currentExperiment?.parameters?.growth_parameters || {}).length > 0">
    <TableComponent
      :key="currentExperiment.id"
      :fetchData="fetchCulturesData"
      :updateData="updateCulturesData"
      :columnHeaders="['Vial 1', 'Vial 2', 'Vial 3', 'Vial 4', 'Vial 5', 'Vial 6', 'Vial 7']"
      rowHeaderLabel="Parameter"
      :rowHeaderWidth="270"
      :rowTooltips="growthParameterTooltips"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useExperimentStore } from '@/client/stores/experiment';
import TableComponent from "../PredictionTab/TableComponent.vue";
import { toast } from 'vue3-toastify';
import 'vue3-toastify/dist/index.css';

const experimentStore = useExperimentStore();
const currentExperiment = computed(() => experimentStore.currentExperiment || {});

// Tooltip descriptions for each growth parameter
const growthParameterTooltips = {
  'initial_population': 'Initial OD of the culture at the start of the experiment',
  'doubling_time_mins': 'Time in minutes for the culture to double under optimal conditions',
  'carrying_capacity': 'Maximum OD the culture can reach under optimal conditions.',
  'mu_min': 'Minimum growth rate (death rate under stress)',
  'ic50_initial': 'Initial drug concentration that inhibits growth by 50% (IC50)',
  'ic10_ic50_ratio': 'Ratio between IC10 and IC50 concentrations. Lower values indicate steeper dose-response curves.',
  'dose_effective_slope_width_mins': 'Describes how fast the drug can stress the culture.',
  'time_lag_drug_effect_mins': 'Delay in minutes between drug addition and onset of growth inhibition effects.',
  'adaptation_rate_max': 'Maximum rate at which the culture can adapt to stress - the model assumes it is at IC50.',
  'adaptation_rate_ic10_ic50_ratio': 'Ratio of adaptation rate at IC10 to IC50. Higher values indicate more similar adaptation at optimum and suboptimum stress conditions.', 
  'effective_dose': 'Calculated effective drug dose based on current conditions and adaptation state.'
};

function fetchCulturesData() {
  const cultures = currentExperiment.value.parameters.growth_parameters;
  if (!cultures) return { data: [], keys: [] };
  const keys = Object.keys(cultures[1] || {});
  const customOrder = [
    'initial_population',
    'doubling_time_mins',
    'carrying_capacity',
    'mu_min',
    'ic50_initial',
    'ic10_ic50_ratio',
    'dose_effective_slope_width_mins',
    'time_lag_drug_effect_mins',
    'adaptation_rate_max',
    'adaptation_rate_ic10_ic50_ratio',
    'drug_concentration',
    'effective_dose'
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
}

async function updateCulturesData(data) {
  const { keys: sortedKeys } = fetchCulturesData();
  const columnNames = Object.keys(currentExperiment.value.parameters.growth_parameters);

  // Reconstruct the growth_parameters object
  const newGrowthParameters = {};
  for (let v = 0; v < columnNames.length; v++) {
    newGrowthParameters[columnNames[v]] = {};
    for (let r = 0; r < sortedKeys.length; r++) {
      newGrowthParameters[columnNames[v]][sortedKeys[r]] = data[r][v];
    }
  }

  if (experimentStore.updateCurrentGrowthParameters) {
    try {
      await experimentStore.updateCurrentGrowthParameters(newGrowthParameters);
      toast('Growth parameters updated', { type: 'success' });
    } catch (error) {
      toast('Failed to update growth parameters', { type: 'error' });
    }
  }
}
</script>

<style scoped>
</style>
