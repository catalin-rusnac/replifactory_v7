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
import { ref, computed, watch } from 'vue';
import { useStore } from 'vuex';
import Chart from 'chart.js/auto';

const store = useStore();
const isFetchingCalibration = computed(() => store.state.device.isFetchingCalibration);
const maxODSignals = computed(() => store.state.device.ods.max_signal);

const chartCanvas = ref(null);
let chart = null;

function createChart(data) {
  const datasets = [];
  const colors = {
    red: 'rgba(255, 0, 0, 1)',
    green: 'rgba(0, 255, 0, 1)',
    blue: 'rgba(0, 0, 255, 1)',
    laser: 'rgba(139, 0, 0, 1)', // Dark red for laser
  };

  // Define the order of the datasets and their labels
  const order = [
    { key: 'laser', label: 'Laser (nominal power)' },
    { key: 'red', label: 'Red LED (max power)' },
    { key: 'green', label: 'Green LED (max power)' },
    { key: 'blue', label: 'Blue LED (max power)' },
  ];

  // Iterate over the data in the desired order
  order.forEach(({key, label}) => {
    if (data[key]) {
      const dataPoints = Object.keys(data[key]).map(vial => ({
        x: parseInt(vial),
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

const runODTest = async () => {
  console.log('Running OD test...');
  await store.dispatch('device/fetchODCalibrationData');
  console.log('OD test completed. Plotting data...');
  await store.dispatch('device/getAllDeviceData');
  if (maxODSignals.value) {
    createChart(maxODSignals.value);
  } else {
    console.error("No OD signal data available.");
  }
};

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