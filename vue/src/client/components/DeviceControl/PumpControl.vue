<template>
  <div class="pump-controls" v-if="pumps && pumps.states">
    <div class="pump" v-for="i in [1,2,4]" :key="i">
      <v-btn
        class="pump-button"
        :class="{ 'stop-button': pumps.states[i] === 'running' }"
        @click="handlePumpClick(i)"
      >
        <v-progress-circular
          v-if="pumps.states[i] === 'running'"
          indeterminate
          color="white"
          class="spinner-custom"
          size="64"
        ></v-progress-circular>
        <span v-else>{{ pump_names[i] }}<br>pump</span>
      </v-btn>

      <div class="pump-input">
        <v-text-field
          label="Volume (mL)"
          type="number"
          dense
          v-model="volume[i]"
          @update:modelValue="onVolumeInput($event, i)"
        ></v-text-field>

        <v-text-field
          v-if="calibrationModeEnabled"
          label="Rotations"
          type="number"
          dense
          v-model="rotations[i]"
          @update:modelValue="onRotationsInput($event, i)"
        ></v-text-field>

        <PumpCalibration v-if="calibrationModeEnabled" :pumpId="i" />
      </div>
    </div>
  </div>
  <div v-else>
    Loading pump data...
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useDeviceStore } from '../../stores/device'
import PumpCalibration from '@/client/components/DeviceControl/PumpCalibration.vue'
import { onMounted, reactive, watch, ref } from 'vue'

const deviceStore = useDeviceStore()
const { pumps, valves, calibrationModeEnabled } = storeToRefs(deviceStore)

// Track polling intervals to prevent multiple polling
const pollIntervals = ref({})

// Watch for pump state changes (without deep watching to avoid excessive updates)
watch(() => pumps.value?.states, (newStates) => {
  // Only log if needed for debugging - remove in production
  // console.log('PumpControl - pump states changed:', newStates)
}, { immediate: false })

const pump_names = {
  1: 'MAIN',
  2: 'DRUG',
  3: 'MISSING!!!',
  4: 'WASTE'
}
const rotations = reactive({ 1: null, 2: null, 3: null, 4: null })
const volume = reactive({ 1: null, 2: null, 3: null, 4: null })

onMounted(() => {
  if (!pumps.value) {
    deviceStore.fetchDeviceData()
  }
})

async function handlePumpClick(pumpId) {
  // Clear any existing polling for this pump
  if (pollIntervals.value[pumpId]) {
    clearInterval(pollIntervals.value[pumpId])
    delete pollIntervals.value[pumpId]
  }
  
  if (pumps.value.states[pumpId] === 'running') {
    await deviceStore.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'stopped' })
    
    // Force refresh to get real state from backend
    await deviceStore.fetchDeviceData()
    return
  }

  const isValveOpen = Object.values(valves.value.states).some((valve) => valve === 'open')
  if (!isValveOpen) {
    alert('At least one valve must be open to start the pump')
    return
  }

  const vol = parseFloat(volume[pumpId])
  if (!vol) {
    alert('Please set the volume before starting the pump')
    return
  }

  try {
    // Start polling BEFORE starting the pump so we catch state changes
    pollIntervals.value[pumpId] = setInterval(async () => {
      await deviceStore.fetchDeviceData()
      const newState = pumps.value.states[pumpId]
      
      // Stop polling when pump is no longer running (either stopped manually or finished automatically)
      if (newState !== 'running') {
        clearInterval(pollIntervals.value[pumpId])
        delete pollIntervals.value[pumpId]
      }
    }, 500) // Poll every 500ms (reduced frequency)
    
    // Start the pump (no optimistic update - let real state drive the UI)
    await deviceStore.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'running', input: { volume: vol } })
    
    // Fallback timeout to stop polling after 30 seconds
    setTimeout(() => {
      if (pollIntervals.value[pumpId]) {
        clearInterval(pollIntervals.value[pumpId])
        delete pollIntervals.value[pumpId]
        // Force refresh state
        deviceStore.fetchDeviceData()
      }
    }, 30000)
    
  } catch (error) {
    console.error(`Error starting pump ${pumpId}:`, error)
    // Reset state on error and clear polling
    pumps.value.states[pumpId] = 'stopped'
    if (pollIntervals.value[pumpId]) {
      clearInterval(pollIntervals.value[pumpId])
      delete pollIntervals.value[pumpId]
    }
  }
}

function onVolumeInput(event, pumpId) {
  volume[pumpId] = event
  const vol = parseFloat(volume[pumpId])
  if (!isNaN(vol)) {
    rotations[pumpId] = calculateRotations(vol, pumpId).toFixed(2)
  } else {
    rotations[pumpId] = ''
  }
}

function onRotationsInput(event, pumpId) {
  rotations[pumpId] = event
  const rot = parseFloat(rotations[pumpId])
  if (!isNaN(rot)) {
    volume[pumpId] = calculateVolume(rot, pumpId)
  } else {
    volume[pumpId] = ''
  }
}

function calculateRotations(volumeVal, pumpId) {
  const pumpCoefficients = pumps.value.calibration[pumpId]
  const points = Object.entries(pumpCoefficients).map(([rot, coef]) => [parseInt(rot), coef]).sort((a, b) => a[0] - b[0])

  if (volumeVal >= points[points.length - 1][0] * points[points.length - 1][1]) {
    return volumeVal / points[points.length - 1][1]
  }

  let lowerPoint = points[0]
  let upperPoint = points[points.length - 1]
  for (let i = 0; i < points.length - 1; i++) {
    if (volumeVal >= points[i][0] * points[i][1] && volumeVal <= points[i + 1][0] * points[i + 1][1]) {
      lowerPoint = points[i]
      upperPoint = points[i + 1]
      break
    }
  }

  const lowerVolume = lowerPoint[0] * lowerPoint[1]
  const upperVolume = upperPoint[0] * upperPoint[1]
  const factor = (volumeVal - lowerVolume) / (upperVolume - lowerVolume)

  const interpolatedCoefficient = lowerPoint[1] + (upperPoint[1] - lowerPoint[1]) * factor

  return volumeVal / interpolatedCoefficient
}

function calculateVolume(rotationsVal, pumpId) {
  const pumpCoefficients = pumps.value.calibration[pumpId]
  const points = Object.entries(pumpCoefficients).map(([rot, coef]) => [parseInt(rot), coef]).sort((a, b) => a[0] - b[0])

  if (rotationsVal >= points[points.length - 1][0]) {
    return (rotationsVal * points[points.length - 1][1]).toFixed(2)
  }

  let lowerPoint = points[0]
  let upperPoint = points[points.length - 1]
  for (let i = 0; i < points.length - 1; i++) {
    if (rotationsVal >= points[i][0] && rotationsVal <= points[i + 1][0]) {
      lowerPoint = points[i]
      upperPoint = points[i + 1]
      break
    }
  }

  const factor = (rotationsVal - lowerPoint[0]) / (upperPoint[0] - lowerPoint[0])
  const interpolatedCoefficient = lowerPoint[1] + (upperPoint[1] - lowerPoint[1]) * factor

  return (rotationsVal * interpolatedCoefficient).toFixed(2)
}
</script>

<style scoped>
.pump-input {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.pump-button {
  margin-bottom: 20px;
  background-color: blue !important;
  color: white !important;
  font-size: 20px;
  padding: 10px;
  width: 160px;
  height: 160px;
  text-align: center;
  border-radius: 50%;
  box-shadow: 0px 5px 10px rgba(0, 0, 0, 0.5);
}

.pump-button.stop-button {
  background-color: red !important;
  color: white !important;
}

:deep(.pump-button.stop-button .v-btn__content) {
  color: white !important;
}

:deep(.pump-button.stop-button .v-btn__overlay) {
  opacity: 0 !important;
}

.pump-controls {
  display: flex;
  flex-wrap: wrap; /* Allow wrapping if needed for narrow screens */
  flex-direction: row; /* Arrange pumps horizontally */
  justify-content: space-evenly; /* Distribute pumps evenly across the container */
  width: 100%; /* Use full width of the container */
  max-width: 800px; /* Optional: Limit maximum width */
  margin: 0 auto; /* Center container within the page */
  gap: 10px; /* Add spacing between pumps */
}


.pump {
  flex: 1 1 auto; /* Allow pumps to shrink or grow as needed */
  display: flex;
  flex-direction: column; /* Keep individual pump items aligned vertically */
  align-items: center;
  min-width: 180px; /* Ensure consistent sizing */
  max-width: 250px; /* Prevent pumps from being too wide */
  margin: 10px; /* Add spacing around each pump */
}

.spinner-custom {
  width: 48px;
  height: 48px;
}
</style>
