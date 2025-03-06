<template>
  <div>
    <!-- Button Row -->
    <v-row class="mt-3">
      <v-col cols="4">
        <!-- Camera Button -->
        <v-btn color="info" @click="capture_image">
          <v-icon size="large">mdi-camera</v-icon> Photo
        </v-btn>
      </v-col>

      <v-col cols="4">
        <!-- Download Database Button -->
        <v-btn color="success" @click="download_db">
          <v-icon size="large">mdi-cloud-download</v-icon> Download Database
        </v-btn>
      </v-col>

      <v-col cols="4">
        <!-- Status Button -->
        <v-btn color="primary" @click="get_info">
          <v-icon size="large">mdi-information</v-icon> Status
        </v-btn>
      </v-col>
    </v-row>

    <!-- Export Section -->
    <v-row class="mt-3" align="center">
      <v-col cols="3" class="text-right">
        <strong>Export Data</strong>
      </v-col>

      <!-- Format Selection -->
      <v-col cols="3">
        <v-select
          v-model="selectedFormat"
          :items="['csv', 'html']"
          label="Select Format"
          dense
        ></v-select>
      </v-col>

      <!-- Vial Buttons -->
      <v-col cols="6">
        <v-btn
          v-for="i in 7"
          :key="'vial'+i"
          color="info"
          class="mr-1 mb-1"
          @click="export_data(i, selectedFormat)"
        >
          Vial {{ i }}
        </v-btn>
      </v-col>
    </v-row>

    <!-- Image Display -->
    <div class="mt-3" v-if="camera_image">
      <img :src="camera_image" class="img-fluid" />
    </div>

    <!-- Status Display -->
    <div class="mt-3" v-html="status_text"></div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import api from '@/api';

const status_text = ref('');
const camera_image = ref(null);
const selectedFormat = ref('html');

/**
 * Download database file
 */
async function download_db() {
  try {
    const response = await api.get('/download_db', { responseType: 'blob' });
    const file = new Blob([response.data], { type: 'application/octet-stream' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(file);
    a.download = document.title + '_replifactory.db';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (error) {
    console.error('Error downloading database:', error);
  }
}

/**
 * Get device status
 */
async function get_info() {
  try {
    const response = await api.get('/status');
    status_text.value = `<pre>${JSON.stringify(response.data, null, 2)}</pre>`;
  } catch (error) {
    console.error('Error fetching status:', error);
  }
}

/**
 * Export data for a specific vial
 * @param {number} vial - Vial number
 * @param {string} filetype - File format (csv/html)
 */
async function export_data(vial, filetype) {
  try {
    const response = await api.get(`/export/${vial}/${filetype}`, { responseType: 'blob' });
    const file = new Blob([response.data], { type: 'application/octet-stream' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(file);
    a.download = `vial_${vial}_data.${filetype}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (error) {
    console.error(`Error exporting data for vial ${vial}:`, error);
  }
}

/**
 * Capture an image from the camera
 */
async function capture_image() {
  try {
    const response = await api.get('/capture', { responseType: 'arraybuffer' });
    const base64 = btoa(
      new Uint8Array(response.data).reduce((data, byte) => data + String.fromCharCode(byte), '')
    );
    camera_image.value = `data:image/jpeg;base64,${base64}`;
  } catch (error) {
    console.error('Error capturing image:', error);
  }
}
</script>

<style scoped>
.img-fluid {
  max-width: 100%;
  height: auto;
}
</style>
