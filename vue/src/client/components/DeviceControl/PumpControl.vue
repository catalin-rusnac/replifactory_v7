<template>
  <div class="pump-controls">
    <div class="pump" v-for="i in [1,2,4]" :key="i">
      <button class="pump-button"
              :class="{ 'stop-button': pumps.states[i] === 'running' }"
              @click="handlePumpClick(i)">
        <div v-if="pumps.states[i] === 'running'" class="spinner-border spinner-custom" role="status"></div>
        <span v-else>{{pump_names[i]}}<br>pump</span>
<!--        <span v-if="pumps.states[i] === 'running'">Stop</span>-->
      </button>
<!--      <input v-model="pumps.input[i].volume" class="volume" placeholder="Volume">-->
      <div class="pump-input">
        <div class="form-group">
            <CFormInput id="volume" placeholder="volume (mL)" type="number" size="lg" :value="volume[i]" @input="event => onVolumeInput(event, i)" />
        </div>

        <div v-if="calibrationModeEnabled" class="form-group">
          <CFormInput id="rotations" placeholder="rotations" type="float" size="sm" :value="rotations[i]" @input="event => onRotationsInput(event, i)" />
          <label for="calibration">Calibration:</label>
          <PumpCalibration :pumpId="i" />
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
      pump_names: {
        1: 'MAIN',
        2: 'DRUG',
        3: 'MISSING!!!',
        4: 'WASTE'
      },
      rotations: {1:null, 2:null, 3:null, 4:null},
      volume: {1:null, 2:null, 3:null, 4:null},
  }},
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

      // Check if at least one valve is open
      console.log("handlePumpClick, pumpId: " + pumpId);
      const isValveOpen = Object.values(this.valves.states).some((valve) => valve === 'open');

      if (!isValveOpen) {
        alert('At least one valve must be open to start the pump');
        return;
      }

      // Ensure volume is set
      const volume = parseFloat(this.volume[pumpId]);

      console.log("volume: " + volume);
      if (!volume) {
        alert('Please set the volume before starting the pump');
        return;
      }

      try {
        await this.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'running', input: {volume: volume}});
        // Send a POST request to the Flask endpoint with the specified pump ID and volume
      } catch (error) {
        // Handle any errors here
        console.error(error);
      } finally {
        await this.setPartStateAction({ devicePart: 'pumps', partIndex: pumpId, newState: 'stopped' });
      }
    },
    onVolumeInput(event, pumpId) {
      this.volume[pumpId] = event.target.value;
      const volume = parseFloat(this.volume[pumpId]);
      if (!isNaN(volume)) {
        this.rotations[pumpId] = this.calculateRotations(volume,pumpId).toFixed(2);
      } else {
        this.rotations[pumpId] = '';
      }
    },
    onRotationsInput(event, pumpId) {
      this.rotations[pumpId] = event.target.value;
      const rotations = parseFloat(this.rotations[pumpId]);
      if (!isNaN(rotations)) {
        this.volume[pumpId] = this.calculateVolume(rotations,pumpId);
      } else {
        this.volume[pumpId] = '';
      }
    },

  calculateRotations(volume, pumpId) {
    // Get the coefficients for the given pumpId
    const pumpCoefficients = this.pumps.calibration[pumpId];
    // Convert the coefficients into an array of [rotations, coefficient] pairs
    const points = Object.entries(pumpCoefficients).map(([rot, coef]) => [parseInt(rot), coef]).sort((a, b) => a[0] - b[0]);

    // If volume is larger than the largest known, use the largest coefficient
    if (volume >= points[points.length - 1][0] * points[points.length - 1][1]) {
      return (volume / points[points.length - 1][1]);
    }

    // Find the two points surrounding the given volume
    let lowerPoint = points[0];
    let upperPoint = points[points.length - 1];
    for (let i = 0; i < points.length - 1; i++) {
      if (volume >= points[i][0] * points[i][1] && volume <= points[i + 1][0] * points[i + 1][1]) {
        lowerPoint = points[i];
        upperPoint = points[i + 1];
        break;
      }
    }

    // Calculate the interpolation factor
    const lowerVolume = lowerPoint[0] * lowerPoint[1];
    const upperVolume = upperPoint[0] * upperPoint[1];
    const factor = (volume - lowerVolume) / (upperVolume - lowerVolume);

    // Interpolate the coefficient
    const interpolatedCoefficient = lowerPoint[1] + (upperPoint[1] - lowerPoint[1]) * factor;

    // Calculate the rotations
    const rotations = volume / interpolatedCoefficient;

    return rotations;
  },



calculateVolume(rotations, pumpId) {
  // Get the coefficients for the given pumpId
  const pumpCoefficients = this.pumps.calibration[pumpId];
  // Convert the coefficients into an array of [rotations, coefficient] pairs
  const points = Object.entries(pumpCoefficients).map(([rot, coef]) => [parseInt(rot), coef]).sort((a, b) => a[0] - b[0]);

  // If rotations is more than the largest known, use the largest coefficient
  if (rotations >= points[points.length - 1][0]) {
    return (rotations * points[points.length - 1][1]).toFixed(2);
  }

  // Find the two points surrounding the given number of rotations
  let lowerPoint = points[0];
  let upperPoint = points[points.length - 1];
  for (let i = 0; i < points.length - 1; i++) {
    if (rotations >= points[i][0] && rotations <= points[i + 1][0]) {
      lowerPoint = points[i];
      upperPoint = points[i + 1];
      break;
    }
  }

  // Calculate the interpolation factor
  const factor = (rotations - lowerPoint[0]) / (upperPoint[0] - lowerPoint[0]);

  // Interpolate the coefficient
  const interpolatedCoefficient = lowerPoint[1] + (upperPoint[1] - lowerPoint[1]) * factor;

  // Calculate the volume
  const volume = rotations * interpolatedCoefficient;

  return volume.toFixed(2);
},
  },
}
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
  animation: spinner-border 0.95s linear infinite;
}


.pump-button {
  margin-bottom: 20px;
  background-color: blue;
  color: white;
  font-size: 20px;
  padding: 10px;
  width: 130px;  /* Adjust as needed */
  height: 130px;  /* Adjust as needed */
  text-align: center;
  border-radius: 50%;  /* This makes the button round */
  box-shadow: 0px 5px 10px rgba(0, 0, 0, 0.5);
}

.pump-button.stop-button {
  background-color: red;
  color: white;
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
