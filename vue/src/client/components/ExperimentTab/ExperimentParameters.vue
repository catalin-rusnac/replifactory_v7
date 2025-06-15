<template>
  <div class="experiment-parameters">
    <div class="stock-parameters">
      <template v-for="(value, key) in currentExperiment.parameters" :key="key">
        <v-text-field
          v-if="key !== 'cultures' && key !== 'growth_parameters'"
          class="stock-parameter-field"
          :label="`${key}`"
          :model-value="currentExperiment.parameters[key]"
          :readonly="currentExperiment.status === 'running'"
          :min="0"
          type="number"
          @update:model-value="(val) => handleInputChange(key, val)"
          @blur="handleInputCommit(key)"
          @keyup.enter="handleInputCommit(key)"
        ></v-text-field>
      </template>
<!--      TODO: arrange pump order-->
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useExperimentStore } from '@/client/stores/experiment'
import { toast } from 'vue3-toastify';

const experimentStore = useExperimentStore()
const currentExperiment = computed(() => experimentStore.currentExperiment || {})
const pendingChanges = ref({})
console.log(currentExperiment.parameters)
function handleInputChange(key, value) {
  pendingChanges.value[key] = value
}

async function handleInputCommit(key) {
  const newValue = pendingChanges.value[key]
  const currentValue = currentExperiment.value.parameters[key]

  console.log('Input commit:', {
    key,
    newValue,
    currentValue,
    type: typeof newValue,
    currentType: typeof currentValue
  })

  // Convert both values to numbers for comparison if they are numeric
  const parsedNewValue = !isNaN(newValue) ? Number(newValue) : newValue
  const parsedCurrentValue = !isNaN(currentValue) ? Number(currentValue) : currentValue

  if (newValue !== '' && newValue !== null && newValue !== undefined && parsedNewValue !== parsedCurrentValue) {
    currentExperiment.value.parameters[key] = parsedNewValue
    try {
      await experimentStore.updateCurrentExperimentParameters(currentExperiment.value.parameters)
      toast('Parameter updated', { type: 'success' })
    } catch (e) {
      toast('Failed to update parameter', { type: 'error' })
    }
  }
  // Clear the pending change
  delete pendingChanges.value[key]
}
</script>

<style scoped>
.experiment-parameters {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.stock-parameters {
  display: flex;
  flex-wrap: wrap; /* Allow wrapping if screen width is too small */
  gap: 10px; /* Space between the fields */
  justify-content: space-between; /* Distribute fields evenly */
  margin-top: 20px; /* Add space above the parameter fields */
}

.stock-parameter-field {
  flex: 1 1 350px; /* Set flexible basis and width */
  max-width: 350px; /* Prevent fields from growing beyond 350px */
  margin: 0; /* Remove margin; spacing is handled by gap */
}

@media (max-width: 768px) {
  .stock-parameters {
    justify-content: center; /* Center fields on smaller screens */
  }
}
</style>
