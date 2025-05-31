<template>
  <div v-if="Object.keys(currentExperiment?.parameters?.growth_parameters || {}).length > 0">
    <TableComponent
      :key="currentExperiment.id"
      :fetchData="fetchCulturesData"
      :updateData="updateCulturesData"
      tableTitle="Culture Growth Parameters"
      :columnHeaders="['Vial 1', 'Vial 2', 'Vial 3', 'Vial 4', 'Vial 5', 'Vial 6', 'Vial 7']"
      rowHeaderLabel="Parameter"
      :rowHeaderWidth="270"
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
