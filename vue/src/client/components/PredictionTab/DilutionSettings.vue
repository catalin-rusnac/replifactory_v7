<template>
  <div class="dilution-settings">
    <div class="warning-header">
      <v-icon color="warning" size="large">warning</v-icon>
      <h2>Dilution Settings for Vial {{ vialId }}</h2>
    </div>

    <div class="settings-content">
      <p class="settings-description">
        This will modify the following parameters:
      </p>
      
      <div class="parameter-list">
        <div class="parameter-item">
          <span class="parameter-name">OD Dilution Threshold</span>
          <div class="parameter-values">
            <span class="parameter-value">{{ currentValues.od_dilution_threshold }}</span>
            <span class="parameter-arrow">→</span>
            <span class="parameter-value new">-1</span>
          </div>
        </div>
        <div class="parameter-item">
          <span class="parameter-name">Delay Dilution Max Hours</span>
          <div class="parameter-values">
            <span class="parameter-value">{{ currentValues.delay_dilution_max_hours }}</span>
            <span class="parameter-arrow">→</span>
            <span class="parameter-value new">-1</span>
          </div>
        </div>
        <div class="parameter-item">
          <span class="parameter-name">Dose Initialization</span>
          <div class="parameter-values">
            <span class="parameter-value">{{ currentValues.dose_initialization }}</span>
            <span class="parameter-arrow">→</span>
            <span class="parameter-value new">-1</span>
          </div>
        </div>
      </div>

      <div class="action-buttons">
        <v-btn
          color="primary"
          @click="confirmSettings"
        >
          Confirm Changes
        </v-btn>
        <v-btn
          color="error"
          @click="$emit('close')"
        >
          Cancel
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useExperimentStore } from '@/client/stores/experiment'
import { toast } from 'vue3-toastify'

const props = defineProps({
  vialId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['close', 'confirm'])
const experimentStore = useExperimentStore()

const currentValues = computed(() => {
  const params = experimentStore.currentExperiment?.parameters
  if (!params || !params.cultures || !params.cultures[props.vialId]) {
    return {
      od_dilution_threshold: 'N/A',
      delay_dilution_max_hours: 'N/A',
      dose_initialization: 'N/A'
    }
  }
  return params.cultures[props.vialId]
})

async function confirmSettings() {
  try {
    const params = { ...experimentStore.currentExperiment.parameters }
    
    // Set parameters to disable dilutions
    params.cultures[props.vialId] = {
      ...params.cultures[props.vialId],
      od_dilution_threshold: -1,  // Disable OD triggered dilution
      delay_dilution_max_hours: -1,  // Disable time triggered dilution
      dose_initialization: -1  // Disable initial dose
    }

    await experimentStore.updateCurrentExperimentParameters(params)
    toast.success(`Dilutions disabled for Vial ${props.vialId}`)
    emit('confirm')
  } catch (error) {
    console.error('Failed to update dilution settings:', error)
    toast.error('Failed to update dilution settings')
  }
}
</script>

<style scoped>
.dilution-settings {
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
  background-color: rgba(255, 152, 0, 0.1);
  border-radius: 4px;
}

.warning-header h2 {
  margin: 0;
  color: #ff9800;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-description {
  font-size: 1.1em;
  color: #e0e0e0;
}

.parameter-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background-color: #363636;
  padding: 16px;
  border-radius: 4px;
}

.parameter-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  border-bottom: 1px solid #444;
}

.parameter-item:last-child {
  border-bottom: none;
}

.parameter-name {
  color: #90caf9;
  font-weight: 500;
}

.parameter-values {
  display: flex;
  align-items: center;
  gap: 8px;
}

.parameter-value {
  font-family: monospace;
  color: #fff;
}

.parameter-value.new {
  color: #ff9800;
}

.parameter-arrow {
  color: #90caf9;
  font-weight: bold;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 16px;
}
</style> 