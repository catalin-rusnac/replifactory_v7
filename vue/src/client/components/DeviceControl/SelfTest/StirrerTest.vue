<!-- StirrerTest.vue -->
<template>
  <div>
    <h2>Stirrer Speed Profiles
      <v-btn @click="runCalibrationTest" :disabled="isFetchingCalibration">
        Remeasure (approx. 2 min)
      </v-btn>
    </h2>

    <!-- The Chart.js canvas -->
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineExpose } from 'vue';
import { useDeviceStore } from '@/client/stores/device';
import Chart from 'chart.js/auto';

const deviceStore = useDeviceStore();
const isFetchingCalibration = computed(() => deviceStore.isFetchingCalibration);
const speedProfiles = computed(() => deviceStore.stirrers?.speed_profiles);

const chartCanvas = ref(null);
let chart = null;

// 1) Create or update the chart
function createChart(data) {
  if (chart) {
    chart.destroy();
  }

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
      const avg =
        numericMeasurements.reduce((sum, cur) => sum + cur, 0) /
        numericMeasurements.length;
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

  if (chartCanvas.value) {
    chart = new Chart(chartCanvas.value, {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true,
        scales: {
          x: {
            type: 'linear',
            position: 'bottom',
            min: 0,
            max: 1.02,
            title: {
              display: true,
              text: 'Duty Cycle'
            }
          },
          y: {
            min: 0,
            max: 10000,
            title: {
              display: true,
              text: 'Revolutions per Minute'
            }
          }
        }
      }
    });
  }
}

// 2) Expose a method for the parent to retrieve the chart image
function getChartImage() {
  if (!chart) return '';
  return chart.toBase64Image();
}

defineExpose({ getChartImage });

// 3) Actions to fetch data, then create chart
const runCalibrationTest = async () => {
  await deviceStore.fetchStirrerCalibrationData();
  await deviceStore.fetchDeviceData();
  if (speedProfiles.value) {
    createChart(speedProfiles.value);
  }
};

// Re-create chart whenever speedProfiles changes
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
