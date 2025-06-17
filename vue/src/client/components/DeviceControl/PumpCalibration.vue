<template>
  <div class="pump-data">
    <table>
      <thead>
        <tr>
          <th>Calibration Sequence</th>
          <th></th>
          <th>Volume (mL)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="index">
          <td>
            <div class="iteration-rotation-wrapper">
              <div class="iteration">{{ row.iterations }}</div>
              <div class="multiplier">x</div>
              <div class="rotation">{{ row.rotations }} rots</div>
            </div>
          </td>
          <td>
            <button @click="toggleButtonState(index)" :class="[isStopButton[index] ? 'stop-button' : '', isStopButton[index] === false && rows[index].total_ml ? 'restart-button' : '']">
              <span v-if="isStopButton[index]">Stop</span>
              <span v-else>Start</span>
            </button>
          </td>
          <td>
            <input v-model="row.total_ml" @change="onTotalMlInput(row)" type="float" />
          </td>
        </tr>
      </tbody>
    </table>

    <div class="chart-container">
      <Bar
        id="pump-calibration-chart"
        :options="chartOptions"
        class="pump-calibration-chart"
        v-if="chartData.datasets[0].data.length > 0"
        :data="chartData"
      />
    </div>

    <div v-if="calibrationModeEnabled" class="calibration-section">
      <!-- Existing content -->
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDeviceStore } from '@/client/stores/device'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, Title, Tooltip, Legend } from 'chart.js'

ChartJS.register(BarElement, CategoryScale, LinearScale, Title, Tooltip, Legend)

const props = defineProps({
  pumpId: {
    type: Number,
    required: true
  }
})

const deviceStore = useDeviceStore()
const { calibrationModeEnabled, pumps, valves } = storeToRefs(deviceStore)

const chartData = ref({ datasets: [{ data: [] }] })
const chartOptions = ref({
  responsive: true,
  devicePixelRatio: 4,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }
  },
  backgroundColor: 'rgba(0, 140, 186, 0.3)',
  layout: { padding: { top: 20 } },
  scales: {
    x: { title: { display: true, text: 'rotations' } },
    y: {
      title: { display: true, text: 'mL / rotation' },
      beginAtZero: false,
      suggestedMin: 0.1,
      suggestedMax: 0.22,
    },
  },
})

const isStopButton = ref({})
const activeCalibrationId = ref(null)
const rows = ref([
  { rotations: 1, iterations: 50, total_ml: NaN },
  { rotations: 5, iterations: 10, total_ml: NaN },
  { rotations: 10, iterations: 5, total_ml: NaN },
  { rotations: 50, iterations: 1, total_ml: NaN },
])

const pumpIdCalibrationData = computed(() => pumps.value?.calibration?.[props.pumpId] || {})

function createChartData() {
  return {
    labels: Object.keys(pumpIdCalibrationData.value),
    datasets: [{
      label: null,
      data: Object.values(pumpIdCalibrationData.value),
      fill: false,
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1,
    }]
  }
}

function updateChartData() {
  chartData.value = createChartData()
}

function toggleButtonState(index) {
  const isValveOpen = Object.values(valves.value.states).some((valve) => valve === 'open')
  if (!isValveOpen) {
    alert('At least one valve must be open to start the pump')
    return
  }
  isStopButton.value[index] = !isStopButton.value[index]
  if (isStopButton.value[index]) {
    promptForMl(rows.value[index])
  } else {
    deviceStore.setPartStateAction({ devicePart: 'pumps', partIndex: props.pumpId, newState: 'stopped' })
  }
}

function resetButton(row) {
  isStopButton.value[row] = false
}

function onTotalMlInput(row) {
  if (row.total_ml) {
    deviceStore.setPartCalibrationAction({
      devicePart: 'pumps',
      partIndex: props.pumpId,
      newCalibration: {
        ...pumpIdCalibrationData.value,
        [row.rotations]: row.total_ml / row.rotations / row.iterations
      }
    })
    isStopButton.value[row] = false
  }
}

async function promptForMl(row) {
  const proceed = confirm(`Pumping ${row.rotations} rotations ${row.iterations} times. Please blank the scale. Continue?`)
  
  if (!proceed) {
    // User cancelled, reset button back to start state
    const rowIndex = rows.value.findIndex(r => r === row)
    resetButton(rowIndex)
    return
  }
  
  try {
    // Create unique ID for this calibration
    const calibrationId = Date.now() + Math.random()
    activeCalibrationId.value = calibrationId
    
    // Start calibration sequence (this sets pump state to 'running' in backend)
    const calibrationPromise = deviceStore.startPumpCalibrationSequence({
      pumpId: props.pumpId,
      rotations: row.rotations,
      iterations: row.iterations
    })
    
    // Small delay to ensure backend has set the pump state
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Refresh device data so main pump button shows spinning
    await deviceStore.fetchDeviceData()
    
    // Wait for calibration to complete
    await calibrationPromise
    
    const rowIndex = rows.value.findIndex(r => r === row)
    resetButton(rowIndex)
    
    // Only ask for input if this calibration is still active (wasn't interrupted)
    if (activeCalibrationId.value === calibrationId) {
      const total_ml = parseFloat(prompt('Enter total mL pumped'))
      if (!isNaN(total_ml)) {
        row.total_ml = total_ml
        onTotalMlInput(row)
      }
    }
    
    // Clear active calibration ID
    if (activeCalibrationId.value === calibrationId) {
      activeCalibrationId.value = null
    }
  } catch (error) {
    console.error('Calibration failed:', error)
    const rowIndex = rows.value.findIndex(r => r === row)
    resetButton(rowIndex)
    // Clear active calibration on error
    activeCalibrationId.value = null
  }
}

onMounted(() => {
  if (pumpIdCalibrationData.value) {
    updateChartData()
  }
  rows.value.forEach((row) => {
    row.total_ml = (pumpIdCalibrationData.value[row.rotations] || 0) * row.rotations * row.iterations
    row.total_ml = row.total_ml ? row.total_ml.toFixed(2) : ''
  })
})

watch(pumpIdCalibrationData, () => {
  updateChartData()
}, { deep: true })

// Watch pump state and reset calibration buttons when pump is stopped externally
watch(() => pumps.value?.states?.[props.pumpId], (newState, oldState) => {
  if (newState === 'stopped' && oldState === 'running') {
    // Mark calibration as interrupted if pump was manually stopped
    const anyCalibrationRunning = Object.values(isStopButton.value).some(Boolean)
    if (anyCalibrationRunning && activeCalibrationId.value) {
      activeCalibrationId.value = null // Clear active calibration to prevent input prompt
    }
    
    // Reset all calibration buttons when pump is stopped
    Object.keys(isStopButton.value).forEach(index => {
      if (isStopButton.value[index]) {
        isStopButton.value[index] = false
      }
    })
  }
})
</script>

<style scoped>
.pump-data {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-top: 10px;
  width: 200px;
  border: 1px solid #e3e3e3;
  border-radius: 5px;
  justify-content: center;
  padding-left: 5px;
  padding-right: 5px;
}

table {
  border-collapse: collapse;
  width: 100%;
}

th, td {
  border: none;
  padding: 4px;
  text-align: center;
  font-size: 0.8rem;
}

button {
  padding: 3px 5px;
  background-color: #008CBA;
  color: white;
  border: none;
  cursor: pointer;
  border-radius: 8px;
  font-size: 0.7rem;
}

button.stop-button {
  background-color: #f44336 !important;
  color: white !important;
}

button.restart-button {
  background-color: #15007ea3 !important;
  color: white !important;
}

button:hover {
  background-color: #007B9A;
}

td:nth-child(1), td:nth-child(2) {
  width: 40px;
}

td:nth-child(4) {
  width: 60px;
}

input[type="float"] {
  width: 100%;
  font-size: 12px;
}

.pump-calibration-chart {
  margin-top: 0px;
  width: 190px;
  height: 130px;
}

.iteration-rotation-wrapper {
  width: 75px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.iteration {
  width: 15px;
  text-align: right;
}

.multiplier {
  width: 10px;
  text-align: center;
}

.rotation {
  width: 40px;
  text-align: left;
}
</style>
