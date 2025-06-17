<!-- implement experiment checlist in a simple short way -->
 <!-- check 1 - all stock concentrations match (vials 1-7 and stock bottle)  -->

 <!-- create simple table with 3 columns: check name, status, action -->

<template>
  <div class="experiment-checks">
    <v-table>
      <thead>
        <tr>
          <th>
            <v-btn 
              color="primary" 
              @click="verifyAll"
              :loading="isVerifyingAll"
              :disabled="checks.some(c => c.loading)"
              size="small"
            >
              Verify All
            </v-btn>
          </th>
          <th>Pre-experiment Checks</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="check in checks" :key="check.id">
          <td>
            <v-btn 
              size="small" 
              @click="runCheck(check.id)"
              :loading="check.loading"
            >
              Verify
            </v-btn>
          </td>
          <td>
            <span v-if="check.tooltip">
              <v-tooltip :text="check.tooltip">
                <template v-slot:activator="{ props }">
                  <span v-bind="props">{{ check.name }}</span>
                </template>
              </v-tooltip>
            </span>
            <span v-else>{{ check.name }}</span>
          </td>
          <td>
            <v-chip :color="getStatusColor(check.status)" size="small">
              {{ getStatusText(check.status) }}
            </v-chip>
          </td>
        </tr>
      </tbody>
    </v-table>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { toast } from 'vue3-toastify'
import { useExperimentStore } from '@/client/stores/experiment'
import { useDeviceStore } from '@/client/stores/device'

const experimentStore = useExperimentStore()
const deviceStore = useDeviceStore()

const isVerifyingAll = ref(false)

const checks = ref([
  {
    id: 'stock',
    name: 'Stock Concentrations Match (Vials 1-7 & Stock Bottle)',
    status: 'pending',
    loading: false,
    tooltip: 'Verifies that all vials (1-7) have the same drug concentration as the stock bottle to ensure experiment consistency'
  },
  {
    id: 'od',
    name: 'OD Calibration (OD0 > 20mV)',
    status: 'pending',
    loading: false,
    tooltip: 'Checks that optical density blank calibration is above 20mV for all vials to ensure accurate OD measurements'
  },
  {
    id: 'volume',
    name: 'Stock Volume Sufficient (24h Simulation)',
    status: 'pending',
    loading: false,
    tooltip: 'Runs a 24-hour simulation to predict media and drug consumption, ensuring sufficient stock volumes are available'
  },
  {
    id: 'waste',
    name: 'Waste Bottle Capacity vs Current Stock Volumes',
    status: 'pending',
    loading: false,
    tooltip: 'Media use may exceed prediction and overfill the waste bottle. Check if the waste bottle has enough space to fit all the medium and drug medium.'
  },
  {
    id: 'pump1',
    name: 'Pump1 Concentration Zero (All Vials)',
    status: 'pending',
    loading: false,
    tooltip: 'Ensures pump1 (main media) has zero drug concentration in all vials to prevent contamination and maintain experimental control'
  }
])

function getStatusColor(status) {
  return status === 'passed' ? 'success' : 
         status === 'failed' ? 'error' : 
         status === 'warning' ? 'warning' : 'grey'
}

function getStatusText(status) {
  return status === 'passed' ? 'Passed' : 
         status === 'failed' ? 'Failed' : 
         status === 'warning' ? 'Warning' : 'Pending'
}

async function runCheck(checkId) {
  const check = checks.value.find(c => c.id === checkId)
  check.loading = true
  
  try {
    if (checkId === 'stock') {
      await checkStockConcentrations(check)
    } else if (checkId === 'od') {
      await checkODCalibration(check)
    } else if (checkId === 'volume') {
      await checkStockVolume(check)
    } else if (checkId === 'waste') {
      await checkWasteBottleCapacity(check)
    } else if (checkId === 'pump1') {
      await checkPump1Concentration(check)
    }
  } finally {
    check.loading = false
  }
}

async function checkStockConcentrations(check) {
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  const params = experimentStore.currentExperiment?.parameters
  const stockConcentration = params.stock_concentration_drug
  const vialConcentrations = Object.values(params.cultures).map(vial => vial.pump2_stock_drug_concentration)
  const allMatch = vialConcentrations.every(concentration => concentration === stockConcentration)
  
  check.status = allMatch ? 'passed' : 'failed'
  toast(
    check.status === 'passed' ? 'Stock concentrations verified' : 'Stock concentration mismatch detected',
    { type: check.status === 'passed' ? 'success' : 'error' }
  )
}

async function checkODCalibration(check) {
  await deviceStore.fetchDeviceData()
  const od0_values = Object.values(deviceStore.ods.calibration)
  const failed_vials = {vial: [], value: []}
  const warning_vials = {vial: [], value: []}

  for (let vial = 0; vial < 7; vial++) {
    const od0_value = od0_values[vial][0] || od0_values[vial][0.0] || 0
    if (od0_value < 15) {
      failed_vials.value.push(od0_value)
      failed_vials.vial.push(vial + 1) // Convert to 1-based vial numbering
    } else if (od0_value < 20) {
      warning_vials.value.push(od0_value)
      warning_vials.vial.push(vial + 1) // Convert to 1-based vial numbering
    }
  }
  
  if (failed_vials.vial.length > 0) {
    check.status = 'failed'
    const message = `OD calibration failed. OD0 value in vial ${failed_vials.vial.join(', ')} is ${failed_vials.value.join(', ')}mV (below 15mV threshold)`
    toast(message, { type: 'error' })
  } else if (warning_vials.vial.length > 0) {
    check.status = 'warning'
    const message = `OD calibration warning. OD0 value in vial ${warning_vials.vial.join(', ')} is ${warning_vials.value.join(', ')}mV (below 20mV recommended)`
    toast(message, { type: 'warning' })
  } else {
    check.status = 'passed'
    toast('OD calibration verified', { type: 'success' })
  }
}

async function checkStockVolume(check) {
  const params = experimentStore.currentExperiment?.parameters
  if (!params) {
    check.status = 'failed'
    toast('No experiment parameters found', { type: 'error' })
    return
  }

  try {
    // Run 24h simulation for all vials (1-7) using the same approach as ExperimentSimulation
    const simulationResults = []
    
    for (let vial = 1; vial <= 7; vial++) {
      try {
        const response = await deviceStore.runSimulation(vial, 24)
        simulationResults.push({
          vial_id: vial,
          ...response.summary_data
        })
      } catch (error) {
        console.error(`Vial ${vial} simulation failed:`, error)
        // Continue with other vials even if one fails
      }
    }
    
    // If no valid simulation data, fail the check
    if (simulationResults.length === 0) {
      check.status = 'failed'
      toast('Failed to fetch simulation data for volume calculation', { type: 'error' })
      return
    }
    
    // Calculate total volumes using the same approach as ExperimentSimulation
    const totalPump1Volume = simulationResults.reduce((sum, result) => sum + result.pump1_volume_used, 0)
    const totalPump2Volume = simulationResults.reduce((sum, result) => sum + result.pump2_volume_used, 0)
    const totalWasteVolume = simulationResults.reduce((sum, result) => sum + result.waste_medium_volume_created, 0)
    
    // Get available stock volumes and waste capacity - using correct parameter names
    const drugStockVolume = params.stock_volume_drug || 0
    const mediaStockVolume = params.stock_volume_main || 0
    const wasteBottleVolume = params.bottle_volume_waste || 0
    const currentWasteVolume = params.stock_volume_waste || 0
    const availableWasteSpace = wasteBottleVolume - currentWasteVolume
    
    // Check if we have enough stock and waste capacity
    const drugSufficient = totalPump2Volume <= drugStockVolume
    const mediaSufficient = totalPump1Volume <= mediaStockVolume
    const wasteSufficient = totalWasteVolume <= availableWasteSpace
    
    if (drugSufficient && mediaSufficient && wasteSufficient) {
      check.status = 'passed'
      toast(`Stock volumes sufficient. Drug: ${totalPump2Volume.toFixed(1)}/${drugStockVolume}mL, Media: ${totalPump1Volume.toFixed(1)}/${mediaStockVolume}mL, Waste: ${totalWasteVolume.toFixed(1)}/${availableWasteSpace.toFixed(1)}mL available`, { type: 'success' })
    } else {
      check.status = 'failed'
      const issues = []
      if (!drugSufficient) issues.push(`Drug: need ${totalPump2Volume.toFixed(1)}mL, have ${drugStockVolume}mL`)
      if (!mediaSufficient) issues.push(`Media: need ${totalPump1Volume.toFixed(1)}mL, have ${mediaStockVolume}mL`)
      if (!wasteSufficient) issues.push(`Waste: need ${totalWasteVolume.toFixed(1)}mL, only ${availableWasteSpace.toFixed(1)}mL available`)
      toast(`Volume issues. ${issues.join(', ')}`, { type: 'error' })
    }
    
  } catch (error) {
    check.status = 'failed'
    toast('Simulation failed: ' + (error.message || 'Unknown error'), { type: 'error' })
  }
}

async function checkWasteBottleCapacity(check) {
  await new Promise(resolve => setTimeout(resolve, 300))
  
  const params = experimentStore.currentExperiment?.parameters
  if (!params) {
    check.status = 'failed'
    toast('No experiment parameters found', { type: 'error' })
    return
  }

  // Get current stock volumes and waste bottle parameters
  const mainStockVolume = params.stock_volume_main || 0
  const drugStockVolume = params.stock_volume_drug || 0
  const wasteBottleVolume = params.bottle_volume_waste || 0
  const currentWasteVolume = params.stock_volume_waste || 0
  
  // Calculate available waste space and total current stock
  const availableWasteSpace = wasteBottleVolume - currentWasteVolume
  const totalCurrentStock = mainStockVolume + drugStockVolume
  
  if (totalCurrentStock <= availableWasteSpace) {
    check.status = 'passed'
    toast(`Waste capacity sufficient. Current stocks: ${totalCurrentStock.toFixed(1)}mL, Available waste space: ${availableWasteSpace.toFixed(1)}mL`, { type: 'success' })
  } else {
    check.status = 'warning'
    toast(`Warning: Current stock volumes (${totalCurrentStock.toFixed(1)}mL) exceed available waste space (${availableWasteSpace.toFixed(1)}mL). Overflow may occur.`, { type: 'warning' })
  }
}

async function checkPump1Concentration(check) {
  await new Promise(resolve => setTimeout(resolve, 500))
  
  const params = experimentStore.currentExperiment?.parameters
  if (!params || !params.cultures) {
    check.status = 'failed'
    toast('No experiment parameters or cultures found', { type: 'error' })
    return
  }

  const wrongVials = []
  
  // Check pump1_stock_drug_concentration for vials 1-7
  for (let vial = 1; vial <= 7; vial++) {
    const culture = params.cultures[vial]
    if (culture) {
      const pump1Concentration = culture.pump1_stock_drug_concentration || 0
      if (pump1Concentration !== 0) {
        wrongVials.push(`Vial ${vial}: ${pump1Concentration}`)
      }
    }
  }
  
  if (wrongVials.length > 0) {
    check.status = 'failed'
    toast(`Pump1 concentration not zero in: ${wrongVials.join(', ')}`, { type: 'error' })
  } else {
    check.status = 'passed'
    toast('All vials have pump1 concentration set to zero', { type: 'success' })
  }
}

async function verifyAll() {
  isVerifyingAll.value = true
  
  try {
    // Run all checks sequentially
    for (const check of checks.value) {
      await runCheck(check.id)
    }
    
    // Check overall status and show summary
    const passedChecks = checks.value.filter(c => c.status === 'passed').length
    const failedChecks = checks.value.filter(c => c.status === 'failed').length
    const warningChecks = checks.value.filter(c => c.status === 'warning').length
    const totalChecks = checks.value.length
    
    if (failedChecks === 0 && warningChecks === 0) {
      toast(`All ${totalChecks} checks passed! Experiment ready to start.`, { type: 'success' })
    } else if (failedChecks === 0 && warningChecks > 0) {
      toast(`${passedChecks} checks passed, ${warningChecks} warning(s). Review warnings before starting.`, { type: 'warning' })
    } else if (failedChecks > 0) {
      const issues = []
      if (failedChecks > 0) issues.push(`${failedChecks} failed`)
      if (warningChecks > 0) issues.push(`${warningChecks} warning(s)`)
      toast(`${passedChecks}/${totalChecks} checks passed, ${issues.join(', ')}. Review issues before starting.`, { type: 'warning' })
    } else {
      toast(`All ${totalChecks} checks failed. Address issues before starting experiment.`, { type: 'error' })
    }
    
  } catch (error) {
    toast('Error running checks: ' + (error.message || 'Unknown error'), { type: 'error' })
  } finally {
    isVerifyingAll.value = false
  }
}

// Expose checks for parent component access
defineExpose({
  checks
})
</script>

<style scoped>
.experiment-checks {
  margin: 20px 0;
}
</style>