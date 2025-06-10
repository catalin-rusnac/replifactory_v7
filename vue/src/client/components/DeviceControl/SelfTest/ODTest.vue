<!-- ODTest.vue -->
<template>
  <div>
    <h2>
      Transmitted Light Intensity
      <v-btn @click="runODTest" :disabled="isFetchingCalibration">
        Remeasure (approx. 5 sec)
      </v-btn>
    </h2>
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineExpose } from 'vue';
import { useDeviceStore } from '@/client/stores/device';
import Chart from 'chart.js/auto';

const deviceStore = useDeviceStore();
const isFetchingCalibration = computed(() => deviceStore.isFetchingCalibration);
const maxODSignals = computed(() => deviceStore.ods?.max_signal);

const chartCanvas = ref(null);
let chart = null;

/**
 * Create or update the Chart.js chart.
 */
function createChart(data) {
  const datasets = [];
  const colors = {
    red: 'rgba(255, 0, 0, 1)',
    green: 'rgba(0, 255, 0, 1)',
    blue: 'rgba(0, 0, 255, 1)',
    laser: 'rgba(139, 0, 0, 1)', // Dark red for laser
  };

  // Order & labels for each type of LED or laser
  const order = [
    { key: 'laser', label: 'Laser (nominal power)' },
    { key: 'red', label: 'Red LED (max power)' },
    { key: 'green', label: 'Green LED (max power)' },
    { key: 'blue', label: 'Blue LED (max power)' },
  ];

  // Build the datasets in the defined order
  order.forEach(({ key, label }) => {
    if (data[key]) {
      const dataPoints = Object.keys(data[key]).map((vial) => ({
        x: parseInt(vial, 10),
        y: data[key][vial],
      }));

      datasets.push({
        label: label, // Use the descriptive label
        data: dataPoints,
        backgroundColor: colors[key],
        borderColor: colors[key],
        borderWidth: 1,
        type: 'bar',
      });
    }
  });

  if (chart) {
    chart.destroy();
  }

  if (chartCanvas.value) {
    chart = new Chart(chartCanvas.value, {
      type: 'bar',
      data: {datasets: datasets},
      options: {
        responsive: true,
        scales: {
          x: {
            type: 'linear',
            position: 'bottom',
            title: {display: true, text: 'Vial'},
          },
          y: {
            title: {display: true, text: 'Signal [mV]'},
          },
        },
      },
    });
  }
}

/**
 * Expose a method for the parent to grab the chart's Base64 snapshot
 */
function getChartImage() {
  if (!chart) return '';
  return chart.toBase64Image();
}

defineExpose({ getChartImage });

/**
 * Actions to run the OD test, fetch data, and update chart.
 */
async function runODTest() {
  console.log('Running OD test...');
  await deviceStore.fetchODCalibrationData();
  console.log('OD test completed. Plotting data...');
  await deviceStore.fetchDeviceData();
  if (maxODSignals.value) {
    createChart(maxODSignals.value);
  } else {
    console.error('No OD signal data available.');
  }
}

// Whenever maxODSignals changes, re-create the chart.
watch(maxODSignals, (newData) => {
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
