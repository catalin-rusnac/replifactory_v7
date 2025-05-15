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
        <!-- Video Button with Duration Selection -->
        <v-menu>
          <template v-slot:activator="{ props }">
            <v-btn color="warning" v-bind="props">
              <v-icon size="large">mdi-video</v-icon> Video
            </v-btn>
          </template>
          <v-list>
            <v-list-item v-for="duration in [5, 10, 25]" :key="duration" @click="capture_video(duration)">
              <v-list-item-title>
                <v-icon color="warning" class="mr-2">mdi-clock-outline</v-icon>
                {{ duration }} seconds
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </v-col>

      <v-col cols="4">
        <!-- Download Database Button -->
        <v-btn color="success" @click="download_db">
          <v-icon size="large">mdi-cloud-download</v-icon> Download Database
        </v-btn>
      </v-col>
    </v-row>

    <!-- Camera Reset Button -->
    <v-row class="mt-2">
      <v-col cols="12" class="text-center">
        <v-btn color="error" @click="forceResetCamera" class="mt-2">
          <v-icon size="large">mdi-camera-refresh</v-icon> Force Reset Camera
        </v-btn>
      </v-col>
    </v-row>

    <!-- Video Recording Progress -->
    <v-row v-if="isRecording" class="mt-3">
      <v-col cols="12">
        <v-progress-linear
          :model-value="recordingProgress"
          color="warning"
          height="20"
        >
          <template v-slot:default="{ value }">
            <strong>Recording: {{ Math.ceil(value) }}% ({{ currentDuration }}s)</strong>
          </template>
        </v-progress-linear>
      </v-col>
    </v-row>

    <!-- Image Display -->
    <div class="mt-3" v-if="camera_image">
      <img :src="camera_image" class="img-fluid" />
    </div>

    <!-- Video Display -->
    <div class="mt-3" v-if="video_url">
      <div v-if="video_url" class="mb-2">
        <small>Video URL: {{ video_url }}</small>
        <small v-if="videoBlob" class="d-block">Video size: {{ (videoBlob.size / 1024 / 1024).toFixed(2) }} MB</small>
        <small v-if="videoBlob" class="d-block">Video type: {{ videoBlob.type }}</small>
      </div>
      <div class="mb-2">
        <v-btn color="primary" @click="downloadVideo" v-if="videoBlob">
          Download Video
        </v-btn>
      </div>
      <video 
        controls 
        class="img-fluid" 
        style="max-width: 100%; height: auto;"
        @error="(e) => console.error('Video error:', e)"
        @loadeddata="() => console.log('Video loaded')"
      >
        <source :src="video_url" type="video/mp4">
        Your browser does not support the video tag.
      </video>
    </div>

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

    <!-- Status Display -->
    <div class="mt-3" v-html="status_text"></div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue';
import api from '@/api';

const status_text = ref('');
const camera_image = ref(null);
const selectedFormat = ref('html');
const video_url = ref(null);
const videoBlob = ref(null);
const isRecording = ref(false);
const recordingProgress = ref(0);
const recordingInterval = ref(null);
const currentDuration = ref(0);

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
    const response = await api.get('/camera/capture', { responseType: 'arraybuffer' });
    const base64 = btoa(
      new Uint8Array(response.data).reduce((data, byte) => data + String.fromCharCode(byte), '')
    );
    camera_image.value = `data:image/jpeg;base64,${base64}`;
  } catch (error) {
    console.error('Error capturing image:', error);
  }
}

/**
 * Download the recorded video
 */
function downloadVideo() {
  if (videoBlob.value) {
    const a = document.createElement('a');
    a.href = video_url.value;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    a.download = `video_${timestamp}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
}

/**
 * Capture a video for the specified duration
 * @param {number} duration - Duration in seconds
 */
async function capture_video(duration) {
  try {
    isRecording.value = true;
    recordingProgress.value = 0;
    currentDuration.value = duration;
    
    // Start progress tracking
    recordingInterval.value = setInterval(() => {
      recordingProgress.value += (100 / duration);
      if (recordingProgress.value >= 100) {
        clearInterval(recordingInterval.value);
      }
    }, 1000);

    console.log('Requesting video...');
    const response = await api.get(`/camera/video/${duration}`, { 
      responseType: 'blob'
    });
    console.log('Video response received:', response);
    
    // Store the blob
    videoBlob.value = response.data;
    
    // Create video URL from blob with MP4 MIME type
    const blob = new Blob([response.data], { type: 'video/mp4' });
    video_url.value = URL.createObjectURL(blob);
    
    // Reset recording state
    isRecording.value = false;
    recordingProgress.value = 0;
    currentDuration.value = 0;
    clearInterval(recordingInterval.value);
  } catch (error) {
    console.error('Error capturing video:', error);
    console.error('Error details:', error.response);
    isRecording.value = false;
    recordingProgress.value = 0;
    currentDuration.value = 0;
    clearInterval(recordingInterval.value);
  }
}

/**
 * Force reset the camera
 */
async function forceResetCamera() {
  try {
    const response = await api.post('/camera/force_reset');
    console.log('Camera reset response:', response.data);
    // Show success message
    alert('Camera reset successful');
  } catch (error) {
    console.error('Error resetting camera:', error);
    // Show error message
    alert('Failed to reset camera: ' + (error.response?.data?.error || error.message));
  }
}

// Clean up on component unmount
onUnmounted(() => {
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value);
  }
});
</script>

<style scoped>
.img-fluid {
  max-width: 100%;
  height: auto;
}
</style>
