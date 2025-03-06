<template>
  <div>
    <v-row>
      <v-col>
        <v-tooltip text="Plot test data stored on device">
          <template v-slot:activator="{ props }">
            <v-btn v-bind="props" @click="plotExistingData">
              <v-icon>mdi-chart-line</v-icon>Plot Self-Test Data
            </v-btn>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <v-tooltip text="Export the current page as an HTML file">
          <template v-slot:activator="{ props }">
            <v-btn v-bind="props" @click="exportPageAsHtml">
              <v-icon>mdi-file-download</v-icon> Download Self-Test Report
            </v-btn>
          </template>
        </v-tooltip>
      </v-col>
    </v-row>
    <br>

    <StirrerTest ref="stirrerRef" />
    <ODTest ref="odRef" />

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useStore } from 'vuex';
import StirrerTest from './StirrerTest.vue';
import ODTest from './ODTest.vue';

const store = useStore();
const stirrerRef = ref(null);
const odRef = ref(null);

/**
 * Fetch all existing data for charts.
 */
const plotExistingData = async () => {
  await store.dispatch('device/getAllDeviceData');
};

/**
 * Exports all self-test data (Charts + Camera Test) as an HTML file.
 */
function exportPageAsHtml() {
  // Ensure all data is available before exporting
  const stirrerImg = stirrerRef.value?.getChartImage() || '';
  const odImg = odRef.value?.getChartImage() || '';
  const cameraMedia = cameraRef.value?.getCameraMedia() || '';

  if (!stirrerImg || !odImg) {
    alert('Please run all tests before exporting.');
    return;
  }

  // Generate HTML content with all test results
  const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>Self Test Report</title>
</head>
<body>
  <h1>Self Test Report</h1>

  <h2>Stirrer Speed Profiles</h2>
  ${
    stirrerImg
      ? `<img src="${stirrerImg}" alt="Stirrer Chart" style="max-width: 100%;" />`
      : "<p>No stirrer chart available</p>"
  }

  <h2>Transmitted Light Intensity</h2>
  ${
    odImg
      ? `<img src="${odImg}" alt="OD Chart" style="max-width: 100%;" />`
      : "<p>No OD chart available</p>"
  }

  <p>Exported from the interactive dashboard</p>
</body>
</html>
  `;

  // Generate filename using device name and timestamp
  const deviceName = store.state.hostname || 'device';
  const date = new Date().toISOString().split('T')[0];
  const filename = `${deviceName}-self-test-report-${date}.html`;

  // Create a downloadable HTML file
  const blob = new Blob([htmlContent], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
</script>

<style scoped>
h1 {
  text-align: center;
  margin-bottom: 20px;
}
button {
  margin-top: 20px;
  display: block;
  margin-inline: auto;
}
</style>
