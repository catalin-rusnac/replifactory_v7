<template>
  <div>
    <!-- Button to run the stirrer calibration test -->
    <v-btn @click="plotExistingData">
      Plot Existing Data
    </v-btn>
    <br>
    <br>
<!--    title of chart -->
    <h2>Stirrer Speed Profiles
    <v-btn @click="runCalibrationTest" :disabled="isFetchingCalibration">
      Remeasure (approx. 2 min)
    </v-btn>
      </h2>
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useStore } from 'vuex';
import Chart from 'chart.js/auto';

// Get the Vuex store instance.
const store = useStore();

// Access calibration data and fetching state from the deviceTestStore module.
const isFetchingCalibration = computed(() => store.state.device.isFetchingCalibration);

// Access the existing stirrer calibration data (speed_profiles) from the device module.
const speedProfiles = computed(() => store.state.device.stirrers.speed_profiles);

// Reference to the canvas element for Chart.js.
const chartCanvas = ref(null);
// Variable to hold the Chart.js instance.
let chart = null;

/**
 * Create (or update) the Chart.js chart using the provided data.
 * @param {Object} data - The calibration data to be plotted.
 */
function createChart(data) {
  const datasets = [];
  const colors = [
    'rgba(255, 99, 132, 1)',
    'rgba(54, 162, 235, 1)',
    'rgba(255, 206, 86, 1)',
    'rgba(75, 192, 192, 1)',
    'rgba(153, 102, 255, 1)',
    'rgba(255, 159, 64, 1)',
    'rgba(201, 203, 207, 1)'
  ];
  let colorIndex = 0;

  for (const [stirrerId, curves] of Object.entries(data)) {
    const dataPoints = [];
    for (const [param, measurements] of Object.entries(curves)) {
      const x = parseFloat(param);
      const numericMeasurements = measurements.map(Number);
      const avg = numericMeasurements.reduce((sum, cur) => sum + cur, 0) / numericMeasurements.length;
      dataPoints.push({ x, y: avg });
    }
    dataPoints.sort((a, b) => a.x - b.x);
    datasets.push({
      label: `Stirrer ${stirrerId}`,
      data: dataPoints,
      borderColor: colors[colorIndex % colors.length],
      backgroundColor: colors[colorIndex % colors.length],
      fill: false,
      tension: 0.1
    });
    colorIndex++;
  }

  if (chart) {
    chart.destroy();
  }

  if (chartCanvas.value) {
    chart = new Chart(chartCanvas.value, {
      type: 'line',
      data: { datasets: datasets },
      options: {
        responsive: true,
        scales: {
          x: {
            type: 'linear',
            position: 'bottom',
            min: 0,
            max: 1.02,
            title: { display: true, text: 'Duty Cycle' }
          },
          y: {
            min: 0,
            max: 10000,
            title: { display: true, text: 'Revolutions per Minute' }
          }
        }
      }
    });
  }
}

const runCalibrationTest = async () => {
  console.log('Running stirrer calibration test...');
  await store.dispatch('device/fetchStirrerCalibrationData');
  console.log('Stirrer calibration test completed. Plotting data...');
  await store.dispatch('device/getAllDeviceData');
  if (speedProfiles.value) {
    createChart(speedProfiles.value);
  } else {
    console.error("No existing stirrer calibration data available in speed_profiles.");
  }
};

const plotExistingData = async () => {
  await store.dispatch('device/getAllDeviceData');
  if (speedProfiles.value) {
    createChart(speedProfiles.value);
  } else {
    console.error("No existing stirrer calibration data available in speed_profiles.");
  }
};

watch(speedProfiles, (newData) => {
  if (newData) {
    createChart(newData);
  }
});
</script>

<style scoped>
canvas {
  max-width: 100%;
}
</style>
