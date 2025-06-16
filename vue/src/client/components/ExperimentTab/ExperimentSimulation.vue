<!-- vue component that shows simulation summary for experiment parameters in a nice table -->


<!-- @router.put("/cultures/{vial}/run-simulation")
def run_simulation(vial: int, simulation_hours: int = 48, db_session: Session = Depends(get_db)):
    """Run a simulation of the current experiment"""
    try:
        experiment = experiment_manager.experiment
        experiment.cultures[vial].run_and_save_simulation(simulation_hours=simulation_hours)
        culture = experiment.cultures[vial]
        pump1_volume_used = sum(culture.culture_growth_model.pump1_volumes)
        pump2_volume_used = sum(culture.culture_growth_model.pump2_volumes)
        waste_medium_volume_created = sum(culture.culture_growth_model.waste_medium_created)
        summary_data = {
            "final_population": culture.culture_growth_model.population[-1],
            "final_effective_growth_rate": culture.culture_growth_model.effective_growth_rates[-1][0],
            "final_dose": culture.culture_growth_model.doses[-1][0],
            "final_generation": culture.culture_growth_model.generations[-1][0],
            "pump1_volume_used": pump1_volume_used,
            "pump2_volume_used": pump2_volume_used,
            "waste_medium_volume_created": waste_medium_volume_created,
        }
        return {"message": "Simulation run", "summary_data": summary_data} -->

<template>
  <div class="experiment-simulation">
    <div class="header">
      <h3>Experiment Simulation</h3>
      <p class="description">Run a simulation to predict culture growth and resource usage for all vials</p>
    </div>

    <div class="controls">
      <v-btn
        color="primary"
        :loading="isSimulating"
        :disabled="isSimulating || !!simulationHoursError"
        @click="runSimulation"
      >
        <v-icon left>mdi-play</v-icon>
        Run Simulation
      </v-btn>
      <div class="simulation-input">
        <v-text-field
          v-model.number="simulationHours"
          type="number"
          label="Simulation hours"
          min="1"
          max="240"
          density="compact"
          :hide-details="!simulationHoursError"
          :error="!!simulationHoursError"
          :error-messages="simulationHoursError"
          class="hours-input"
          style="width: 130px;"
        ></v-text-field>
      </div>
    </div>

    <div v-if="isSimulating" class="simulation-status">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
      <span>Running simulations...</span>
    </div>

    <div v-if="simulationResults.length > 0" class="results">
      <v-card class="summary-card">
        <v-card-title>Simulation Results</v-card-title>
        <v-card-text>
          <v-table>
            <thead>
              <tr>
                <th>Metric</th>
                <th v-for="vial in 7" :key="vial">Vial {{ vial }}</th>
                <th v-if="!isSimulating && simulationResults.length === 7">Total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <v-tooltip text="Name of the vial">
                    <template v-slot:activator="{ props }">
                      <span v-bind="props">Vial Name</span>
                    </template>
                  </v-tooltip>
                </td>
                <td v-for="vial in 7" :key="vial">
                  <template v-if="loadingStates[vial]">
                    <v-progress-circular
                      indeterminate
                      size="24"
                      color="primary"
                    ></v-progress-circular>
                  </template>
                  <template v-else>
                    <template v-if="getMetricValue(vial, { key: 'name' }) === 'Error'">
                      <div class="volume-cell error">
                        <v-icon size="small" color="error" icon="mdi-close-circle"></v-icon>
                        <v-tooltip text="Adjust parameters and rerun simulation">
                          <template v-slot:activator="{ props }">
                            <span v-bind="props" class="text-error">Error</span>
                          </template>
                        </v-tooltip>
                      </div>
                    </template>
                    <template v-else>
                      {{ getVialName(vial) }}
                    </template>
                  </template>
                </td>
                <td v-if="!isSimulating && simulationResults.length === 7"></td>
              </tr>
              <tr>
                <td>
                  <v-tooltip text="Description of the vial">
                    <template v-slot:activator="{ props }">
                      <span v-bind="props">Description</span>
                    </template>
                  </v-tooltip>
                </td>
                <td v-for="vial in 7" :key="vial">
                  <template v-if="loadingStates[vial]">
                    <v-progress-circular
                      indeterminate
                      size="24"
                      color="primary"
                    ></v-progress-circular>
                  </template>
                  <template v-else>
                    <template v-if="getMetricValue(vial, { key: 'description' }) === 'Error'">
                      <div class="volume-cell error">
                        <v-icon size="small" color="error" icon="mdi-close-circle"></v-icon>
                        <v-tooltip text="Adjust parameters and rerun simulation">
                          <template v-slot:activator="{ props }">
                            <span v-bind="props" class="text-error">Error</span>
                          </template>
                        </v-tooltip>
                      </div>
                    </template>
                    <template v-else>
                      {{ getVialDescription(vial) }}
                    </template>
                  </template>
                </td>
                <td v-if="!isSimulating && simulationResults.length === 7"></td>
              </tr>
              <tr v-for="metric in metrics" :key="metric.key">
                <td>
                  <v-tooltip :text="getMetricTooltip(metric)">
                    <template v-slot:activator="{ props }">
                      <span v-bind="props">{{ metric.name }}</span>
                    </template>
                  </v-tooltip>
                </td>
                <td v-for="vial in 7" :key="vial">
                  <template v-if="loadingStates[vial]">
                    <v-progress-circular
                      indeterminate
                      size="24"
                      color="primary"
                    ></v-progress-circular>
                  </template>
                  <template v-else>
                    <template v-if="getMetricValue(vial, metric) === 'Error'">
                      <div class="volume-cell error">
                        <v-icon size="small" color="error" icon="mdi-close-circle"></v-icon>
                        <v-tooltip text="Adjust parameters and rerun simulation">
                          <template v-slot:activator="{ props }">
                            <span v-bind="props" class="text-error">Error</span>
                          </template>
                        </v-tooltip>
                      </div>
                    </template>
                    <template v-else>
                      <template v-if="metric.key === 'final_effective_growth_rate'">
                        <v-tooltip :text="getMetricTooltip(metric, vial)">
                          <template v-slot:activator="{ props }">
                            <span v-bind="props">{{ formatMetricValue(getMetricValue(vial, metric), metric) }}</span>
                          </template>
                        </v-tooltip>
                      </template>
                      <template v-else>
                        <span v-if="typeof formatMetricValue(getMetricValue(vial, metric), metric) === 'object'" 
                              :class="{ 'text-error': formatMetricValue(getMetricValue(vial, metric), metric).isError }">
                          {{ formatMetricValue(getMetricValue(vial, metric), metric).text }}
                        </span>
                        <span v-else>{{ formatMetricValue(getMetricValue(vial, metric), metric) }}</span>
                      </template>
                    </template>
                  </template>
                </td>
                <td v-if="!isSimulating && simulationResults.length === 7">
                  <template v-if="metric.key === 'pump1_volume_used'">
                    <div class="volume-cell" :class="isNaN(totalPump1Volume) ? 'error' : getTotalVolumeStatus(totalPump1Volume, stockVolumeMain)">
                      <v-tooltip :text="getTotalVolumeTooltip(totalPump1Volume, stockVolumeMain, 'Main medium')">
                        <template v-slot:activator="{ props }">
                          <div v-bind="props" class="volume-content">
                            <v-icon size="small" :color="isNaN(totalPump1Volume) ? 'error' : getTotalVolumeStatus(totalPump1Volume, stockVolumeMain)" 
                                    :icon="isNaN(totalPump1Volume) ? 'mdi-close-circle' : (getTotalVolumeStatus(totalPump1Volume, stockVolumeMain) === 'success' ? 'mdi-check-circle' : 'mdi-close-circle')"></v-icon>
                            <span :class="isNaN(totalPump1Volume) ? 'text-error' : getVolumeTextClass(totalPump1Volume, stockVolumeMain)">
                              {{ formatVolume(totalPump1Volume) }}
                            </span>
                          </div>
                        </template>
                      </v-tooltip>
                    </div>
                  </template>
                  <template v-else-if="metric.key === 'pump2_volume_used'">
                    <div class="volume-cell" :class="isNaN(totalPump2Volume) ? 'error' : getTotalVolumeStatus(totalPump2Volume, stockVolumeDrug)">
                      <v-tooltip :text="getTotalVolumeTooltip(totalPump2Volume, stockVolumeDrug, 'Drug medium')">
                        <template v-slot:activator="{ props }">
                          <div v-bind="props" class="volume-content">
                            <v-icon size="small" :color="isNaN(totalPump2Volume) ? 'error' : getTotalVolumeStatus(totalPump2Volume, stockVolumeDrug)" 
                                    :icon="isNaN(totalPump2Volume) ? 'mdi-close-circle' : (getTotalVolumeStatus(totalPump2Volume, stockVolumeDrug) === 'success' ? 'mdi-check-circle' : 'mdi-close-circle')"></v-icon>
                            <span :class="isNaN(totalPump2Volume) ? 'text-error' : getVolumeTextClass(totalPump2Volume, stockVolumeDrug)">
                              {{ formatVolume(totalPump2Volume) }}
                            </span>
                          </div>
                        </template>
                      </v-tooltip>
                    </div>
                  </template>
                  <template v-else-if="metric.key === 'waste_medium_volume_created'">
                    <div class="volume-cell" :class="isNaN(totalWasteVolume) ? 'error' : getWasteVolumeStatus(totalWasteVolume)">
                      <v-tooltip :text="getWasteVolumeTooltip(totalWasteVolume)">
                        <template v-slot:activator="{ props }">
                          <div v-bind="props" class="volume-content">
                            <v-icon size="small" :color="isNaN(totalWasteVolume) ? 'error' : getWasteVolumeStatus(totalWasteVolume)" 
                                    :icon="isNaN(totalWasteVolume) ? 'mdi-close-circle' : (getWasteVolumeStatus(totalWasteVolume) === 'success' ? 'mdi-check-circle' : 'mdi-close-circle')"></v-icon>
                            <span :class="isNaN(totalWasteVolume) ? 'text-error' : getWasteVolumeTextClass(totalWasteVolume)">
                              {{ formatVolume(totalWasteVolume) }}
                            </span>
                          </div>
                        </template>
                      </v-tooltip>
                    </div>
                  </template>
                </td>
              </tr>

            </tbody>
          </v-table>

        </v-card-text>
      </v-card>


    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDeviceStore } from '@/client/stores/device'
import { useExperimentStore } from '@/client/stores/experiment'
import { toast } from 'vue3-toastify'


const deviceStore = useDeviceStore()
const experimentStore = useExperimentStore()
const isSimulating = ref(false)
const simulationResults = ref([])
const simulationHours = computed({
  get: () => experimentStore.simulationHours,
  set: (value) => experimentStore.setSimulationHours(value)
})

// Validation for simulation hours
const simulationHoursError = computed(() => {
  const hours = simulationHours.value
  if (hours < 1) {
    return 'Simulation hours must be at least 1'
  }
  if (hours > 240) {
    return 'Simulation hours cannot exceed 240 (10 days)'
  }
  return null
})
const lastSimulatedHours = ref(24)
const loadingStates = ref({}) // Track loading state for each vial
const hasFirstResult = ref(false) // Track if first result has arrived



// Get stock volumes from experiment parameters
const stockVolumeMain = computed(() => {
  const volume = experimentStore.currentExperiment?.parameters?.stock_volume_main || 0
  return volume
})

const stockVolumeDrug = computed(() => {
  const volume = experimentStore.currentExperiment?.parameters?.stock_volume_drug || 0
  return volume
})

const wasteBottleVolume = computed(() => {
  const volume = experimentStore.currentExperiment?.parameters?.bottle_volume_waste || 0
  return volume
})

const currentWasteVolume = computed(() => {
  const volume = experimentStore.currentExperiment?.parameters?.stock_volume_waste || 0
  return volume
})

// Computed properties for total volumes
const totalPump1Volume = computed(() => {
  const total = simulationResults.value.reduce((sum, result) => sum + result.pump1_volume_used, 0)
  return total
})

const totalPump2Volume = computed(() => {
  const total = simulationResults.value.reduce((sum, result) => sum + result.pump2_volume_used, 0)
  return total
})

const totalWasteVolume = computed(() => {
  const total = simulationResults.value.reduce((sum, result) => sum + result.waste_medium_volume_created, 0)
  return total
})

// Function to check if volume exceeds stock
function isVolumeExceedingStock(volume, stockVolume) {
  return volume > stockVolume
}

// Function to check if waste volume exceeds available space
function isWasteVolumeExceedingSpace(volume) {
  const availableSpace = wasteBottleVolume.value - currentWasteVolume.value
  return volume > availableSpace
}

// Function to get total volume status
function getTotalVolumeStatus(volume, stockVolume) {
  return isVolumeExceedingStock(volume, stockVolume) ? 'danger' : 'success'
}

// Function to get waste volume status
function getWasteVolumeStatus(volume) {
  return isWasteVolumeExceedingSpace(volume) ? 'danger' : 'success'
}

// Function to get volume text class
function getVolumeTextClass(volume, stockVolume) {
  return isVolumeExceedingStock(volume, stockVolume) ? 'text-danger' : 'text-success'
}

// Function to get waste volume text class
function getWasteVolumeTextClass(volume) {
  return isWasteVolumeExceedingSpace(volume) ? 'text-danger' : 'text-success'
}

// Function to calculate doubling time from growth rate
function calculateDoublingTime(growthRate) {
  return formatNumber(Math.log(2) / growthRate * 60) + ' min'
}

// Function to run simulation
async function runSimulation() {
  if (isSimulating.value) return
  
  // Check for validation errors
  if (simulationHoursError.value) {
    toast.error(simulationHoursError.value)
    return
  }

  isSimulating.value = true
  simulationResults.value = []
  hasFirstResult.value = false
  
  // Initialize loading states for all vials (1-7)
  loadingStates.value = Object.fromEntries(
    Array.from({ length: 7 }, (_, i) => [i + 1, true])
  )

  try {
    // Run simulations sequentially
    for (let vial = 1; vial <= 7; vial++) {
      if (!isSimulating.value) break // Check if component is still mounted
      
      console.log(`Starting simulation for vial ${vial}...`)
      try {
        const response = await deviceStore.runSimulation(vial, simulationHours.value)
        if (!isSimulating.value) break // Check if component is still mounted
        
        // Update loading state for this vial
        loadingStates.value[vial] = false
        console.log(`Completed simulation for vial ${vial}`)
        
        // Add result to array
        simulationResults.value.push({
          vial_id: vial,
          ...response.summary_data
        })

        // After first result, set hasFirstResult to true
        if (vial === 1) {
          hasFirstResult.value = true
        }
      } catch (error) {
        if (!isSimulating.value) break // Check if component is still mounted
        
        // Handle simulation error for this specific vial
        loadingStates.value[vial] = false
        const errorDetail = error.response?.data?.detail
        const errorMessage = errorDetail?.message || error.message
        toast.error(`Vial ${vial} simulation failed: ${errorMessage}`)
        // Add error state to results
        simulationResults.value.push({
          vial_id: vial,
          error: true,
          error_message: errorMessage
        })
      }
    }
    
    if (!isSimulating.value) return // Check if component is still mounted
    
    console.log('All simulations completed')
    if (simulationResults.value.some(r => r.error)) {
      toast.warning('Some simulations completed with errors')
    } else {
      toast.success('All simulations completed successfully')
    }
  } catch (error) {
    if (!isSimulating.value) return // Check if component is still mounted
    
    console.error('Error running simulations:', error)
    toast.error(error.message || 'Failed to run simulations')
  } finally {
    if (isSimulating.value) { // Only update state if component is still mounted
    isSimulating.value = false
    // Clear loading states
    loadingStates.value = {}
    }
  }
}

const metrics = [
  { name: 'Initial OD', key: 'initial_population', tooltip: 'Starting optical density of the culture' },
  { name: 'Initial IC50', key: 'initial_ic50', tooltip: 'Initial drug concentration at which growth rate is reduced by 50%' },
  { name: 'Final IC50', key: 'final_ic50', tooltip: 'Final drug concentration at which growth rate is reduced by 50%' },
  { name: 'Adaptation Factor', key: 'adaptation_factor', tooltip: 'Ratio of final IC50 to initial IC50, indicating how much the culture adapted to the drug. A value of 2 means the culture became twice as resistant to the drug.' },
  { name: 'Final Dose', key: 'final_dose', tooltip: 'Final drug concentration applied to the culture' },
  { name: 'Final Growth Rate', key: 'final_effective_growth_rate', tooltip: 'Final growth rate of the culture (hover for doubling time)' },
  { name: 'Final OD', key: 'final_population', tooltip: 'Final optical density of the culture' },
  { name: 'Final Generation Number', key: 'final_generation', tooltip: 'Final number of population doublings during the simulation' },
  { name: 'Pump 1 Volume', key: 'pump1_volume_used', tooltip: 'Total volume of medium used from Pump 1' },
  { name: 'Pump 2 Volume', key: 'pump2_volume_used', tooltip: 'Total volume of drug medium used from Pump 2' },
  { name: 'Waste Volume', key: 'waste_medium_volume_created', tooltip: 'Total volume of waste medium created' }
]

// Function to get value for a specific metric and vial
function getMetricValue(vialId, metric) {
  const result = simulationResults.value.find(r => r.vial_id === vialId)
  if (!result) {
    return hasFirstResult.value ? '---' : null
  }
  if (result.error) {
    return 'Error'
  }
  if (metric.key === 'adaptation_factor') {
    if (result.final_ic50 && result.initial_ic50) {
      return result.final_ic50 / result.initial_ic50
    }
    return '---'
  }
  const value = result[metric.key]
  if (value === null || value === undefined) {
    return '---'
  }
  return value
}

function formatNumber(value) {
  if (value === null || value === undefined || value === '---' || value === 'Error') {
    return value
  }
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2
  }).format(value)
}

function formatVolume(value) {
  if (value === null || value === undefined || value === '---' || value === 'Error') {
    return value
  }
  if (isNaN(value)) {
    return 'NaN mL'
  }
  return `${formatNumber(value)} mL`
}

function formatMetricValue(value, metric) {
  if (value === '---' || value === null || value === undefined) return value
  if (value === 'Error') return value
  
  if (metric.key === 'final_effective_growth_rate') {
    return `${formatNumber(value)} /hr`
  } else if (metric.key.includes('volume')) {
    const formatted = formatVolume(value)
    return {
      text: formatted,
      isError: formatted.includes('NaN')
    }
  } else if (metric.key === 'final_population') {
    return formatNumber(Array.isArray(value) ? value[0] : value)
  } else {
    return formatNumber(value)
  }
}

function getMetricTooltip(metric, vialId = null) {
  if (metric.key === 'final_effective_growth_rate' && vialId) {
    const result = simulationResults.value.find(r => r.vial_id === vialId)
    if (result && !result.error) {
      return `Doubling time: ${calculateDoublingTime(result.final_effective_growth_rate)}`
    }
  }
  if (metric.key === 'adaptation_factor' && vialId) {
    const result = simulationResults.value.find(r => r.vial_id === vialId)
    if (result && !result.error) {
      return `Initial IC50: ${formatNumber(result.initial_ic50)} μg/mL\nFinal IC50: ${formatNumber(result.final_ic50)} μg/mL\nAdaptation Factor: ${formatNumber(result.final_ic50 / result.initial_ic50)}`
    }
  }
  return metric.tooltip
}

// Function to get vial name
function getVialName(vialId) {
  const result = simulationResults.value.find(r => r.vial_id === vialId)
  if (!result) {
    return hasFirstResult.value ? '---' : null
  }
  if (result.error) {
    return 'Error'
  }
  // Get vial name from experiment parameters cultures
  const culture = experimentStore.currentExperiment?.parameters?.cultures?.[vialId]
  return culture?.name || `Vial ${vialId}`
}

// Function to get vial description
function getVialDescription(vialId) {
  const result = simulationResults.value.find(r => r.vial_id === vialId)
  if (!result) {
    return hasFirstResult.value ? '---' : null
  }
  if (result.error) {
    return 'Error'
  }
  // Get vial description from experiment parameters cultures
  const culture = experimentStore.currentExperiment?.parameters?.cultures?.[vialId]
  return culture?.description || '-'
}



// Add these new functions
function getTotalVolumeTooltip(volume, stockVolume, mediumType) {
  if (isNaN(volume)) {
    return 'Error calculating volume'
  }
  const remaining = stockVolume - volume
  if (remaining >= 0) {
    return `${mediumType} stock bottle (${formatVolume(stockVolume)}) is sufficient.\nWill use ${formatVolume(volume)} (${formatNumber(volume/stockVolume*100)}% of stock).\n${formatVolume(remaining)} will remain.`
  } else {
    return `${mediumType} stock bottle (${formatVolume(stockVolume)}) is insufficient.\nWill use ${formatVolume(volume)} (${formatNumber(volume/stockVolume*100)}% of stock).\nMissing ${formatVolume(Math.abs(remaining))}.`
  }
}

function getWasteVolumeTooltip(volume) {
  if (isNaN(volume)) {
    return 'Error calculating volume'
  }
  const availableSpace = wasteBottleVolume.value - currentWasteVolume.value
  if (availableSpace >= volume) {
    return `Waste bottle (${formatVolume(wasteBottleVolume.value)}) has sufficient space.\nCurrent waste: ${formatVolume(currentWasteVolume.value)}\nWill create ${formatVolume(volume)} (${formatNumber(volume/wasteBottleVolume.value*100)}% of bottle).\n${formatVolume(availableSpace - volume)} will remain available.`
  } else {
    return `Waste bottle (${formatVolume(wasteBottleVolume.value)}) has insufficient space.\nCurrent waste: ${formatVolume(currentWasteVolume.value)}\nWill create ${formatVolume(volume)} (${formatNumber(volume/wasteBottleVolume.value*100)}% of bottle).\nMissing ${formatVolume(Math.abs(availableSpace - volume))} of space.`
  }
}
</script>

<style scoped>
.experiment-simulation {
  padding: 20px;
  background: #1e1e1e;
  border-radius: 8px;
  margin: 20px 0;
  width: 100%;
}

.header {
  margin-bottom: 20px;
}

.header h3 {
  margin: 0;
  color: #fff;
  font-size: 1.2em;
}

.description {
  color: #888;
  margin: 5px 0 0;
  font-size: 0.9em;
}

.controls {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.simulation-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hours-input {
  width: 100px;
}

.hours-label {
  color: #888;
  font-size: 0.9em;
  margin-left: 4px;
  margin-top: 8px;
  /* Vertically center with input text */
  display: flex;
  align-items: center;
  height: 40px;
}

.simulation-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 20px 0;
  color: #fff;
}

.results {
  margin-top: 20px;
}

.summary-card {
  background: #2a2a2a !important;
  width: 100%;
}

:deep(.v-table) {
  background: transparent !important;
  width: 100%;
}

:deep(.v-table__wrapper) {
  background: transparent !important;
  width: 100%;
}

:deep(.v-table__wrapper > table) {
  background: transparent !important;
  width: 100%;
}

:deep(.v-table__wrapper > table > thead > tr > th) {
  color: #fff !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  font-weight: 500;
}

:deep(.v-table__wrapper > table > tbody > tr > td) {
  color: #fff !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}

:deep(.v-table__wrapper > table > tbody > tr:hover) {
  background: rgba(255, 255, 255, 0.05) !important;
}

.volume-text-danger {
  color: #ff1744 !important;  /* Brighter red */
  font-weight: 500;
}

.volume-text-success {
  color: #4caf50 !important;  /* Green */
  font-weight: 500;
}

.volume-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

.volume-good {
  color: #4caf50 !important;
}

.volume-danger {
  color: #f44336 !important;
}

:deep(.volume-cell.volume-danger .v-icon) {
  color: #f44336 !important;
}

:deep(.volume-cell.volume-good .v-icon) {
  color: #4caf50 !important;
}

.text-danger {
  color: #ff5252 !important;
  font-weight: bold;
}

.text-success {
  color: #4caf50 !important;
  font-weight: bold;
}

.text-error {
  color: rgb(var(--v-theme-error));
}

.volume-cell.error {
  color: rgb(var(--v-theme-error));
  display: flex;
  align-items: center;
  gap: 4px;
}

.plot-section {
  margin-top: 30px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #2a2a2a;
  border-radius: 4px;
  padding: 20px;
}

.plot-wrapper {
  width: 100%;
  height: 500px;
  min-height: 400px;
  max-height: 600px;
  position: relative;
}

.plot-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(42, 42, 42, 0.9);
  z-index: 1;
}

.loading-text {
  margin-top: 16px;
  color: #fff;
  font-size: 1.1em;
}

:deep(.graph-container) {
  width: 100% !important;
  height: 100% !important;
  margin-top: 0 !important;
}


</style>
