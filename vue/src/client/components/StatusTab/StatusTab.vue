<template>
  <div>
    <!-- Database Download Row -->
    <v-row class="mt-3">
      <v-col cols="4">
        <!-- Download Database Button -->
        <v-btn 
          color="success" 
          @click="download_db"
          :loading="isDownloadingDb"
          :disabled="isDownloadingDb"
          size="large"
        >
          <v-icon size="large">mdi-cloud-download</v-icon> Download Database
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
          :loading="exportingVials[i]"
          :disabled="isDownloadingDb || exportingVials[i]"
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
import { toast } from 'vue3-toastify';

const status_text = ref('');
const selectedFormat = ref('html');
const isDownloadingDb = ref(false);
const exportingVials = ref({1: false, 2: false, 3: false, 4: false, 5: false, 6: false, 7: false});

/**
 * Download database file
 */
async function download_db() {
  if (isDownloadingDb.value) {
    toast('Database download already in progress...', { type: 'warning' });
    return;
  }
  
  isDownloadingDb.value = true;
  
  try {
    toast('Preparing database download...', { type: 'info' });
    
    const response = await api.get('/download_db', { 
      responseType: 'blob',
      timeout: 30000  // 30 second timeout for large database files
    });
    
    const file = new Blob([response.data], { type: 'application/octet-stream' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(file);
    a.download = 'replifactory.db';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    // Clean up the blob URL
    URL.revokeObjectURL(a.href);
    
    toast('Database downloaded successfully!', { type: 'success' });
    
  } catch (error) {
    console.error('Error downloading database:', error);
    
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      toast('Database download timed out - the file might be too large', { type: 'error' });
    } else if (error.response?.status === 404) {
      toast('Database file not found on server', { type: 'error' });
    } else if (error.response?.status === 500) {
      toast('Server error during database download', { type: 'error' });
    } else {
      toast('Failed to download database - check connection', { type: 'error' });
    }
  } finally {
    isDownloadingDb.value = false;
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
  if (exportingVials.value[vial]) {
    toast(`Vial ${vial} export already in progress...`, { type: 'warning' });
    return;
  }
  
  exportingVials.value[vial] = true;
  
  try {
    toast(`Exporting vial ${vial} data as ${filetype.toUpperCase()}...`, { type: 'info' });
    
    const response = await api.get(`/export/${vial}/${filetype}`, { 
      responseType: 'blob',
      timeout: 60000  // 60 second timeout for large exports
    });
    
    const file = new Blob([response.data], { type: 'application/octet-stream' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(file);
    
    // Use descriptive filename based on file type
    if (filetype === 'html') {
      a.download = `vial_${vial}_plot.html`;
    } else {
      a.download = `vial_${vial}_data.${filetype}`;
    }
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    // Clean up the blob URL
    URL.revokeObjectURL(a.href);
    
    toast(`Vial ${vial} ${filetype.toUpperCase()} exported successfully!`, { type: 'success' });
    
  } catch (error) {
    console.error(`Error exporting data for vial ${vial}:`, error);
    
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      toast(`Vial ${vial} export timed out - the file might be too large`, { type: 'error' });
    } else if (error.response?.status === 404) {
      toast(`Vial ${vial} not found or no current experiment selected`, { type: 'error' });
    } else if (error.response?.status === 400) {
      toast(`Invalid export parameters for vial ${vial}`, { type: 'error' });
    } else if (error.response?.status === 500) {
      toast(`Server error during vial ${vial} export - check if experiment has data`, { type: 'error' });
    } else {
      toast(`Failed to export vial ${vial} data - check connection`, { type: 'error' });
    }
  } finally {
    exportingVials.value[vial] = false;
  }
}



</script>

<style scoped>
.img-fluid {
  max-width: 100%;
  height: auto;
}
</style>
