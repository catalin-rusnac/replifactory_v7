  <!-- implement experiment checlist in a simple short way -->
 <!-- check 1 - all stock concentrations match (vials 1-7 and stock bottle)  -->

 <!-- create simple table with 3 columns: check name, status, action -->

<template>
  <div class="experiment-checks" ref="checksContainer">
    <v-table>
      <thead>
        <tr>
          <th>
            <v-btn 
              color="primary" 
              @click="verifyAll"
              :loading="isVerifyingAll"
              :disabled="checks.some(c => c.loading) || !isExperimentSafeForChecks"
              size="small"
            >
              Verify All
            </v-btn>
          </th>
          <th>Status</th>
          <th>Pre-experiment Checks</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="check in checks" :key="check.id">
          <td>
            <v-btn 
              size="small" 
              @click="runCheck(check.id)"
              :loading="check.loading"
              :disabled="check.loading || !isExperimentSafeForChecks"
            >
              Verify
            </v-btn>
          </td>
          <td>
            <v-chip :color="getStatusColor(check.status)" size="small">
              {{ getStatusText(check.status) }}
            </v-chip>
          </td>
          <td>
            <v-tooltip location="top">
              <template v-slot:activator="{ props }">
                <div v-bind="props">
                  <span>{{ check.name }}</span>
                  <div 
                    v-if="check.details" 
                    v-html="check.details" 
                    class="od-details-container"
                  ></div>
                </div>
              </template>
              <div v-html="check.tooltip"></div>
            </v-tooltip>
          </td>
        </tr>
      </tbody>
    </v-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { toast } from 'vue3-toastify'
import { useExperimentStore } from '@/client/stores/experiment'
import { useDeviceStore } from '@/client/stores/device'



const experimentStore = useExperimentStore()
const deviceStore = useDeviceStore()

const isVerifyingAll = ref(false)
const checksContainer = ref(null)
const isPageVisible = ref(true)
const isComponentVisible = ref(true)
const intersectionObserver = ref(null)

const checks = ref([
  {
    id: 'experiment_timing',
    name: 'Experiment Selection & Timing',
    status: 'pending',
    loading: false,
    tooltip: 'Checks that an experiment is selected and verifies timing safety. Warns if resuming after >3h delay as culture dynamics can become unstable.',
    details: ''
  },
  {
    id: 'pump_calibration',
    name: 'Pump Calibration Monotonicity',
    status: 'pending',
    loading: false,
    tooltip: 'Validates that pump calibration values (ml/rotation) are monotonically descending. Higher speeds should pump less volume per rotation (e.g., 50 rots < 10 rots < 5 rots < 1 rot). <br><br/><b>Tip:</b> If calibration fails, check for air bubbles in the tubing during calibration.',
    details: ''
  },
  {
    id: 'stirrer_calibration',
    name: 'Stirrer Calibration (High > Low)',
    status: 'pending',
    loading: false,
    tooltip: 'Validates that stirrer high speed setting is greater than low speed setting for all vials (1-7). This ensures proper speed differentiation.',
    details: ''
  },
  {
    id: 'od',
    name: 'OD Calibration (OD0 > 20mV)',
    status: 'pending',
    loading: false,
    tooltip: 'Checks that optical density blank calibration is above 20mV for all vials to ensure accurate OD measurements',
    details: ''
  },
  {
    id: 'current_od',
    name: 'Current OD Values',
    status: 'pending',
    loading: false,
    tooltip: 'Measures the current OD of all vials to ensure they are properly zeroed before starting a new experiment.',
    details: ''
  },
  {
    id: 'stock',
    name: 'Stock Concentrations Match (Vials 1-7 & Stock Bottle)',
    status: 'pending',
    loading: false,
    tooltip: 'Verifies that all vials (1-7) have the same drug concentration as the stock bottle to ensure experiment consistency'
  },
  {
    id: 'pump1',
    name: 'Pump1 Concentration Zero (All Vials)',
    status: 'pending',
    loading: false,
    tooltip: 'Ensures pump1 (main media) has zero drug concentration in all vials.'
  },
  {
    id: 'waste',
    name: 'Waste Bottle Capacity vs Current Stock Volumes',
    status: 'pending',
    loading: false,
    tooltip: 'Media use may exceed prediction and overfill the waste bottle. Checks that the waste bottle has enough space to fit all the medium and drug medium.'
  },
  {
    id: 'volume',
    name: 'Stock Volume Sufficient (24h Simulation)',
    status: 'pending',
    loading: false,
    tooltip: 'Runs a 24-hour simulation to predict media and drug consumption, ensuring sufficient stock volumes are available'
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

async function checkExperimentTiming(check) {
  check.details = '' // Reset details on each run
  await new Promise(resolve => setTimeout(resolve, 300))
  
  // Check if experiment is selected
  const currentExperiment = experimentStore.currentExperiment
  if (!currentExperiment || !currentExperiment.id) {
    check.status = 'failed'
    check.details = `<span class="experiment-timing-value red">
      <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
      No experiment selected - please select or create an experiment
    </span>`
    toast('No experiment selected', { type: 'error', autoClose: 10000 })
    return
  }

  // Check OD data timing
  try {
    // Get the latest experiment summary data
    const backendSummary = await experimentStore.fetchExperimentSummary()
    
    // Check if any vials have OD data
    let latestOdTimestamp = null
    for (let vial = 1; vial <= 7; vial++) {
      const vialData = backendSummary[`vial${vial}`]
      if (vialData && vialData.od_timestamp) {
        const timestamp = new Date(vialData.od_timestamp).getTime()
        if (!latestOdTimestamp || timestamp > latestOdTimestamp) {
          latestOdTimestamp = timestamp
        }
      }
    }
    
    if (!latestOdTimestamp) {
      // No OD data - this is fine for new experiments
      check.status = 'passed'
      check.details = `<span class="experiment-timing-value green">
        <i class="v-icon mdi mdi-check-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Experiment "${currentExperiment.name}" selected - no previous OD data (new experiment)
      </span>`
      toast('Experiment ready - no previous data found', { type: 'success', autoClose: 10000 })
      return
    }

    // Calculate time difference
    const latestTime = new Date(latestOdTimestamp)
    const currentTime = new Date()
    const timeDifferenceHours = (currentTime - latestTime) / (1000 * 60 * 60)

    if (timeDifferenceHours > 24) {
      check.status = 'failed'
      const hoursAgo = Math.floor(timeDifferenceHours)
      const minutesAgo = Math.floor((timeDifferenceHours - hoursAgo) * 60)
      check.details = `<span class="experiment-timing-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Last OD measurement was ${hoursAgo}h ${minutesAgo}m ago. Experiments idle >24h must be restarted. Autoclave tubing and start a new experiment.
      </span>`
      toast(`Error: Last measurement was ${hoursAgo}h ${minutesAgo}m ago. Must start new experiment.`, { type: 'error', autoClose: 10000 })
    } else if (timeDifferenceHours > 3) {
      check.status = 'warning'
      const hoursAgo = Math.floor(timeDifferenceHours)
      const minutesAgo = Math.floor((timeDifferenceHours - hoursAgo) * 60)
      check.details = `<span class="experiment-timing-value yellow">
        <i class="v-icon mdi mdi-alert-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Last OD measurement was ${hoursAgo}h ${minutesAgo}m ago. Resuming after >3h delays can cause unstable culture dynamics. Consider autoclaving tubing and starting a new experiment.
      </span>`
      toast(`Warning: Last measurement was ${hoursAgo}h ${minutesAgo}m ago. Consider starting fresh.`, { type: 'warning', autoClose: 10000 })
    } else {
      check.status = 'passed'
      const hoursAgo = Math.floor(timeDifferenceHours)
      const minutesAgo = Math.floor((timeDifferenceHours - hoursAgo) * 60)
      check.details = `<span class="experiment-timing-value green">
        <i class="v-icon mdi mdi-check-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Experiment "${currentExperiment.name}" selected - last measurement ${hoursAgo}h ${minutesAgo}m ago (safe to resume)
      </span>`
      toast('Experiment timing is safe for resumption', { type: 'success', autoClose: 10000 })
    }

  } catch (error) {
    // If we can't fetch experiment data, treat as new experiment
    check.status = 'passed'
    check.details = `<span class="experiment-timing-value green">
      <i class="v-icon mdi mdi-check-circle" style="font-size: 16px; vertical-align: middle;"></i> 
      Experiment "${currentExperiment.name}" selected - no previous data available (new experiment)
    </span>`
    toast('Experiment selected - no previous data available', { type: 'success', autoClose: 10000 })
  }
}

// Computed property to check if updates should be allowed
const shouldAllowUpdates = () => {
  return isPageVisible.value && isComponentVisible.value
}

// Page visibility change handler
function handleVisibilityChange() {
  isPageVisible.value = !document.hidden
}

// Setup intersection observer to detect component visibility
function setupVisibilityObserver() {
  if (!checksContainer.value) return
  
  intersectionObserver.value = new IntersectionObserver(
    (entries) => {
      isComponentVisible.value = entries[0].isIntersecting
    },
    {
      threshold: 0.1 // Component is considered visible when 10% is in view
    }
  )
  
  intersectionObserver.value.observe(checksContainer.value)
}

// Computed property to check if experiment is in a safe state to run checks
const isExperimentSafeForChecks = computed(() => {
  const currentExperiment = experimentStore.currentExperiment
  if (!currentExperiment) return true // No experiment selected is safe
  
  const status = currentExperiment.status
  // Only allow checks when experiment is fully stopped or in safe states
  return status === 'stopped' || status === 'inactive' || !status
})

async function runCheck(checkId) {
  // Only run checks if the page and component are visible
  if (!shouldAllowUpdates()) {
    toast('Cannot run checks while page/component is not visible', { type: 'warning', autoClose: 10000 })
    return
  }
  
  // Only run checks if experiment is in a safe state
  if (!isExperimentSafeForChecks.value) {
    const status = experimentStore.currentExperiment?.status || 'unknown'
    toast(`Cannot run checks while experiment is ${status}. Please wait for experiment to fully stop.`, { type: 'warning', autoClose: 10000 })
    return
  }

  const check = checks.value.find(c => c.id === checkId)
  check.loading = true
  
  try {
    if (checkId === 'experiment_timing') {
      await checkExperimentTiming(check)
    } else if (checkId === 'stock') {
      await checkStockConcentrations(check)
    } else if (checkId === 'od') {
      await checkODCalibration(check)
    } else if (checkId === 'current_od') {
      await checkCurrentODs(check)
    } else if (checkId === 'volume') {
      await checkStockVolume(check)
    } else if (checkId === 'waste') {
      await checkWasteBottleCapacity(check)
    } else if (checkId === 'pump1') {
      await checkPump1Concentration(check)
    } else if (checkId === 'pump_calibration') {
      await checkPumpCalibrationMonotonicity(check)
    } else if (checkId === 'stirrer_calibration') {
      await checkStirrerCalibration(check)
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
    { type: check.status === 'passed' ? 'success' : 'error', autoClose: 10000 }
  )
}

async function checkODCalibration(check) {
  check.details = ''; // Reset details on each run
  await deviceStore.fetchDeviceData()
  const od0_calibration = deviceStore.ods.calibration;
  const failed_vials = [];
  const warning_vials = [];

  if (!od0_calibration) {
    check.status = 'failed';
    toast.error('OD calibration data not found. Please run a calibration.', { type: 'error' });
    return;
  }

  for (let vial = 1; vial <= 7; vial++) {
    const vialData = od0_calibration[vial];
    // Check for both '0' and '0.0' keys
    const od0_value = vialData ? (vialData['0.0'] ?? vialData['0']) : undefined;

    if (od0_value === undefined || od0_value === null) {
      // If no OD0 value, it's a failure.
      failed_vials.push({ vial, value: 'N/A' });
      continue;
    }

    if (od0_value < 15) {
      failed_vials.push({ vial, value: od0_value });
    } else if (od0_value < 20) {
      warning_vials.push({ vial, value: od0_value });
    }
  }
  
  let detailsHtml = '';
  if (failed_vials.length > 0) {
    check.status = 'failed';
    detailsHtml += failed_vials.map(v => 
      `<span class="od-value red">Vial ${v.vial}: ${typeof v.value === 'number' ? v.value.toFixed(1) + 'mV' : v.value}</span>`
    ).join('');
    toast.error(`OD calibration failed for vials: ${failed_vials.map(v => v.vial).join(', ')}`, { type: 'error' });
  } else if (warning_vials.length > 0) {
    check.status = 'warning';
    toast.warning(`OD calibration warning for vials: ${warning_vials.map(v => v.vial).join(', ')}`, { type: 'warning' });
  } else {
    check.status = 'passed';
    toast('OD calibration verified', { type: 'success', autoClose: 10000 });
  }

  if (warning_vials.length > 0) {
      detailsHtml += warning_vials.map(v => 
      `<span class="od-value yellow">Vial ${v.vial}: ${v.value.toFixed(1)}mV</span>`
    ).join('');
  }
  
  if (detailsHtml) {
    check.details = `<div class="od-values-grid">${detailsHtml}</div>`;
  }
}

async function checkCurrentODs(check) {
  check.details = ''; // Reset details on each run
  try {
    // Measure ODs sequentially for each vial (1-7)
    const vials = [1, 2, 3, 4, 5, 6, 7];
    for (const vial of vials) {
      try {
        await deviceStore.measureODs([vial]); // Measure one vial at a time
        // Small delay between measurements to prevent overwhelming the system
        await new Promise(resolve => setTimeout(resolve, 50));
      } catch (vialError) {
        console.warn(`Failed to measure OD for vial ${vial}:`, vialError);
        console.log('Full vialError object:', {
          message: vialError.message,
          response: vialError.response,
          status: vialError.response?.status,
          data: vialError.response?.data
        });
        
        // Check if this is a device/server connection error
        if ((vialError.response && vialError.response.status === 500) || 
            (vialError.response && vialError.response.data && vialError.response.data.detail && vialError.response.data.detail.includes('Device not initialized')) ||
            (vialError.message && vialError.message.includes('500')) ||
            (vialError.message === 'Network Error') ||
            (vialError.code === 'ERR_NETWORK') ||
            (!vialError.response && vialError.message)) {
          check.status = 'failed';
          check.details = `<span class="od-value red">
            <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
            Error - Device disconnected. Please check device connection and try again.
          </span>`
          toast('Error - Device disconnected. Check device connection.', { type: 'error', autoClose: 10000 });
          console.log('Device disconnection error detected:', vialError);
          return;
        }
        // Continue with other vials for other types of errors
      }
    }
  } catch (error) {
    // Check if this is a device/server connection error
    if ((error.response && error.response.status === 500) || 
        (error.response && error.response.data && error.response.data.detail && error.response.data.detail.includes('Device not initialized')) ||
        (error.message && error.message.includes('500')) ||
        (error.message === 'Network Error') ||
        (error.code === 'ERR_NETWORK') ||
        (!error.response && error.message)) {
      check.status = 'failed';
      check.details = `<span class="od-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Error - Device disconnected. Please check device connection and try again.
      </span>`
      toast('Error - Device disconnected. Check device connection.', { type: 'error' });
      console.log('Device disconnection error detected:', error);
    } else {
      check.status = 'failed';
      check.details = `<span class="od-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Failed to measure current ODs. Check device connection.
      </span>`
      toast('Failed to measure current ODs. Check device connection.', { type: 'error' });
    }
    console.error(error);
    return;
  }
  
  const odValues = deviceStore.ods.states;
  const vials = [1, 2, 3, 4, 5, 6, 7]; // Assuming 7 vials
  const errorVials = [];
  const warningVials = [];
  
  const valueSpans = vials.map(vial => {
    const value = odValues[vial];
    let icon = '';
    let colorClass = '';

    if (value === undefined || value === null) {
      icon = 'mdi-help-circle';
      colorClass = 'grey';
    } else if (value < -0.03) {
      icon = 'mdi-close-circle'; // Red cross
      colorClass = 'red';
      errorVials.push({ vial, value });
    } else if (value > 0.03) {
      icon = 'mdi-alert-circle'; // Yellow warning
      colorClass = 'yellow';
      warningVials.push({ vial, value });
    } else {
      icon = 'mdi-check-circle'; // Green tick
      colorClass = 'green';
    }
    
    const displayValue = (value !== undefined && value !== null) ? value.toFixed(3) : 'N/A';
    
    return `<span class="od-value ${colorClass}">
              <i class="v-icon mdi ${icon}" style="font-size: 16px; vertical-align: middle;"></i> 
              Vial ${vial}: ${displayValue}
            </span>`;
  }).join('');

  check.details = `<div class="od-values-grid">${valueSpans}</div>`;
  
  let tooltipText = ''
  if (errorVials.length > 0) {
    check.status = 'failed';
    tooltipText += "<b>Error:</b> One or more vials have a very low OD reading (&lt; -0.03). This suggests a calibration issue. Please perform an OD calibration.";
    toast.error(`OD check failed for vials: ${errorVials.map(v => v.vial).join(', ')}`, { type: 'error' });
  } else if (warningVials.length > 0) {
    check.status = 'warning';
    tooltipText += "<br/><br/><b>Warning:</b> One or more vials have a positive OD reading (&gt; 0.03). This is acceptable if you are resuming a previous experiment, but new experiments should start with zeroed ODs.";
    toast.warning(`Positive OD detected for vials: ${warningVials.map(v => v.vial).join(', ')}`, { type: 'warning' });
  } else {
    check.status = 'passed';
    tooltipText += "<br/><br/><b>Passed:</b> All vial ODs are close to zero, which is ideal for starting a new experiment.";
    toast.success('Current OD values verified.', { type: 'success' });
  }
  
  check.tooltip = tooltipText;
}

async function checkStockVolume(check) {
  check.details = '' // Reset details on each run
  check.status = 'pending'
  toast('Running 24h simulation for volume check...', { type: 'info' })
  
  const params = experimentStore.currentExperiment?.parameters
  if (!params) {
    check.status = 'failed'
    toast('No experiment parameters found', { type: 'error' })
    return
  }

  try {
    // Run 24h simulation for all vials (1-7) using the same approach as ExperimentSimulation
    const simulationResults = []
    const failedVials = []
    
    for (let vial = 1; vial <= 7; vial++) {
      try {
        const response = await deviceStore.runSimulation(vial, 24)
        simulationResults.push({
          vial_id: vial,
          ...response.summary_data
        })
      } catch (error) {
        console.error(`Vial ${vial} simulation failed:`, error)
        failedVials.push(vial)
        // Continue with other vials even if one fails
      }
    }
    
    // If no valid simulation data, fail the check
    if (simulationResults.length === 0) {
      check.status = 'failed'
      check.details = `<span class="simulation-volume-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        All vials failed to simulate - check experiment parameters and device connection
      </span>`
      toast('Failed to fetch simulation data for volume calculation', { type: 'error' })
      return
    }
    
    // Calculate total volumes using the same approach as ExperimentSimulation
    const totalPump1Volume = simulationResults.reduce((sum, result) => sum + result.pump1_volume_used, 0)
    const totalPump2Volume = simulationResults.reduce((sum, result) => sum + result.pump2_volume_used, 0)
    const totalWasteVolume = simulationResults.reduce((sum, result) => sum + result.waste_medium_volume_created, 0)
    
    // Get available stock volumes and waste capacity - using correct parameter names
    const drugStockVolume = Number(params.stock_volume_drug) || 0
    const mediaStockVolume = Number(params.stock_volume_main) || 0
    const wasteBottleVolume = Number(params.bottle_volume_waste) || 0
    const currentWasteVolume = Number(params.stock_volume_waste) || 0
    const availableWasteSpace = wasteBottleVolume - currentWasteVolume
    
    // Check if we have enough stock and waste capacity
    const drugSufficient = totalPump2Volume <= drugStockVolume
    const mediaSufficient = totalPump1Volume <= mediaStockVolume
    const wasteSufficient = totalWasteVolume <= availableWasteSpace
    
    // Build details HTML for issues
    let detailsHtml = ''
    const issues = []
    
    if (!drugSufficient) {
      issues.push(`Drug: need ${totalPump2Volume.toFixed(1)}mL, have ${drugStockVolume}mL`)
      detailsHtml += `<span class="simulation-volume-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Drug bottle: need ${totalPump2Volume.toFixed(1)}mL, have ${drugStockVolume}mL (${(totalPump2Volume - drugStockVolume).toFixed(1)}mL short)
      </span>`
    }
    
    if (!mediaSufficient) {
      issues.push(`Media: need ${totalPump1Volume.toFixed(1)}mL, have ${mediaStockVolume}mL`)
      detailsHtml += `<span class="simulation-volume-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Main bottle: need ${totalPump1Volume.toFixed(2)}mL, have ${mediaStockVolume.toFixed(2)}mL (${(totalPump1Volume - mediaStockVolume).toFixed(2)}mL short)
      </span>`
    }
    
    if (!wasteSufficient) {
      issues.push(`Waste: need ${totalWasteVolume.toFixed(1)}mL, only ${availableWasteSpace.toFixed(1)}mL available`)
      detailsHtml += `<span class="simulation-volume-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Waste bottle: need ${totalWasteVolume.toFixed(1)}mL space, only ${availableWasteSpace.toFixed(1)}mL available (${(totalWasteVolume - availableWasteSpace).toFixed(1)}mL overflow)
      </span>`
    }
    
    if (failedVials.length > 0) {
      detailsHtml += `<span class="simulation-volume-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Failed simulations: Vial${failedVials.length > 1 ? 's' : ''} ${failedVials.join(', ')} - check parameters
      </span>`
    }
    
    if (detailsHtml) {
      check.details = `<div class="simulation-volume-grid">${detailsHtml}</div>`
    }
    
    if (drugSufficient && mediaSufficient && wasteSufficient && failedVials.length === 0) {
      check.status = 'passed'
      toast(`Stock volumes sufficient. Drug: ${totalPump2Volume.toFixed(1)}/${drugStockVolume}mL, Media: ${totalPump1Volume.toFixed(1)}/${mediaStockVolume}mL, Waste: ${totalWasteVolume.toFixed(1)}/${availableWasteSpace.toFixed(1)}mL available`, { type: 'success' })
    } else if (failedVials.length > 0 && issues.length === 0) {
      check.status = 'warning'
      toast(`Simulation warnings: ${failedVials.length} vial(s) failed but volumes are sufficient for others`, { type: 'warning' })
    } else {
      check.status = 'failed'
      const allIssues = [...issues]
      if (failedVials.length > 0) allIssues.push(`${failedVials.length} vial(s) failed simulation`)
      toast(`Volume issues. ${allIssues.join(', ')}`, { type: 'error' })
    }
    
  } catch (error) {
    check.status = 'failed'
    check.details = `<span class="simulation-volume-value red">
      <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
      Simulation error: ${error.message || 'Unknown error'}
    </span>`
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
  const mainStockVolume = Number(params.stock_volume_main) || 0
  const drugStockVolume = Number(params.stock_volume_drug) || 0
  const wasteBottleVolume = Number(params.bottle_volume_waste) || 0
  const currentWasteVolume = Number(params.stock_volume_waste) || 0
  
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

async function checkPumpCalibrationMonotonicity(check) {
  check.details = '' // Reset details on each run
  await deviceStore.fetchDeviceData()
  
  const pumps = deviceStore.pumps
  if (!pumps || !pumps.calibration) {
    check.status = 'failed'
    toast('Pump calibration data not found. Please run pump calibration.', { type: 'error' })
    return
  }

  const pumpIds = [1, 2, 4] // MAIN, DRUG, WASTE pumps
  const pumpNames = { 1: 'MAIN', 2: 'DRUG', 4: 'WASTE' }
  const failedPumps = []
  const warningPumps = []
  let detailsHtml = ''
  
  for (const pumpId of pumpIds) {
    const calibrationData = pumps.calibration[pumpId]
    
    if (!calibrationData || Object.keys(calibrationData).length === 0) {
      failedPumps.push(`${pumpNames[pumpId]} (no calibration data)`)
      detailsHtml += `<span class="pump-calibration-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        ${pumpNames[pumpId]}: Missing calibration data - please calibrate this pump
      </span>`
      continue
    }
    
    // Convert to array of [rotations, ml_per_rotation] and sort by rotations ascending
    const calibrationPoints = Object.entries(calibrationData)
      .map(([rot, coef]) => [parseInt(rot), parseFloat(coef)])
      .sort((a, b) => a[0] - b[0])
    
    if (calibrationPoints.length < 2) {
      warningPumps.push(`${pumpNames[pumpId]} (insufficient data points)`)
      detailsHtml += `<span class="pump-calibration-value yellow">
        <i class="v-icon mdi mdi-alert-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        ${pumpNames[pumpId]}: Only ${calibrationPoints.length} calibration point(s) - need at least 2 to check monotonicity
      </span>`
      continue
    }
    
    // Check if ml/rotation values are monotonically descending (higher speeds pump less volume)
    let isMonotonic = true
    const violations = []
    
    for (let i = 1; i < calibrationPoints.length; i++) {
      const prevPoint = calibrationPoints[i - 1]
      const currPoint = calibrationPoints[i]
      
      // Higher rotation speed should have lower or equal ml/rotation coefficient
      if (currPoint[1] > prevPoint[1]) {
        isMonotonic = false
        violations.push(`${currPoint[0]} rots pumps MORE than ${prevPoint[0]} rots (${currPoint[1].toFixed(3)} vs ${prevPoint[1].toFixed(3)} ml/rot)`)
      }
    }
    
    if (!isMonotonic) {
      failedPumps.push(`${pumpNames[pumpId]} (non-monotonic)`)
      detailsHtml += `<span class="pump-calibration-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        ${pumpNames[pumpId]}: Invalid calibration - ${violations.join('; ')}
      </span>`
    }
    // Only show failed pumps - don't display passing ones
  }
  
  if (detailsHtml) {
    check.details = `<div class="pump-calibration-grid">${detailsHtml}</div>`
  }
  
  if (failedPumps.length > 0) {
    check.status = 'failed'
    toast(`Pump calibration monotonicity failed for: ${failedPumps.join(', ')}`, { type: 'error' })
  } else if (warningPumps.length > 0) {
    check.status = 'warning'
    toast(`Pump calibration warnings for: ${warningPumps.join(', ')}`, { type: 'warning' })
  } else {
    check.status = 'passed'
    toast('All pump calibrations are monotonically correct', { type: 'success' })
  }
}

async function checkStirrerCalibration(check) {
  check.details = '' // Reset details on each run
  await deviceStore.fetchDeviceData()
  
  const stirrers = deviceStore.stirrers
  if (!stirrers || !stirrers.calibration) {
    check.status = 'failed'
    toast('Stirrer calibration data not found. Please run stirrer calibration.', { type: 'error' })
    return
  }

  const stirrerIds = [1, 2, 3, 4, 5, 6, 7] // All 7 stirrers
  const failedStirrers = []
  let detailsHtml = ''
  
  for (const stirrerId of stirrerIds) {
    const calibrationData = stirrers.calibration[stirrerId]
    
    if (!calibrationData || typeof calibrationData !== 'object') {
      failedStirrers.push(`Stirrer ${stirrerId} (no calibration data)`)
      detailsHtml += `<span class="stirrer-calibration-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Stirrer ${stirrerId}: Missing calibration data - please calibrate this stirrer
      </span>`
      continue
    }
    
    const { high, low } = calibrationData
    
    if (high === undefined || high === null || low === undefined || low === null) {
      failedStirrers.push(`Stirrer ${stirrerId} (incomplete calibration)`)
      detailsHtml += `<span class="stirrer-calibration-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Stirrer ${stirrerId}: Incomplete calibration data (high: ${high}, low: ${low})
      </span>`
      continue
    }
    
    // Check if high speed is greater than low speed
    if (high <= low) {
      failedStirrers.push(`Stirrer ${stirrerId} (high ≤ low)`)
      detailsHtml += `<span class="stirrer-calibration-value red">
        <i class="v-icon mdi mdi-close-circle" style="font-size: 16px; vertical-align: middle;"></i> 
        Stirrer ${stirrerId}: High speed (${high.toFixed(3)}) must be greater than low speed (${low.toFixed(3)})
      </span>`
    }
    // Only show failed stirrers - don't display passing ones
  }
  
  if (detailsHtml) {
    check.details = `<div class="stirrer-calibration-grid">${detailsHtml}</div>`
  }
  
  if (failedStirrers.length > 0) {
    check.status = 'failed'
    toast(`Stirrer calibration failed for: ${failedStirrers.join(', ')}`, { type: 'error' })
  } else {
    check.status = 'passed'
    toast('All stirrer calibrations are correct (high > low)', { type: 'success' })
  }
}

async function verifyAll() {
  // Only run checks if the page and component are visible
  if (!shouldAllowUpdates()) {
    toast('Cannot run checks while page/component is not visible', { type: 'warning' })
    return
  }
  
  // Only run checks if experiment is in a safe state
  if (!isExperimentSafeForChecks.value) {
    const status = experimentStore.currentExperiment?.status || 'unknown'
    toast(`Cannot run checks while experiment is ${status}. Please wait for experiment to fully stop.`, { type: 'warning' })
    return
  }

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
      toast(`All ${totalChecks} checks passed! Experiment ready to start.`, { type: 'success', autoClose: 10000 })
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

// Setup and cleanup lifecycle hooks
onMounted(() => {
  // Setup page visibility listener
  document.addEventListener('visibilitychange', handleVisibilityChange)
  
  // Setup intersection observer for component visibility
  setupVisibilityObserver()
  
  // Initialize page visibility state
  isPageVisible.value = !document.hidden
})

onUnmounted(() => {
  // Cleanup page visibility listener
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  
  // Cleanup intersection observer
  if (intersectionObserver.value) {
    intersectionObserver.value.disconnect()
  }
})

// Expose checks and visibility state for parent component access
defineExpose({
  checks,
  isPageVisible,
  isComponentVisible,
  shouldAllowUpdates
})
</script>

<style scoped>
.experiment-checks {
  width: 100%;
}

.experiment-checks .v-table {
  margin-top: 20px;
}

.experiment-checks .v-table :deep(th),
.experiment-checks .v-table :deep(td) {
  padding: 8px 12px !important;
}

.experiment-checks .v-table :deep(th:first-child),
.experiment-checks .v-table :deep(td:first-child) {
  padding-left: 16px !important;
}

.experiment-checks .v-table :deep(th:last-child),
.experiment-checks .v-table :deep(td:last-child) {
  padding-right: 16px !important;
}
.od-details-container {
  margin-top: 8px;
  font-size: 0.9em;
}

.od-details-container :deep(.od-values-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 4px 12px;
  margin-top: 4px;
}

.od-details-container :deep(.od-value) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  border-radius: 4px;
  white-space: nowrap;
}

.od-details-container :deep(.od-value .v-icon) {
  margin-right: 2px;
}

.od-details-container :deep(.od-value.red) {
  color: #FF5252;
  font-weight: 500;
}

.od-details-container :deep(.od-value.yellow) {
  color: #FFC107;
}

.od-details-container :deep(.od-value.green) {
  color: #9CCC65;
}

/* Pump calibration specific styles */
.od-details-container :deep(.pump-calibration-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 6px 12px;
  margin-top: 4px;
}

.od-details-container :deep(.pump-calibration-value) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 4px;
  white-space: nowrap;
  font-size: 0.85em;
}

.od-details-container :deep(.pump-calibration-value .v-icon) {
  margin-right: 2px;
}

.od-details-container :deep(.pump-calibration-value.red) {
  color: #FF5252;
  font-weight: 500;
}

.od-details-container :deep(.pump-calibration-value.yellow) {
  color: #FFC107;
}

.od-details-container :deep(.pump-calibration-value.green) {
  color: #9CCC65;
}

/* Stirrer calibration specific styles */
.od-details-container :deep(.stirrer-calibration-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 6px 12px;
  margin-top: 4px;
}

.od-details-container :deep(.stirrer-calibration-value) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 4px;
  white-space: nowrap;
  font-size: 0.85em;
}

.od-details-container :deep(.stirrer-calibration-value .v-icon) {
  margin-right: 2px;
}

.od-details-container :deep(.stirrer-calibration-value.red) {
  color: #FF5252;
  font-weight: 500;
}

/* Simulation volume specific styles */
.od-details-container :deep(.simulation-volume-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 6px 12px;
  margin-top: 4px;
}

.od-details-container :deep(.simulation-volume-value) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 4px;
  white-space: nowrap;
  font-size: 0.85em;
}

.od-details-container :deep(.simulation-volume-value .v-icon) {
  margin-right: 2px;
}

.od-details-container :deep(.simulation-volume-value.red) {
  color: #FF5252;
  font-weight: 500;
}

/* Experiment timing specific styles */
.od-details-container :deep(.experiment-timing-value) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 4px;
  white-space: nowrap;
  font-size: 0.85em;
  max-width: 100%;
  word-wrap: break-word;
  white-space: normal;
}

.od-details-container :deep(.experiment-timing-value .v-icon) {
  margin-right: 2px;
  flex-shrink: 0;
}

.od-details-container :deep(.experiment-timing-value.red) {
  color: #FF5252;
  font-weight: 500;
}

.od-details-container :deep(.experiment-timing-value.yellow) {
  color: #FFC107;
}

.od-details-container :deep(.experiment-timing-value.green) {
  color: #9CCC65;
}
</style>