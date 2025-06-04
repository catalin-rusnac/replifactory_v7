<template>
  <div class="experiment-parameters">
    <div class="stock-parameters">
      <template v-for="(value, key) in currentExperiment.parameters" :key="key">
        <v-text-field
          v-if="key !== 'cultures' && key !== 'growth_parameters'"
          class="stock-parameter-field"
          :label="`${key}`"
          v-model="currentExperiment.parameters[key]"
          :readonly="currentExperiment.status === 'running'"
          @blur="handleInputCommit(key, $event.target.value)"
          @keyup.enter="handleInputCommit(key, $event.target.value)"
        ></v-text-field>
      </template>
<!--      TODO: arrange pump order-->
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useExperimentStore } from '@/client/stores/experiment'
import { toast } from 'vue3-toastify';

const experimentStore = useExperimentStore()
const currentExperiment = computed(() => experimentStore.currentExperiment || {})

async function handleInputCommit(key, value) {
  if (value !== '' && value !== null && value !== undefined) {
    currentExperiment.value.parameters[key] = value
    try {
      await experimentStore.updateCurrentExperimentParameters(currentExperiment.value.parameters)
      toast('Parameter updated', { type: 'success' })
    } catch (e) {
      toast('Failed to update parameter', { type: 'error' })
    }
  }
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
