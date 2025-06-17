<template>
  <div class="device-configs">
    <div class="config-actions">
      <v-btn 
        color="success" 
        @click="saveConfigs"
      >
        <v-icon left>mdi-content-save</v-icon>
        Save Calibration
      </v-btn>
      <v-btn 
        color="primary" 
        @click="fetchConfigs" 
        :loading="loadingConfigs"
        class="mr-2"
      >
        <v-icon left>mdi-folder-open</v-icon>
        Load Calibration Checkpoints
      </v-btn>
    </div>

    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>

    <div class="config-list mt-4" v-if="configs.length > 0 || loadingConfigs">
      <h3 class="text-h6 mb-2">Available Device Calibration Checkpoints</h3>
      <div v-if="configs.length > 0">
        <v-list>
          <v-list-item
            v-for="config in configs"
            :key="config"
            @click="confirmLoadConfig(config)"
            :class="{ 'config-item': true, 'loading': loadingConfig === config }"
          >
            <v-icon left>mdi-file-document</v-icon>
            {{ config }}
            <v-icon v-if="loadingConfig === config" right>mdi-loading</v-icon>
          </v-list-item>
        </v-list>
      </div>
      <div v-else-if="!loadingConfigs" class="text-muted">
        Click "Refresh Configs" to load.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useDeviceStore } from '../../stores/device'
import { useDialog } from '@/client/composables/useDialog'
import { toast } from 'vue3-toastify';

const deviceStore = useDeviceStore()
const { openDialog } = useDialog()

const configs = ref([])
const errorMessage = ref('')
const loadingConfigs = ref(false)
const loadingConfig = ref(null)
const configToLoad = ref(null)

async function fetchConfigs() {
  errorMessage.value = ''
  loadingConfigs.value = true
  try {
    const configList = await deviceStore.listDeviceConfigs()
    configs.value = (configList || []).sort((a, b) => b.localeCompare(a))
  } catch (e) {
    errorMessage.value = 'Failed to list device configs.'
  } finally {
    loadingConfigs.value = false
  }
}

async function loadConfig(filename) {
  errorMessage.value = ''
  loadingConfig.value = filename
  try {
    await deviceStore.loadDeviceConfig(filename)
    // Show success message or trigger refresh
  } catch (e) {
    errorMessage.value = 'Failed to load device config.'
  } finally {
    loadingConfig.value = null
  }
}

const saveConfigs = async () => {
  errorMessage.value = ''
  try {
    await deviceStore.saveCalibrationToBackend()
    toast.success('Calibration checkpoint saved!')
  } catch (e) {
    errorMessage.value = 'Failed to save device configs.'
  }
}

function confirmLoadConfig(config) {
  configToLoad.value = config
  openDialog({
    title: 'Load checkpoint?',
    message: 'Replace default config with checkpoint?',
  }).then(async (result) => {
    if (result) {
      await loadConfig(configToLoad.value)
      configToLoad.value = null
    }
  })
}
</script>

<style scoped>
.device-configs {
  padding: 1em;
}

.config-actions {
  display: flex;
  justify-content: center;
  gap: 1em;
}

.config-list {
  max-width: 600px;
  margin: 0 auto;
}

.error-message {
  color: red;
  margin: 1em 0;
  text-align: center;
}

.text-muted {
  color: #888;
  text-align: center;
  padding: 1em;
}

.config-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.config-item:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.config-item.loading {
  opacity: 0.7;
  pointer-events: none;
}
</style>