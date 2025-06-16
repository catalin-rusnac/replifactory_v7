<template>
  <div>
    <ExperimentSetup/>
    <ExperimentSummary v-if="hasCultures"/>
    <ExperimentChart v-if="hasCultures"/>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useExperimentStore } from '../../stores/experiment'
import ExperimentSetup from './ExperimentSetup.vue'
import ExperimentSummary from './ExperimentSummary.vue'
import ExperimentChart from './ExperimentChart.vue'
import { computed, watch } from 'vue'

const experimentStore = useExperimentStore()
const { experiments, currentExperiment, errorMessage } = storeToRefs(experimentStore)

const hasCultures = computed(() => {
  const count = Object.keys(currentExperiment.value?.parameters?.cultures || {}).length
  return count > 0
})
</script>
