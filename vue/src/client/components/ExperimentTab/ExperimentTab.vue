<template>
  <div>
    <ExperimentSetup/>
    <ExperimentChart v-if="hasCultures"/>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useExperimentStore } from '../../stores/experiment'
import ExperimentSetup from './ExperimentSetup.vue'
import ExperimentChart from './ExperimentChart.vue'
import { computed, watch } from 'vue'

const experimentStore = useExperimentStore()
const { experiments, currentExperiment, errorMessage } = storeToRefs(experimentStore)

const hasCultures = computed(() => {
  const count = Object.keys(currentExperiment.value?.parameters?.cultures || {}).length
  console.log('hasCultures:', count, currentExperiment.value?.parameters?.cultures)
  return count > 0
})
</script>
