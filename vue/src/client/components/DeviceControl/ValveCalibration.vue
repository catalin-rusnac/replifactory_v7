<!-- simple gui that opens as a new tab - like ODGuide.vue -->
<!-- 2 sliders for setting open duty cycle (around 0.03 +- 0.03) and closed duty cycle (around 0.12 +- 0.03) -->
<!-- 2 buttons for opening and closing the given valve -->
<!-- this vue component opens when user presses ctrl shift clicks a valve in the device control page -->
<!-- it should be a reddish dark gray background sayin "Warning! Valve calibration mode" -->

<!-- Valve calibration interface -->
<template>
  <div class="valve-calibration">
    <div class="warning-header">
      <v-icon color="error" size="large">warning</v-icon>
      <h2>Warning! Valve {{ valveId }} Calibration Mode</h2>
    </div>

    <div v-if="isLoading" class="loading-state">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
      <span>Loading valve data...</span>
    </div>

    <div v-else class="calibration-controls">
      <div class="slider-container">
        <div class="slider-label">
          <span>Open Duty Cycle</span>
          <span class="value">{{ openDutyCycle.toFixed(3) }}</span>
        </div>
        <v-slider
          v-model="openDutyCycle"
          :min="0.02"
          :max="0.04"
          :step="0.001"
          color="primary"
          track-color="grey"
          thumb-label
          @update:model-value="handleOpenDutyCycleChange"
          @mouseup="updateOpenDutyCycle"
        ></v-slider>
      </div>

      <div class="slider-container">
        <div class="slider-label">
          <span>Closed Duty Cycle</span>
          <span class="value">{{ closedDutyCycle.toFixed(3) }}</span>
        </div>
        <v-slider
          v-model="closedDutyCycle"
          :min="0.11"
          :max="0.13"
          :step="0.001"
          color="primary"
          track-color="grey"
          thumb-label
          @update:model-value="handleClosedDutyCycleChange"
          @mouseup="updateClosedDutyCycle"
        ></v-slider>
      </div>

      <div class="valve-controls">
        <v-btn
          color="success"
          @click="setValveState(true)"
          :loading="isOperating"
          :disabled="isOperating"
        >
          Open Valve
        </v-btn>
        <v-btn
          color="error"
          @click="setValveState(false)"
          :loading="isOperating"
          :disabled="isOperating"
        >
          Close Valve
        </v-btn>
        <v-btn
          color="primary"
          @click="resetDefaults"
        >
          Reset Defaults
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useDeviceStore } from '../../stores/device'
import { storeToRefs } from 'pinia'
import api from '@/api'
import { toast } from 'vue3-toastify'
import 'vue3-toastify/dist/index.css'

const props = defineProps({
  valveId: {
    type: Number,
    required: true
  }
})

const deviceStore = useDeviceStore()
const { valves } = storeToRefs(deviceStore)

const openDutyCycle = ref(0.03)
const closedDutyCycle = ref(0.12)
const isOperating = ref(false)
const isLoading = ref(true)

// Watch the valves state directly
watch(valves, (newValves) => {
  if (newValves) {
    // Read from the correct YAML structure
    openDutyCycle.value = newValves.duty_cycle_open?.[props.valveId] ?? 0.03
    closedDutyCycle.value = newValves.duty_cycle_closed?.[props.valveId] ?? 0.12
  }
  isLoading.value = false
}, { immediate: true })

onMounted(async () => {
  try {
    await deviceStore.fetchDeviceData()
  } catch (error) {
    console.error('Error initializing valve calibration:', error)
    isLoading.value = false
  }
})

async function setValveState(isOpen) {
  isOperating.value = true
  try {
    await deviceStore.setPartStateAction({
      devicePart: 'valves',
      partIndex: props.valveId,
      newState: isOpen ? 'open' : 'closed',
      input: {
        dutyCycle: isOpen ? openDutyCycle.value : closedDutyCycle.value
      }
    })
    // If we get here, the operation was successful
    toast.success(`Valve ${props.valveId} ${isOpen ? 'opened' : 'closed'} successfully`)
  } catch (error) {
    console.error('Error operating valve:', error)
    // Handle network errors
    if (!error.response) {
      toast.error('Server connection error. Please check if the backend server is running.')
    } else {
      // Handle API errors
      const errorMessage = error.response?.data?.message || error.message || 'Operation failed'
      toast.error(`Failed to ${isOpen ? 'open' : 'close'} valve ${props.valveId}: ${errorMessage}`)
    }
  } finally {
    isOperating.value = false
  }
}

async function updateOpenDutyCycle() {
  try {
    await api.post('/set-valve-duty-cycle-open', {
      valve: props.valveId,
      duty_cycle: openDutyCycle.value
    })
    toast.success(`Valve ${props.valveId} open duty cycle set to ${openDutyCycle.value.toFixed(3)}`)
  } catch (error) {
    console.error('Error updating open duty cycle:', error)
    toast.error(`Failed to update valve ${props.valveId} open duty cycle`)
  }
}

async function updateClosedDutyCycle() {
  try {
    await api.post('/set-valve-duty-cycle-closed', {
      valve: props.valveId,
      duty_cycle: closedDutyCycle.value
    })
    toast.success(`Valve ${props.valveId} closed duty cycle set to ${closedDutyCycle.value.toFixed(3)}`)
  } catch (error) {
    console.error('Error updating closed duty cycle:', error)
    toast.error(`Failed to update valve ${props.valveId} closed duty cycle`)
  }
}

async function resetDefaults() {
  openDutyCycle.value = 0.03
  closedDutyCycle.value = 0.12
  try {
    await Promise.all([
      updateOpenDutyCycle(),
      updateClosedDutyCycle()
    ])
    toast.success(`Valve ${props.valveId} duty cycles reset to defaults`)
  } catch (error) {
    toast.error(`Failed to reset valve ${props.valveId} duty cycles`)
  }
}

function handleOpenDutyCycleChange(value) {
  openDutyCycle.value = value
}

function handleClosedDutyCycleChange(value) {
  closedDutyCycle.value = value
}
</script>

<style scoped>
.valve-calibration {
  background-color: #2d2d2d;
  color: #fff;
  padding: 20px;
  border-radius: 8px;
  max-width: 600px;
  margin: 20px auto;
}

.warning-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 12px;
  background-color: rgba(255, 0, 0, 0.1);
  border-radius: 4px;
}

.warning-header h2 {
  margin: 0;
  color: #ff4444;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px;
}

.calibration-controls {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.slider-container {
  background-color: #363636;
  padding: 16px;
  border-radius: 4px;
}

.slider-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.value {
  font-family: monospace;
  color: #90caf9;
}

.valve-controls {
  display: flex;
  gap: 16px;
  justify-content: center;
}

:deep(.v-slider) {
  color: #90caf9;
}

:deep(.v-slider__thumb) {
  background-color: #90caf9;
}

:deep(.v-slider__track-fill) {
  background-color: #90caf9;
}
</style>
