<template>
  <div class="stirrer-calibrator" ref="container">
    <div class="elements-container">
      <div v-if="calibrationModeEnabled">
        <input
          type="range"
          class="slider slider-high"
          :class="{ active: currentStirrerState === 'high' }"
          :min=min
          :max=max
          :step=0.01
          v-model="stirrers.calibration[stirrerId].high"
          @change="onSliderChange('high', $event)"
          @input="onSliderInput('high', $event)"
        />
        <input
          type="range"
          class="slider slider-low"
          :class="{ active: currentStirrerState === 'low' }"
          :min=min
          :max=max
          :step=0.01
          v-model="stirrers.calibration[stirrerId].low"
          @change="onSliderChange('low', $event)"
          @input="onSliderInput('low', $event)"
        />


        <svg class="svg-container">
          <line
            :x1="lowX1"
            :y1="lowY1"
            :x2="lowX2"
            :y2="lowY2"
            stroke= "gray"
            stroke-width="1"
          />
          <line
            :x1="highX1"
            :y1="highY1"
            :x2="highX2"
            :y2="highY2"
            stroke="gray"
            stroke-width="1"
          />
        </svg>

      </div>

      <div class="buttons-container">
        <button
          class="button button-high"
          :class="{ active: currentStirrerState === 'high' }"
          ref="buttonHigh"
          @click="onClick('high')"
          @dblclick="onDoubleClick('high')"
        >
          High
        </button>
        <button
          class="button button-low"
          :class="{ active: currentStirrerState === 'low' }"
          ref="buttonLow"
          @click="onClick('low')"
          @dblclick="onDoubleClick('low')"
        >
          Low
        </button>
        <button
          class="button button-off"
          :class="{ active: currentStirrerState === 'stopped' }"
          ref="buttonOff"
          @click="onClick('stopped')"
          @dblclick="onDoubleClick('stopped')"
        >
          Off
        </button>
      </div>
    </div>
  </div>
</template>
<script>
import { mapState, mapActions } from 'vuex';

export default {
  name: "StirrerCalibration",
  props: {
    stirrerId: {
      type: Number,
      required: true
    }
  },
  watch: {
    calibrationModeEnabled(newVal) {
      if (newVal) { // newVal will be true if calibrationModeEnabled has just been set to true
        this.$nextTick(this.updateLine);
      }
    },
  },
  data() {
    return {
      min: 0,
      max: 1,
      lowX1: 0,
      lowY1: 0,
      lowX2: 0,
      lowY2: 0,
      highX1: 0,
      highY1: 0,
      highX2: 0,
      highY2: 0,
      audioContext: new (window.AudioContext || window.webkitAudioContext)()
    };
  },

  // mounted() {
  //     // console.log('mounted stirrer calibration')
  //     // this.lowValue = this.stirrers.calibration[this.stirrerId].low;
  //     // this.highValue = this.stirrers.calibration[this.stirrerId].high;
  // },


  computed: {
    ...mapState('device', ['calibrationModeEnabled', 'stirrers']),
    currentStirrerState() {
      return this.stirrers.states[this.stirrerId];
    },
  },

  methods: {
    ...mapActions('device', ['setPartStateAction', 'setPartCalibrationAction', 'getAllDeviceData', 'setAllStirrersStateAction']),
    onClick(type) {
          this.setPartStateAction({ devicePart: 'stirrers', partIndex: this.stirrerId, newState: type });
},
    onDoubleClick(type) {
      this.setAllStirrersStateAction(type);
    },

    onSliderChange(type, event) {
      if (type === 'low') {
        this.stirrers.calibration[this.stirrerId].low = parseFloat(event.target.value);
      } else if (type === 'high') {
        this.stirrers.calibration[this.stirrerId].high = parseFloat(event.target.value);
      }
      this.setPartCalibrationAction({
        devicePart: 'stirrers',
        partIndex: this.stirrerId,
        newCalibration: {
          low: this.stirrers.calibration[this.stirrerId].low,
          high: this.stirrers.calibration[this.stirrerId].high,
        },
      }).catch((error) => {
        console.error('Error updating stirrer calibration:', error);
      });
    },

    onSliderInput(type, event) {
      if (type === 'low') {
        this.stirrers.calibration[this.stirrerId].low = parseFloat(event.target.value);
      } else if (type === 'high') {
        this.stirrers.calibration[this.stirrerId].high = parseFloat(event.target.value);
      }
      this.updateLine();
        this.playSound(event.target.value);
      },

    updateLine() {
      this.$nextTick(() => {
        const container = this.$refs.container;
        const rectContainer = container.getBoundingClientRect();

        const sliderLow = this.$el.querySelector(".slider-low");
        const buttonLow = this.$refs.buttonLow;
        const rectSliderLow = sliderLow.getBoundingClientRect();
        const rectButtonLow = buttonLow.getBoundingClientRect();

        this.lowX1 = rectSliderLow.x - rectContainer.x + rectSliderLow.width / 2;
        this.lowY1 = rectSliderLow.y - rectContainer.y + rectSliderLow.height * (1 - this.stirrers.calibration[this.stirrerId].low / (this.max - this.min));
        this.lowX2 = rectButtonLow.x - rectContainer.x
        this.lowY2 = rectButtonLow.y - rectContainer.y + rectButtonLow.height / 2;

        const sliderHigh = this.$el.querySelector(".slider-high");
        const buttonHigh = this.$refs.buttonHigh;
        const rectSliderHigh = sliderHigh.getBoundingClientRect();
        const rectButtonHigh = buttonHigh.getBoundingClientRect();

        this.highX1 = rectSliderHigh.x - rectContainer.x + rectSliderHigh.width / 2;
        this.highY1 = rectSliderHigh.y - rectContainer.y + rectSliderHigh.height * (1 - this.stirrers.calibration[this.stirrerId].high / (this.max - this.min));
        this.highX2 = rectButtonHigh.x - rectContainer.x
        this.highY2 = rectButtonHigh.y - rectContainer.y + rectButtonHigh.height / 2;
      });
    },
    playSound(speed) {
      const frequency = 300 + speed * 5;

      const oscillator = this.audioContext.createOscillator();
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);

      const gainNode = this.audioContext.createGain();
      gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      oscillator.start();
      setTimeout(() => {
        oscillator.stop();
      }, 100);
    },  },
};
</script>



<style scoped>
.stirrer-calibrator {
  position: relative;
  padding: 5px;
  width: 100px;
  margin: 5px;
}

.elements-container {
  display: flex;
  justify-content: center;
  /*align-items: ; bottom */
  align-items: flex-end;
  /*height: 300px;*/
}

.slider {
  -webkit-appearance: slider-vertical;
  height: 100%;
  margin: 0 3px;
  width: 10px;
  pointer-events: none;
  opacity: 0.4;
}

.active {
  opacity: 100%;
  pointer-events: all;
  color: #fff; /* And this to the text color you want for active buttons */
}


.button {
  background-color: #4CAF50;
  border: none;
  color: white;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 16px;
  margin: 5px 5px;
  cursor: pointer;
  border-radius: 12px;
  padding: 5px 5px;
  transition-duration: 0.4s;
  opacity: 60%;
}
.active {
  opacity: 100%;
  color: #fff; /* And this to the text color you want for active buttons */
}

.button:hover {
  background-color: #45a049;
  color: white;
}

.button-off {
  background-color: #f44336;
  opacity: 20%;
}
.active {
  opacity: 100%;
  color: #fff; /* And this to the text color you want for active buttons */
}

.button-off:hover {
  background-color: #da190b;
}

.buttons-container {
  display: flex;
  justify-content: space-between;
  flex-direction: column;
}

.svg-container {
  position: absolute;
  opacity: 40%;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: visible;
  z-index: -1;
}


</style>
