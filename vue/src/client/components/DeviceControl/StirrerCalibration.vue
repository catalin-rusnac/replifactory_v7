<template>
  <div class="stirrer-calibrator" ref="container">
    <div class="elements-container">
      <div class="stirrer-name">
        <header>Stirrer {{ stirrerId }}</header>
      </div>

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
          OFF
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
      audioContext: new (window.AudioContext || window.webkitAudioContext)(),
      oscillator: null,
      gainNode:null,
      stopSoundTimeout: null,
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
    // If an oscillator is not already set up
    if (!this.oscillator) {
      this.oscillator = this.audioContext.createOscillator();
      this.gainNode = this.audioContext.createGain();

      this.oscillator.type = 'sine';
      this.gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);
      this.oscillator.connect(this.gainNode);
      this.gainNode.connect(this.audioContext.destination);
      this.oscillator.start();
    }

    const frequency = 300 + speed * 500;
    this.oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);

    // Clear any previous stopSound timeout
    if (this.stopSoundTimeout) {
      clearTimeout(this.stopSoundTimeout);
    }

    // Set a new timeout to stop the sound in 0.3 seconds
    this.stopSoundTimeout = setTimeout(this.stopSound, 200);
  },

  // Call this method when you want to stop the sound
  stopSound() {
    if (this.oscillator) {
      this.gainNode.gain.exponentialRampToValueAtTime(0.001, this.audioContext.currentTime + 0.01);
      this.gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime + 0.02);
      this.oscillator.stop(this.audioContext.currentTime + 0.02);
      this.oscillator = null;
      this.gainNode = null;
    }
  }

  },
};
</script>


<!--<style>-->
<!--body {-->
<!--  background-color: #242424; /* or any dark color you prefer */-->
<!--  /*color: white; !* this is the color for the general text on the page *!*/-->
<!--}-->
<!--</style>-->

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
  padding-top: 20px;
  /*align-items: ; bottom */
  align-items: flex-end;
  //height: 100px;
  border: 1px solid #e3e3e3; /* Sets the color of the border */
  border-radius: 10px; /* Adjust as needed to create the level of roundness you desire */
}

.slider {
  height: 10%;
  margin: 0 3px;
  width: 10px;
  pointer-events: none;
  opacity: 0.4;
  writing-mode: vertical-lr;
  direction: rtl;
}

.active {
  opacity: 100%;
  pointer-events: all;
  color: #fff; /* And this to the text color you want for active buttons */
}

.button {
  background-color: transparent;
  border: 1px solid #3aab40; /* green border */
  color: #3aab40; /* green text */
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  margin: 8px 5px;
  cursor: pointer;
  border-radius: 8px;
  padding: 5px 5px;
  transition-duration: 0.4s;
  opacity: 60%;
  box-shadow: 0px 3px 5px rgba(0, 0, 0, 0.2);
}

.button:hover {
  opacity:80%;
}

.button-off {
  background-color: transparent;
  border: 1px solid #da190b; /* red border */
  color: #da190b; /* red text */
  opacity: 40%;
}

.button-off:hover {
  background-color: #da190b;
  opacity:60%;
}

.active {
  opacity: 100%;
  color: #fff; /* white text for active buttons */
  background-color: #3aab40; /* green background for active buttons */
}

.button-off.active {
  background-color: #da190b; /* red background for active off button */
}

.button:hover, .button-off:hover, .active:hover {
  opacity: 100%; /* 100% opacity on hover for all buttons */
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

.stirrer-name {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translate(-50%, -50%); /* This centers the header */
  z-index: -1; /* This ensures the header is above everything else */
  color: #9b9b9b; /* Color of the text */
  font-size: 14px; /* Adjust as needed */
}

</style>
