<template>
  <div>
    <!-- Camera Button Row -->
    <v-row class="mt-3">
      <v-col cols="4">
        <!-- Camera Button -->
        <v-btn 
          color="info" 
          @click="capture_image"
          :loading="isCapturingImage"
          :disabled="isCapturingImage"
          size="large"
        >
          <v-icon size="large">mdi-camera</v-icon> Capture Photo
        </v-btn>
      </v-col>
    </v-row>

    <!-- Image Display -->
    <div class="mt-3" v-if="camera_image">
      <v-card>
        <v-card-title>
          <span class="text-h6">Latest Captured Image</span>
        </v-card-title>
        <v-card-text>
          <img :src="camera_image" class="img-fluid" style="max-width: 100%; height: auto;" />
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import api from '@/api';
import { toast } from 'vue3-toastify';

const camera_image = ref(null);
const isCapturingImage = ref(false);

/**
 * Capture an image from the camera
 */
async function capture_image() {
  if (isCapturingImage.value) {
    toast('Camera capture already in progress...', { type: 'warning' });
    return;
  }
  
  isCapturingImage.value = true;
  
  try {
    toast('Capturing image...', { type: 'info' });
    
    const response = await api.get('/camera/capture', { 
      responseType: 'arraybuffer',
      timeout: 15000  // 15 second timeout for camera operations
    });
    
    const base64 = btoa(
      new Uint8Array(response.data).reduce((data, byte) => data + String.fromCharCode(byte), '')
    );
    camera_image.value = `data:image/jpeg;base64,${base64}`;
    toast('Image captured successfully!', { type: 'success' });
    
  } catch (error) {
    console.error('Error capturing image:', error);
    
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      toast('Camera capture timed out - this might indicate the camera is busy or needs reset', { type: 'error' });
    } else if (error.response?.status === 500) {
      toast('Camera error - please try rebooting the device', { type: 'error' }); 
    } else {
      toast('Failed to capture image - check camera connection', { type: 'error' });
    }
    
    // Clear any partial image on error
    camera_image.value = null;
  } finally {
    isCapturingImage.value = false;
  }
}
</script>

<style scoped>
.img-fluid {
  max-width: 100%;
  height: auto;
}
</style> 