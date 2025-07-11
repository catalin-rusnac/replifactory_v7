<template>
  <div class="DeviceControl" :class="{ 'device-disconnected': deviceConnected === false, 'experiment-running-bg': isExperimentRunning }">
<!--    <div class="disconnected-overlay" v-if="deviceConnected === false"></div>-->
<!--    <div v-if="deviceConnected === false" class="centered-text"> device connection not available </div>-->
    <div class="experiment-running-overlay" v-if="deviceControlEnabled === false"></div>
    
    <!-- Overlay when experiment is running -->
    <div class="experiment-running-overlay" v-if="isExperimentRunning && !bypassMode">
      <div class="overlay-content">
        <div class="warning-message">
          <v-icon color="white" size="48">mdi-flask</v-icon>
          <h2>Experiment Running</h2>
          <p>Device controls are locked during experiment</p>
        </div>
        <v-btn
          class="bypass-button"
          color="error"
          size="large"
          @click="enableBypass"
        >
          <v-icon left>mdi-close</v-icon>
          Bypass
        </v-btn>
      </div>
    </div>
    
    <div class="calibration-switch-row">
      <template v-if="calibrationModeEnabled">
        <v-btn class="reconnect-btn" @click="onReconnectClick">Reconnect Device</v-btn>
      </template>
      <v-switch
        v-model="calibrationMode"
        label="Calibration Mode"
      ></v-switch>
    </div>

    <template v-if="deviceControlEnabled || controlsVisible || bypassMode">
      <PumpControl />
      <ValveControl />
      <StirrerControl />
      <!-- <StirrerSpeeds /> -->
      <ODControl />
      <LEDControl />
      <template v-if="calibrationModeEnabled">
        <DeviceConfigs />
      </template>
    </template>

    <template v-else>
      <p>Device Control Disabled</p>
    </template>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useDeviceStore } from '../../stores/device'
import { useExperimentStore } from '../../stores/experiment'
import { computed, onMounted, ref } from 'vue'
import PumpControl from './PumpControl.vue';
import ValveControl from './ValveControl.vue';
import StirrerControl from './StirrerControl.vue';
import ODControl from './ODControl.vue';
import LEDControl from "./LEDControl.vue";
import DeviceConfigs from "./DeviceConfigs.vue";
// import StirrerSpeeds from "./StirrerSpeeds.vue";
import { useDialog } from '@/client/composables/useDialog'
import { toast } from 'vue3-toastify';

const deviceStore = useDeviceStore()
const experimentStore = useExperimentStore()

const {
  deviceConnected,
  deviceControlEnabled,
  calibrationModeEnabled,
  stirrers,
  pumps,
  valves,
  ods
} = storeToRefs(deviceStore)

const { currentExperiment } = storeToRefs(experimentStore)

// Bypass mode to allow device control during experiment
const bypassMode = ref(false)

const controlsVisible = computed(() => deviceControlEnabled.value)

const calibrationMode = computed({
  get: () => calibrationModeEnabled.value,
  set: (val) => deviceStore.setCalibrationModeEnabled(val)
})

// Check if experiment is running
const isExperimentRunning = computed(() => {
  return currentExperiment.value?.status === 'running'
})

const { openDialog } = useDialog()

function enableBypass() {
  bypassMode.value = true
  toast.warning('Device control bypass enabled. Use caution during running experiment.', {
    autoClose: 5000
  })
}

async function onReconnectClick() {
  console.log('onReconnectClick')
  const result = await openDialog({
    title: 'Reconnect Device?',
    message: 'Are you sure you want to reconnect the device?',
  })
  if (result) {
    toast.success('Reconnecting device...')
    deviceStore.connectDevice()
  } else {
    toast.error('Reconnect cancelled')
  }
}

onMounted(() => {
  deviceStore.fetchDeviceData()
  experimentStore.fetchCurrentExperiment()
})
</script>

<style scoped>
.DeviceControl {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  width: 100%;
  position: relative;
}

.calibration-switch-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  width: 100%;
  gap: 1em;
  margin-bottom: 1em;
}

.reconnect-btn {
  margin-left: 0.5em;
}

.disconnected-overlay {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: rgba(128, 128, 128, 0.9);
  z-index: 1;
}

.experiment-running-overlay {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: rgba(250, 1, 59, 0.5);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  background-color: rgba(0, 0, 0, 0.8);
  padding: 40px;
  border-radius: 12px;
  border: 2px solid rgba(250, 1, 59, 0.8);
}

.warning-message {
  color: white;
  margin-bottom: 24px;
}

.warning-message h2 {
  margin: 16px 0 8px 0;
  font-size: 1.8rem;
  font-weight: bold;
}

.warning-message p {
  margin: 0;
  font-size: 1.1rem;
  opacity: 0.9;
}

.bypass-button {
  font-size: 1.1rem;
  font-weight: bold;
  min-width: 140px;
}

.centered-text {
  position: fixed;
  top: 50%;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 3em;
  color: rgba(255, 255, 255, 0.5);
  z-index: 2;
  transform: translateY(-80%);
}

.device-disconnected {
  position: relative;
}

.experiment-running-bg {
  background-color: rgba(139, 0, 0, 0.15) !important;
  border: 2px solid rgba(139, 0, 0, 0.3);
  border-radius: 8px;
}
</style>
