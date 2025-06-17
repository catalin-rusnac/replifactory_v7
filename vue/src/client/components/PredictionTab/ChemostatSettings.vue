<template>
  <div class="chemostat-settings">
    <div class="header">
      <v-icon color="info" size="large">mdi-flask</v-icon>
      <h2>Chemostat Settings for Vial {{ vialId }}</h2>
    </div>
    <div class="settings-content">
      <p class="settings-description">
        Configure the following chemostat parameters:
      </p>
      <div class="parameter-list">
        <template v-for="key in parameterOrder" :key="key">
          <div v-if="changedKeys.includes(key)" class="parameter-item">
            <span class="parameter-name">{{ key }}</span>
            <div class="parameter-values">
              <span class="parameter-value">{{ formatValue(currentValues[key]) }}</span>
              <span class="parameter-arrow">→</span>
              <input
                type="number"
                v-model.number="newValues[key]"
                class="parameter-input"
                :min="getParameterMin(key)"
                :max="getParameterMax(key)"
                @blur="newValues[key] = Number(newValues[key]).toFixed(5) * 1"
              />
            </div>
          </div>
        </template>
      </div>
      <div class="action-buttons">
        <v-btn color="primary" @click="confirmSettings">Confirm Changes</v-btn>
        <v-btn color="error" @click="$emit('close')">Cancel</v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
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

const parameterOrder = [
  'name',
  'description',
  'volume_vial',
  'pump1_stock_drug_concentration',
  'pump2_stock_drug_concentration',
  'dose_initialization',
  'dilution_factor',
  'od_dilution_threshold',
  'delay_dilution_max_hours',
  'dilution_number_first_drug_addition',
  'dose_first_drug_addition',
  'postfill'
]

const chemostatDefaults = {
  volume_vial: 12,
  pump1_stock_drug_concentration: 0,
  dose_initialization: 0,
  dilution_factor: 1.6,
  od_dilution_threshold: -1,
  delay_dilution_max_hours: 4,
  dilution_number_first_drug_addition: -1,
  dose_first_drug_addition: -1,
  dose_increase_factor: -1,
  dose_increase_amount: -1,
  delay_stress_increase_min_generations: -1,
  threshold_od_min_increase_stress: -1,
  threshold_growth_rate_increase_stress: -1,
  threshold_growth_rate_decrease_stress: -1
}

const currentValues = computed(() => {
  const params = experimentStore.currentExperiment?.parameters
  if (!params || !params.cultures || !params.cultures[props.vialId]) {
    return { ...chemostatDefaults }
  }
  return params.cultures[props.vialId]
})

const newValues = ref({ ...chemostatDefaults })

// Update newValues when currentValues changes, but preserve any user edits
const changedKeys = computed(() => {
  const current = currentValues.value;
  const proposed = newValues.value;
  return Object.keys(chemostatDefaults).filter(
    key => current[key] !== proposed[key]
  );
});

function formatValue(val) {
  if (typeof val === 'number') {
    return Number(val).toFixed(5).replace(/\.0+$/, '').replace(/(\.\d*?[1-9])0+$/, '$1');
  }
  return val;
}

function getParameterMin(key) {
  const mins = {
    volume_vial: 0,
    dose_initialization: 0,
    dilution_factor: 1,
    od_dilution_threshold: 0,
    delay_dilution_max_hours: 0,
    dilution_number_first_drug_addition: 1,
    dose_first_drug_addition: 0,
    postfill: 0
  }
  return mins[key] !== undefined ? mins[key] : null
}

function getParameterMax(key) {
  return null
}

async function confirmSettings() {
  try {
    const params = { ...experimentStore.currentExperiment.parameters }
    parameterOrder.forEach(key => {
      if (Object.prototype.hasOwnProperty.call(newValues.value, key)) {
        params.cultures[props.vialId][key] = newValues.value[key]
      }
    })
    await experimentStore.updateCurrentExperimentParameters(params)
    toast.success(`Chemostat settings updated for Vial ${props.vialId}`)
    emit('confirm')
  } catch (error) {
    console.error('Failed to update chemostat settings:', error)
    toast.error('Failed to update chemostat settings')
  }
}
</script>

<style scoped>
.chemostat-settings {
  background-color: #2d2d2d;
  color: #fff;
  padding: 20px;
  border-radius: 8px;
  max-width: 600px;
  margin: 20px auto;
}
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 12px;
  background-color: rgba(33, 150, 243, 0.1);
  border-radius: 4px;
}
.header h2 {
  margin: 0;
  color: #2196f3;
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
.parameter-arrow {
  color: #90caf9;
  font-weight: bold;
}
.parameter-input {
  width: 80px;
  background: #2d2d2d;
  border: 1px solid #444;
  border-radius: 4px;
  color: #fff;
  padding: 4px 8px;
  font-family: monospace;
}
.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 16px;
}
</style> 