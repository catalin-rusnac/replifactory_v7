<template>
  <div id="CulturePlot">
    <div class="control-container">
      <div class="button-row">
        <v-btn class="plot-button" color="success" @click="plotAllData" title="Plot selected vials. alt-click to select single vial">Plot Data</v-btn>
        <div class="button-container">
          <div v-for="vial in vials" :key="vial" class="button-item">
            <v-btn
              :color="selectedVials[vial] ? 'primary' : 'secondary'"
              :style="{ 'background-color': selectedVials[vial] ? '#007bff' : 'transparent' }"
              @click="toggleVial(vial, $event)"
              :id="`vial-button-${vial}`"
            >
              {{ `Vial ${vial}` }}
            </v-btn>
          </div>
        </div>
      </div>
    </div>

    <div v-for="vial in filteredVials" :key="vial">
      <VialPlot :vial="vial" :data="plot_data[vial]" />
    </div>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useExperimentStore } from '../../stores/experiment'
import { computed, onMounted } from 'vue'
import VialPlot from './VialPlot.vue'

const experimentStore = useExperimentStore()
const { currentExperiment, selectedVials, plot_data } = storeToRefs(experimentStore)

const vials = [1, 2, 3, 4, 5, 6, 7]

const filteredVials = computed(() =>
  vials.filter(vial => selectedVials.value[vial])
)

async function plotAllData() {
  if (!currentExperiment.value) return
  for (let vial of filteredVials.value) {
    await experimentStore.fetchCulturePlot(vial)
  }
}

async function toggleVial(vial, event) {
  let updatedVials
  if (event.altKey) {
    updatedVials = { [vial]: true }
  } else {
    updatedVials = { ...selectedVials.value, [vial]: !selectedVials.value[vial] }
  }
  experimentStore.setSelectedVials(updatedVials)
  if (updatedVials[vial]) {
    await experimentStore.fetchCulturePlot(vial)
  }
}

onMounted(() => {
  plotAllData()
})
</script>

<style scoped>
#CulturePlot {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
}
.control-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 800px;
  margin-bottom: 20px;
}

.button-row {
  display: flex;
  align-items: center;
}

.plot-button {
  width: fit-content;
  min-width: 120px;
  margin: 10px;
}

.button-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  width: 100%;
}

.button-item {
  margin: 5px;
}
</style>
