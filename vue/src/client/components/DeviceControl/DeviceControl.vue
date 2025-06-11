<template>
  <div class="DeviceControl" :class="{ 'device-disconnected': deviceConnected === false }">
<!--    <div class="disconnected-overlay" v-if="deviceConnected === false"></div>-->
<!--    <div v-if="deviceConnected === false" class="centered-text"> device connection not available </div>-->
    <div class="experiment-running-overlay" v-if="deviceControlEnabled === false"></div>
    <div class="calibration-switch-row">
      <template v-if="calibrationModeEnabled">
        <v-btn class="reconnect-btn" @click="onReconnectClick">Reconnect Device</v-btn>
      </template>
      <v-switch
        v-model="calibrationMode"
        label="Calibration Mode"
      ></v-switch>
    </div>

    <template v-if="deviceControlEnabled || controlsVisible">
      <PumpControl />
      <ValveControl />
      <StirrerControl />
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
import { computed, onMounted, ref } from 'vue'
import PumpControl from './PumpControl.vue';
import ValveControl from './ValveControl.vue';
import StirrerControl from './StirrerControl.vue';
import ODControl from './ODControl.vue';
import LEDControl from "./LEDControl.vue";
import DeviceConfigs from "./DeviceConfigs.vue";
import { useDialog } from '@/client/composables/useDialog'
import { toast } from 'vue3-toastify';

const deviceStore = useDeviceStore()
const {
  deviceConnected,
  deviceControlEnabled,
  calibrationModeEnabled,
  stirrers,
  pumps,
  valves,
  ods
} = storeToRefs(deviceStore)

const controlsVisible = computed(() => deviceControlEnabled.value)

const calibrationMode = computed({
  get: () => calibrationModeEnabled.value,
  set: (val) => deviceStore.setCalibrationModeEnabled(val)
})

const { openDialog } = useDialog()

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
  z-index: 1;
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
</style>
