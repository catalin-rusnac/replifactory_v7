<!-- group 3 bottles from BottleSingle.vue - main, drug, waste. next to each other. -->
<template>
  <div class="bottle-display">
      <BottleSingle
      v-for="bottle in bottles"
      :key="bottle.name"
      :bottle-name="bottle.name"
      :total-volume="getBottleVolume(bottle.name)"
      :current-volume="getCurrentVolume(bottle.name)"
      :icon="bottle.name === 'drug' ? 'mdi-biohazard' : bottle.name === 'waste' ? 'mdi-trash-can' : ''"
      :liquid-color="getLiquidColor(bottle.name)"
      :concentration="bottle.name === 'drug' ? getConcentration() : null"
      :units="bottle.name === 'drug' ? getUnits() : null"
      @update:total-volume="(val) => updateBottleVolume(bottle.name, val)"
      @update:current-volume="(val) => updateCurrentVolume(bottle.name, val)"
      @update:concentration="(val) => updateConcentration(val)"
      @update:units="(val) => updateUnits(val)"
    />
  </div>
</template>

<script>
import { computed } from 'vue'
import { useExperimentStore } from '@/client/stores/experiment'
import BottleSingle from './BottleSingle.vue'
import { toast } from 'vue3-toastify'
import 'vue3-toastify/dist/index.css'

export default {
  name: 'BottleDisplay',
  components: {
    BottleSingle
  },
  setup() {
    const experimentStore = useExperimentStore()
    const currentExperiment = computed(() => experimentStore.currentExperiment || {})
    
    const bottles = [
      { name: 'main' },
      { name: 'drug' },
      { name: 'waste' }
    ]

    function getBottleScale(bottleName) {
      const volume = getBottleVolume(bottleName)
      const effectiveVolume = Math.min(Math.max(volume, 100), 5000)
      return Math.max(Math.pow(effectiveVolume / 1000, 1/3), 0.5)
    }

    function getMaxScale() {
      return Math.max(...bottles.map(bottle => getBottleScale(bottle.name)))
    }

    function getLiquidColor(bottleName) {
      switch(bottleName) {
        case 'main': return 'rgba(255, 215, 0, 0.7)'  // Original semi-transparent yellow
        case 'drug': return 'rgba(255, 165, 0, 0.7)'  // More reddish, slightly more opaque
        case 'waste': return 'rgba(255, 245, 0, 0.9)' // More opaque yellow
        default: return 'rgba(255, 215, 0, 0.6)'
      }
    }

    function getBottleVolume(bottleName) {
      const params = currentExperiment.value.parameters || {}
      switch(bottleName) {
        case 'main': return params.bottle_volume_main || 0
        case 'drug': return params.bottle_volume_drug || 0
        case 'waste': return params.bottle_volume_waste || 0
        default: return 0
      }
    }

    function getCurrentVolume(bottleName) {
      const params = currentExperiment.value.parameters || {}
      switch(bottleName) {
        case 'main': return params.stock_volume_main || 0
        case 'drug': return params.stock_volume_drug || 0
        case 'waste': return params.stock_volume_waste || 0
        default: return 0
      }
    }

    function getConcentration() {
      const params = currentExperiment.value.parameters || {}
      return params.stock_concentration_drug || 0
    }

    function getUnits() {
      const params = currentExperiment.value.parameters || {}
      return params.concentration_units || 'units'
    }

    async function updateBottleVolume(bottleName, value) {
      const params = { ...currentExperiment.value.parameters }
      switch(bottleName) {
        case 'main': params.bottle_volume_main = value; break
        case 'drug': params.bottle_volume_drug = value; break
        case 'waste': params.bottle_volume_waste = value; break
      }
      await experimentStore.updateCurrentExperimentParameters(params)
    }

    async function updateCurrentVolume(bottleName, value) {
      const params = { ...currentExperiment.value.parameters }
      switch(bottleName) {
        case 'main': params.stock_volume_main = value; break
        case 'drug': params.stock_volume_drug = value; break
        case 'waste': params.stock_volume_waste = value; break
      }
      await experimentStore.updateCurrentExperimentParameters(params)
    }

    async function updateConcentration(value) {
      console.log('updateConcentration called with value:', value)
      const params = { ...currentExperiment.value.parameters }
      const oldValue = params.stock_concentration_drug
      console.log('Current concentration:', oldValue, 'New concentration:', value)
      
      // Only update and show toast if value actually changed
      if (oldValue !== value) {
        params.stock_concentration_drug = value
        // Update pump2_stock_drug_concentration for all cultures
        for (let vial = 1; vial <= 7; vial++) {
          if (params.cultures[vial]) {
            params.cultures[vial].pump2_stock_drug_concentration = value
          }
        }
        await experimentStore.updateCurrentExperimentParameters(params)
        console.log('Parameters updated, showing toast')
        toast.success(`Drug concentration updated from ${oldValue} to ${value} ${params.concentration_units}`)
      }
    }

    async function updateUnits(value) {
      const params = { ...currentExperiment.value.parameters }
      params.concentration_units = value
      await experimentStore.updateCurrentExperimentParameters(params)
    }

    return {
      bottles,
      getBottleVolume,
      getCurrentVolume,
      updateBottleVolume,
      updateCurrentVolume,
      getLiquidColor,
      getConcentration,
      updateConcentration,
      getUnits,
      updateUnits,
      getMaxScale
    }
  }
}
</script>

<style scoped>
.bottle-display {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  padding: 0;
  gap: 100px;
  min-height: v-bind('280 * getMaxScale() + "px"');
}
</style>