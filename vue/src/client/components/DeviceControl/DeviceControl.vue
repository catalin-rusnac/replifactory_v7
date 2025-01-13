<template>
  <div class="DeviceControl" :class="{ 'device-disconnected': deviceConnected === false }">
<!--    <div class="disconnected-overlay" v-if="deviceConnected === false"></div>-->
<!--    <div v-if="deviceConnected === false" class="centered-text"> device connection not available </div>-->
    <div class="experiment-running-overlay" v-if="deviceControlEnabled === false"></div>
    <div class="calibration-switch" style="text-align: right;">
      <v-switch
        v-model="calibrationModeEnabled"
        label="Calibration Mode"
        @change="toggleCalibrationMode"
      ></v-switch>
    </div>

    <template v-if="deviceControlEnabled || controlsVisible">
      <PumpControl />
      <ValveControl />
      <StirrerControl />
      <ODControl />
      <LEDControl />
    </template>

    <template v-else>
      <p>Device Control Disabled - please pause experiment to control device.</p>
    </template>
  </div>
</template>

<script>
import PumpControl from './PumpControl.vue';
import ValveControl from './ValveControl.vue';
import StirrerControl from './StirrerControl.vue';
import ODControl from './ODControl.vue';
import LEDControl from "./LEDControl.vue";
import { mapState, mapMutations, mapActions } from 'vuex';

export default {
  components: {
    PumpControl,
    ValveControl,
    StirrerControl,
    ODControl,
    LEDControl,
  },
  computed: {
    ...mapState(['deviceConnected', 'deviceControlEnabled']),
    ...mapState('device', ['calibrationModeEnabled', 'stirrers', 'pumps', 'valves', 'ods']),
  },
  data() {
    return {
      controlsVisible: false,
    };
  },
  watch: {
    deviceControlEnabled(newVal) {
      this.controlsVisible = newVal;
    },
  },
  mounted() {
    // if not connected, try to connect
    if (!this.deviceConnected) {
      this.connectDevice().then(() => {
        this.getAllDeviceData();
      });
    }
  },
  methods: {
    ...mapMutations('device', ['toggleCalibrationMode', 'setDeviceControlEnabled']),
    ...mapActions('device', ['getAllDeviceData']),
    ...mapActions(['connectDevice']),
  },
};
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

.calibration-switch {
  left: 50%;
  transform: translateX(calc(min(400px, 90vw)));
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
