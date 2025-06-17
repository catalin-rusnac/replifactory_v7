<!-- Vue component that measures stirrer speeds at high and low settings and displays them in a bar plot -->
<template>
  <div class="stirrer-speeds">
    <div class="header">
      <h3>Stirrer Speed Measurement</h3>
      <p class="description">Measure and compare stirrer speeds at high and low settings</p>
    </div>

    <div class="controls">
      <v-btn
        color="primary"
        :loading="isMeasuring"
        :disabled="isMeasuring"
        @click="measureSpeeds"
      >
        <v-icon left>mdi-speedometer</v-icon>
        Measure Speeds
      </v-btn>
    </div>

    <div v-if="isMeasuring" class="measurement-status">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
      <span>{{ measurementStatus }}</span>
    </div>

    <div v-if="measurementData.length > 0" class="plot-container">
      <canvas ref="plotContainer" class="plot"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useDeviceStore } from '@/client/stores/device'
import { storeToRefs } from 'pinia'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)
import { toast } from 'vue3-toastify'

const deviceStore = useDeviceStore()
const { stirrers } = storeToRefs(deviceStore)

const isMeasuring = ref(false)
const measurementStatus = ref('')
const measurementData = ref([])
const plotContainer = ref(null)

const HIGH_SPEED = 0.8
const LOW_SPEED = 0.2
const STABILIZATION_TIME = 5000 // 5 seconds
const MEASUREMENT_TIME = 2000 // 2 seconds

async function measureSpeeds() {
  if (isMeasuring.value) return;
  isMeasuring.value = true;
  measurementStatus.value = 'Starting measurement...';
  
  try {
    // Call the measure-stirrer-speeds endpoint
    measurementStatus.value = 'Measuring stirrer speeds...';
    const response = await deviceStore.measureStirrerSpeeds();
    console.log(response) 
    if (response.success) {
      // Convert the speeds object to an array of measurements
      const speedEntries = Object.entries(response.speeds);
      measurementData.value = speedEntries.map(([stirrerId, speed]) => ({
        setting: `Stirrer ${stirrerId}`,
        speed: speed
      }));
      
      // Wait for DOM update and then plot
      await nextTick();
      plotData();
      
      measurementStatus.value = 'Measurement complete!';
      toast.success('Speed measurement completed successfully');
    } else {
      throw new Error('Failed to measure speeds');
    }
  } catch (error) {
    console.error('Error measuring speeds:', error);
    measurementStatus.value = 'Error during measurement';
    toast.error(error.response?.data?.message || 'Failed to measure speeds');
  } finally {
    isMeasuring.value = false;
  }
}

function plotData() {
  if (!plotContainer.value || measurementData.value.length === 0) return
  
  // Destroy existing chart if it exists
  if (window.stirrerChart) {
    window.stirrerChart.destroy()
  }
  
  const ctx = plotContainer.value.getContext('2d')
  
  window.stirrerChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: measurementData.value.map(d => d.setting),
      datasets: [{
        label: 'Speed (RPM)',
        data: measurementData.value.map(d => d.speed),
        backgroundColor: '#4CAF50',
        borderColor: '#388E3C',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Speed (RPM)'
          }
        },
        x: {
          title: {
            display: true,
            text: 'Stirrer'
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: 'Stirrer Speed Measurements'
        },
        legend: {
          display: false
        }
      }
    }
  })
}

onMounted(() => {
  if (measurementData.value.length > 0) {
    plotData()
  }
})
</script>

<style scoped>
.stirrer-speeds {
  padding: 20px;
  background: #1e1e1e;
  border-radius: 8px;
  margin: 20px 0;
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
}

.measurement-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 20px 0;
  color: #fff;
}

.plot-container {
  margin-top: 20px;
  height: 400px;
  background: #2a2a2a;
  border-radius: 4px;
  padding: 10px;
}

.plot {
  width: 100%;
  height: 100%;
}
</style> 