<template>
  <div class="pump-controls">
    <div class="pump" v-for="i in [1,2,4]" :key="i">
      <v-btn
        class="pump-button"
        :class="{ 'stop-button': pumps.states[i] === 'running' }"
        @click="handlePumpClick(i)"
      >
        <v-progress-circular
          v-if="pumps.states[i] === 'running'"
          indeterminate
          color="white"
          class="spinner-custom"
        ></v-progress-circular>
        <span v-else>{{pump_names[i]}}<br>pump</span>
      </v-btn>

      <div class="pump-input">
        <v-text-field
          label="Volume (mL)"
          type="number"
          dense
          v-model="volume[i]"
          @update:modelValue="onVolumeInput($event, i)"
        ></v-text-field>

        <v-text-field
          v-if="calibrationModeEnabled"
          label="Rotations"
          type="number"
          dense
          v-model="rotations[i]"
          @update:modelValue="onRotationsInput($event, i)"
        ></v-text-field>

        <PumpCalibration v-if="calibrationModeEnabled" :pumpId="i" />
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import PumpCalibration from '@/client/components/DeviceControl/PumpCalibration.vue';
import { VBtn, VTextField, VProgressCircular } from 'vuetify/components';

export default {
  components: {
    PumpCalibration,
    VBtn,
    VTextField,
    VProgressCircular,
  },
  name: 'PumpControl',
  data() {
    return {
      pump_names: {
        1: 'MAIN',
        2: 'DRUG',
        3: 'MISSING!!!',
        4: 'WASTE'
      },
      rotations: { 1: null, 2: null, 3: null, 4: null },
      volume: { 1: null, 2: null, 3: null, 4: null },
    };
  },
  computed: {
    ...mapState('device', ['pumps', 'valves', 'calibrationModeEnabled']),
  },
  methods: {
    ...mapActions('device', ['setPartStateAction']),
    async handlePumpClick(pumpId) {
      if (this.pumps.states[pumpId] === 'running') {
        await this.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'stopped' });
        return;
      }

      const isValveOpen = Object.values(this.valves.states).some((valve) => valve === 'open');

      if (!isValveOpen) {
        alert('At least one valve must be open to start the pump');
        return;
      }

      const volume = parseFloat(this.volume[pumpId]);

      if (!volume) {
        alert('Please set the volume before starting the pump');
        return;
      }

      try {
        await this.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'running', input: { volume } });
      } catch (error) {
        console.error(error);
      } finally {
        await this.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'stopped' });
      }
    },
    onVolumeInput(event, pumpId) {
      this.volume[pumpId] = event;
      const volume = parseFloat(this.volume[pumpId]);
      if (!isNaN(volume)) {
        this.rotations[pumpId] = this.calculateRotations(volume, pumpId).toFixed(2);
      } else {
        this.rotations[pumpId] = '';
      }
    },
    onRotationsInput(event, pumpId) {
      this.rotations[pumpId] = event;
      const rotations = parseFloat(this.rotations[pumpId]);
      if (!isNaN(rotations)) {
        this.volume[pumpId] = this.calculateVolume(rotations, pumpId);
      } else {
        this.volume[pumpId] = '';
      }
    },

    calculateRotations(volume, pumpId) {
      const pumpCoefficients = this.pumps.calibration[pumpId];
      const points = Object.entries(pumpCoefficients).map(([rot, coef]) => [parseInt(rot), coef]).sort((a, b) => a[0] - b[0]);

      if (volume >= points[points.length - 1][0] * points[points.length - 1][1]) {
        return volume / points[points.length - 1][1];
      }

      let lowerPoint = points[0];
      let upperPoint = points[points.length - 1];
      for (let i = 0; i < points.length - 1; i++) {
        if (volume >= points[i][0] * points[i][1] && volume <= points[i + 1][0] * points[i + 1][1]) {
          lowerPoint = points[i];
          upperPoint = points[i + 1];
          break;
        }
      }

      const lowerVolume = lowerPoint[0] * lowerPoint[1];
      const upperVolume = upperPoint[0] * upperPoint[1];
      const factor = (volume - lowerVolume) / (upperVolume - lowerVolume);

      const interpolatedCoefficient = lowerPoint[1] + (upperPoint[1] - lowerPoint[1]) * factor;

      return volume / interpolatedCoefficient;
    },

    calculateVolume(rotations, pumpId) {
      const pumpCoefficients = this.pumps.calibration[pumpId];
      const points = Object.entries(pumpCoefficients).map(([rot, coef]) => [parseInt(rot), coef]).sort((a, b) => a[0] - b[0]);

      if (rotations >= points[points.length - 1][0]) {
        return (rotations * points[points.length - 1][1]).toFixed(2);
      }

      let lowerPoint = points[0];
      let upperPoint = points[points.length - 1];
      for (let i = 0; i < points.length - 1; i++) {
        if (rotations >= points[i][0] && rotations <= points[i + 1][0]) {
          lowerPoint = points[i];
          upperPoint = points[i + 1];
          break;
        }
      }

      const factor = (rotations - lowerPoint[0]) / (upperPoint[0] - lowerPoint[0]);

      const interpolatedCoefficient = lowerPoint[1] + (upperPoint[1] - lowerPoint[1]) * factor;

      return (rotations * interpolatedCoefficient).toFixed(2);
    },
  },
};
</script>

<style scoped>
.pump-input {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.pump-button {
  margin-bottom: 20px;
  background-color: blue;
  color: white;
  font-size: 20px;
  padding: 10px;
  width: 160px;
  height: 160px;
  text-align: center;
  border-radius: 50%;
  box-shadow: 0px 5px 10px rgba(0, 0, 0, 0.5);
}

.pump-button.stop-button {
  background-color: red;
  color: white;
}

.pump-controls {
  display: flex;
  flex-wrap: wrap; /* Allow wrapping if needed for narrow screens */
  flex-direction: row; /* Arrange pumps horizontally */
  justify-content: space-evenly; /* Distribute pumps evenly across the container */
  width: 100%; /* Use full width of the container */
  max-width: 800px; /* Optional: Limit maximum width */
  margin: 0 auto; /* Center container within the page */
  gap: 10px; /* Add spacing between pumps */
}


.pump {
  flex: 1 1 auto; /* Allow pumps to shrink or grow as needed */
  display: flex;
  flex-direction: column; /* Keep individual pump items aligned vertically */
  align-items: center;
  min-width: 180px; /* Ensure consistent sizing */
  max-width: 250px; /* Prevent pumps from being too wide */
  margin: 10px; /* Add spacing around each pump */
}

.spinner-custom {
  width: 48px;
  height: 48px;
}
</style>
