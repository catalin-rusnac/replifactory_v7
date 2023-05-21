<template>
  <div class="DeviceControl" :class="{ 'device-disconnected': deviceConnected === false }">
  <div class="disconnected-overlay" v-if="deviceConnected === false"></div>
  <div style="text-align: right;">
    <CFormSwitch
      label="Calibration Mode"
      id="formSwitchCheckChecked"
      v-model="calibrationModeEnabled"
      @change="toggleCalibrationMode" />
  </div>

    <template v-if="deviceControlEnabled || controlsVisible">
      <PumpControl />
      <ValveControl />
      <StirrerControl />
      <ODControl />
    </template>

    <template v-else>
      <p>Device Control Disabled - please pause experiment to control device.</p>
    </template>
  </div>
</template>


<script>
import PumpControl from './PumpControl';
import ValveControl from './ValveControl';
import StirrerControl from './StirrerControl';
import ODControl from './ODControl';
import {mapState, mapMutations, mapActions} from 'vuex';
import { CFormSwitch } from '@coreui/vue';



export default {
  components: {
    PumpControl,
    ValveControl,
    StirrerControl,
    ODControl,
    CFormSwitch
  },
  computed: {
    ...mapState(['deviceConnected', 'deviceControlEnabled']),
    ...mapState('device', ['calibrationModeEnabled','stirrers','pumps','valves','ods'])
  },
  data() {
    return {
      controlsVisible: false,};
  },
  watch: {
    deviceControlEnabled(newVal) {
      if (newVal) {
        this.controlsVisible = true;
      } else {
        this.controlsVisible = false;
      }
    },
  },
  mounted() {
    // if not connected, try to connect
    if (!this.deviceConnected) {
      this.connectDevice().then(() => {
        this.getAllDeviceData().then(() => {
        });
      });
    }
  },
  methods: {
    ...mapMutations('device',['toggleCalibrationMode', 'setDeviceControlEnabled']),
    ...mapActions('device',['getAllDeviceData']),
    ...mapActions(['connectDevice']),
  },
};
</script>

<style scoped>
.disconnected-overlay {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: rgba(128, 128, 128, 0.9); /* gray with 50% opacity */
  z-index: 1; /* to ensure the overlay is on top */
}

.device-disconnected {
  position: relative; /* this is needed to position the overlay correctly */
}

</style>