<template>
  <h2>
    Culture Control Parameters
    <span 
      class="info-icon" 
      @click="toast.info('Control parameters are used to define the flow of the experiment.', { position: 'top-right', autoClose: 8000 })"
      style="cursor: pointer; margin-left: 8px; font-size: 0.8em;"
    >
      ⓘ
    </span>
  </h2>
  <TableComponent
    :key="currentExperiment.id"
    :fetchData="fetchCulturesData"
    :updateData="updateCulturesData"
    :columnHeaders="['Vial 1', 'Vial 2', 'Vial 3', 'Vial 4', 'Vial 5', 'Vial 6', 'Vial 7']"
    rowHeaderLabel="Parameter"
    :rowHeaderWidth="270"
  />
</template>

<script setup>
import { computed } from 'vue';
import { useExperimentStore } from '@/client/stores/experiment';
import TableComponent from './TableComponent.vue';
import { toast } from 'vue3-toastify';
import 'vue3-toastify/dist/index.css';
import { useDialog } from '@/client/composables/useDialog';

const emit = defineEmits(['refresh-table']);
const experimentStore = useExperimentStore();
const currentExperiment = computed(() => experimentStore.currentExperiment || {});

function fetchCulturesData() {
  const cultures = currentExperiment.value.parameters.cultures;
  if (!cultures) return { data: [], keys: [] };
  const keys = Object.keys(cultures[1] || {});
  const customOrder = [
    'name', 'description',
    'volume_vial',
    'pump1_stock_drug_concentration',
    'pump2_stock_drug_concentration',
    'dose_initialization',
    'dilution_factor',
    'od_dilution_threshold',
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
}

async function updateStockConcentration(newConcentration) {
  console.log('updateStockConcentration called with value:', newConcentration)
  const params = { ...currentExperiment.value.parameters }
  const oldValue = params.stock_concentration_drug
  console.log('Current stock concentration:', oldValue, 'New concentration:', newConcentration)
  
  // Only update if value actually changed
  if (oldValue !== newConcentration) {
    params.stock_concentration_drug = newConcentration
    // Update pump2_stock_drug_concentration for all cultures to match
    for (let vial = 1; vial <= 7; vial++) {
      if (params.cultures[vial]) {
        params.cultures[vial].pump2_stock_drug_concentration = newConcentration
      }
    }
    
    try {
      await experimentStore.updateCurrentExperimentParameters(params)
      console.log('Stock concentration and vial concentrations updated successfully')
      
      // Get units with fallback
      const units = params.concentration_units || 'units'
      toast.success(`Stock concentration updated from ${oldValue} to ${newConcentration} ${units}. All vial concentrations synchronized.`)
      
      // Trigger table refresh
      emit('refresh-table')
    } catch (error) {
      console.error('Failed to update stock concentration:', error)
      toast.error('Failed to update stock concentration')
    }
  }
}

async function updateCulturesData(data) {
  const { keys: sortedKeys } = fetchCulturesData();
  const columnNames = Object.keys(currentExperiment.value.parameters.cultures);

  // Log the data being updated
  console.log('Updating cells with data:', {
    sortedKeys,
    columnNames,
    data
  });

  // Reconstruct the cultures object
  const newParameters = { ...currentExperiment.value.parameters };
  let editedCells = [];
  
  for (let v = 0; v < columnNames.length; v++) {
    for (let r = 0; r < sortedKeys.length; r++) {
      const oldValue = newParameters.cultures[columnNames[v]][sortedKeys[r]];
      const newValue = data[r][v];
      
      // Log each cell change
      if (oldValue !== newValue) {
        console.log(`Cell edited:`, {
          vial: columnNames[v],
          parameter: sortedKeys[r],
          oldValue,
          newValue
        });
        
        editedCells.push({
          vial: columnNames[v],
          parameter: sortedKeys[r],
          oldValue,
          newValue
        });
      }
      
      newParameters.cultures[columnNames[v]][sortedKeys[r]] = newValue;
    }
  }

  // Show toast for edited cells
  if (editedCells.length > 0) {
    const message = editedCells.map(cell => 
      `Vial ${cell.vial}: ${cell.parameter} changed from ${cell.oldValue} to ${cell.newValue}`
    ).join('\n');
    
    toast.info(message, {
      position: "top-right",
      autoClose: 5000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
      progress: undefined,
    });
  }

  if (experimentStore.updateCurrentExperimentParameters) {
    try {
      await experimentStore.updateCurrentExperimentParameters(newParameters);
      
      // After update, check if pump2_stock_drug_concentration matches stock_concentration_drug
      const stockConcentration = Number(newParameters.stock_concentration_drug);
      const cultures = newParameters.cultures;
      let hasMismatch = false;
      let mismatchedVials = [];
      let newVialConcentration = null;
      
      for (let vial = 1; vial <= 7; vial++) {
        if (cultures[vial]) {
          const cultureConcentration = Number(cultures[vial].pump2_stock_drug_concentration);
          // Compare with a small epsilon to handle floating point precision
          if (Math.abs(cultureConcentration - stockConcentration) > 0.0001) {
            hasMismatch = true;
            mismatchedVials.push(vial);
            // Use the first mismatched vial's concentration as the new target value
            if (newVialConcentration === null) {
              newVialConcentration = cultureConcentration;
            }
          }
        }
      }
      
      if (hasMismatch && newVialConcentration !== null) {
        toast.error(`Warning: Culture pump2_stock_drug_concentration values in vials ${mismatchedVials.join(', ')} do not match the stock bottle concentration (${stockConcentration}).`, {
          position: "top-right",
          autoClose: 8000
        });
        const { openDialog } = useDialog();
        const confirmed = await openDialog({
          title: 'Update Stock Concentration',
          message: `Update stock bottle concentration from ${stockConcentration} to ${newVialConcentration}?`,
        });
        
        if (confirmed) {
          // update stock concentration to match vial concentration
          await updateStockConcentration(newVialConcentration);
        }
        
      } else {
        toast.success('Control parameters updated');
      }
    } catch (error) {
      let errorMsg = 'Failed to update parameters';
      if (error?.response?.data?.detail) {
        errorMsg += ': ' + error.response.data.detail;
      } else if (error?.message) {
        errorMsg += ': ' + error.message;
      }
      toast.error(errorMsg);
    }
  }
}
</script>
