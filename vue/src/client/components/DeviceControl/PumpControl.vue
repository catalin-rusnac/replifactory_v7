<template>
  <div class="pump-controls">
    <div class="pump" v-for="i in 3" :key="i">
      <button class="pump-button" @click="handlePumpClick(i)" :disabled="pumps.states[i] === 'running'">
        <div v-if="pumps.states[i] === 'running'" class="spinner-border spinner-custom" role="status"></div>
        <span v-else>Run Pump {{i}}</span>
      </button>
<!--      <input v-model="pumps.input[i].volume" class="volume" placeholder="Volume">-->
      <div class="pump-input">
        <div class="form-group">
          <label for="volume">Volume (ml):</label>
          <CFormInput id="volume" type="float" size="lg" :value="pumps.volume[i]" @input="event => onVolumeInput(event, i)" />
        </div>

        <div v-if="calibrationModeEnabled" class="form-group">
          <label for="calibration">Calibration:</label>
          <PumpCalibration :pumpId="i" />
        </div>
        <div class="form-group">
          <label for="rotations">Pump rotations:</label>
          <CFormInput id="rotations" type="float" size="sm" :value="rotations[i]" @input="event => onRotationsInput(event, i)" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {mapActions, mapState} from 'vuex';
import {CFormInput} from "@coreui/vue";
import PumpCalibration from "@/client/components/DeviceControl/PumpCalibration";


export default {
  components: {
    PumpCalibration,
    CFormInput
  },
  name: 'PumpControl',
  data() {
    return {
      rotations: {1: 0, 2: 0, 3: 0}};
  },
  computed: {
    ...mapState('device', ['pumps', 'valves', 'calibrationModeEnabled']),
  },
  methods: {
    ...mapActions('device', ['setPartStateAction']),
    async handlePumpClick(pumpId) {
      // Check if at least one valve is open
      const isValveOpen = Object.values(this.valves.states).some((valve) => valve === 'open');

      if (!isValveOpen) {
        alert('At least one valve must be open to start the pump');
        return;
      }

      // Ensure volume is set
      const volume = this.pumps.input[pumpId].volume;
      if (!volume) {
        alert('Please set the volume before starting the pump');
        return;
      }

      try {
        await this.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'running', input: this.pumps.input[pumpId] });

        // Send a POST request to the Flask endpoint with the specified pump ID and volume
      } catch (error) {
        // Handle any errors here
        console.error(error);
      } finally {
        await this.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'stopped' });
      }
    },
    onVolumeInput(event, pumpId) {
      this.volume = event.target.value;
      const volume = parseFloat(this.volume);
      if (!isNaN(volume)) {
        this.rotations[pumpId] = this.calculateRotations(volume,pumpId).toString();
      } else {
        this.rotations[pumpId] = '';
      }
    },
    onRotationsInput(event, pumpId) {
      this.rotations[pumpId] = event.target.value;
      const rotations = parseFloat(this.rotations[pumpId]);
      if (!isNaN(rotations)) {
        this.pumps.volume[pumpId] = this.calculateVolume(rotations,pumpId).toString();
      } else {
        this.pumps.volume[pumpId] = '';
      }
    },

  calculateRotations(volume, pumpId) {
    // Get the coefficients for the given pumpId
    const pumpCoefficients = this.pumps.calibration[pumpId];
    // Convert the coefficients into an array of [volume, coefficient] pairs
    const points = Object.entries(pumpCoefficients).map(([vol, coef]) => [parseInt(vol), coef]).sort((a, b) => a[0] - b[0]);

    // Find the two points surrounding the given volume
    let lowerPoint = points[0];
    let upperPoint = points[points.length - 1];
    for (let i = 0; i < points.length - 1; i++) {
      if (volume >= points[i][0] && volume <= points[i + 1][0]) {
        lowerPoint = points[i];
        upperPoint = points[i + 1];
        break;
      }
    }

    // Calculate the interpolation factor
    const factor = (volume - lowerPoint[0]) / (upperPoint[0] - lowerPoint[0]);

    // Interpolate the coefficient
    const interpolatedCoefficient = lowerPoint[1] + (upperPoint[1] - lowerPoint[1]) * factor;

    // Calculate the rotations
    const rotations = volume / interpolatedCoefficient;

    return rotations;
  },


    calculateVolume(rotations,pumpId) {
      //coefficients= {1:0.2, 5:0.19,10:0.17, 50:0.16}
      //interpolate rotations between coefficients and calculate correction_coefficient
      const coefficients = this.pumps.calibration[pumpId];
      let correction_coefficient = 0;
      if (rotations < 1) {
        correction_coefficient = coefficients[1];
      } else if (rotations < 5) {
        correction_coefficient = coefficients[1] + (rotations - 1) * (coefficients[5] - coefficients[1]) / 4;
      } else if (rotations < 10) {
        correction_coefficient = coefficients[5] + (rotations - 5) * (coefficients[10] - coefficients[5]) / 5;
      } else if (rotations < 50) {
        correction_coefficient = coefficients[10] + (rotations - 10) * (coefficients[50] - coefficients[10]) / 40;
      } else {
        correction_coefficient = coefficients[50];
      }
      const volume = rotations * correction_coefficient
      return volume.toFixed(2);
    }
  },
};
</script>



<style scoped>

.pump-input {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.form-group {
  width: 200px;
  margin-bottom: 10px;
}


label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.spinner-custom {
  width: 5rem;
  height: 5rem;
  border-width: 0.5rem;
}

.pump-button {
  background-color: blue;
  color: white;
  font-size: 20px;
  padding: 10px;
  width: 150px;  /* Adjust as needed */
  height: 150px;  /* Adjust as needed */
  text-align: center;
  border-radius: 50%;  /* This makes the button round */
}

.pump-controls {
  display: flex;
  justify-content: center;
  width: 800px;
  margin: 0 auto;
}

.pump {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0 auto;
}

.pump input {
  width: 750px;
  padding: 0px;
  text-align: center;
  margin-top: 10px;  /* Adds a little space between the button and the input */
}

</style>
