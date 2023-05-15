<template>
  <div class="DeviceControl">
    <label>
      Calibration mode:
      <input type="checkbox" :checked="calibrationModeEnabled" @change="toggleCalibrationMode" />
    </label>
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



export default {
  components: {
    PumpControl,
    ValveControl,
    StirrerControl,
    ODControl,
  },
  computed: {
    ...mapState('device', ['deviceConnected','deviceControlEnabled','calibrationModeEnabled','stirrers','pumps','valves','ods'])
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
    ...mapActions('device',['connectDevice','getAllDeviceData']),
  },
};
</script>

<style scoped>
  .row{
    max-width: 1024px;
    margin: 0 auto;
  }
</style>