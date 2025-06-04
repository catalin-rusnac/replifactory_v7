<template>
  <div class="stirrer-calibrator" ref="container">
    <div class="elements-container">
      <div class="stirrer-name">
        <header>Stirrer {{ stirrerId }}</header>
      </div>
      <div v-if="calibrationModeEnabled && stirrers && stirrers.calibration && stirrers.calibration[stirrerId]">
        <div style="position: relative; display: inline-block;">
          <input
            type="range"
            class="slider slider-high"
            :class="[{ active: currentStirrerState === 'high' }, { 'slider-disabled': currentStirrerState !== 'high' }]"
            :min="min"
            :max="max"
            :step="0.01"
            v-model.number="stirrers.calibration[stirrerId].high"
            @input="onSliderInput('high', $event)"
            @change="onSliderChange('high', $event)"
          />
          <div
            v-if="currentStirrerState !== 'high'"
            class="slider-overlay"
            @click="onSliderAttempt('high', $event)"
          ></div>
        </div>
        <div style="position: relative; display: inline-block;">
          <input
            type="range"
            class="slider slider-low"
            :class="[{ active: currentStirrerState === 'low' }, { 'slider-disabled': currentStirrerState !== 'low' }]"
            :min="min"
            :max="max"
            :step="0.01"
            v-model.number="stirrers.calibration[stirrerId].low"
            @input="onSliderInput('low', $event)"
            @change="onSliderChange('low', $event)"
          />
          <div
            v-if="currentStirrerState !== 'low'"
            class="slider-overlay"
            @click="onSliderAttempt('low', $event)"
          ></div>
        </div>
      </div>
      <div class="buttons-container">
        <button
          class="button button-high"
          :class="{ active: currentStirrerState === 'high' }"
          ref="buttonHigh"
          @click="setState('high')"
          @dblclick="onDoubleClick('high')"
        >High</button>
        <button
          class="button button-low"
          :class="{ active: currentStirrerState === 'low' }"
          ref="buttonLow"
          @click="setState('low')"
          @dblclick="onDoubleClick('low')"
        >Low</button>
        <button
          class="button button-off"
          :class="{ active: currentStirrerState === 'stopped' }"
          ref="buttonOff"
          @click="setState('stopped')"
          @dblclick="onDoubleClick('stopped')"
        >OFF</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { useDeviceStore } from '../../stores/device'
import { toast } from 'vue3-toastify';
import 'vue3-toastify/dist/index.css';

const props = defineProps({
  stirrerId: { type: Number, required: true }
})

const min = 0
const max = 1

const container = ref(null)
const buttonHigh = ref(null)
const buttonLow = ref(null)

const audioContext = new (window.AudioContext || window.webkitAudioContext)()
let oscillator = null
let gainNode = null
let stopSoundTimeout = null

const deviceStore = useDeviceStore()
const { calibrationModeEnabled, stirrers } = storeToRefs(deviceStore)

const currentStirrerState = computed(() =>
  stirrers.value && stirrers.value.states
    ? stirrers.value.states[props.stirrerId]
    : undefined
)

function setState(type) {
  deviceStore.setPartStateAction({ devicePart: 'stirrers', partIndex: props.stirrerId, newState: type })
}

function onDoubleClick(type) {
  if (stirrers.value && stirrers.value.states) {
    for (let i = 1; i <= 7; i++) {
      stirrers.value.states[i] = type
    }
  }
  if (deviceStore.setAllStirrersStateAction) {
    deviceStore.setAllStirrersStateAction(type)
  }
}

function onSliderInput(type, event) {
  playSound(event.target.value)
}

function onSliderChange(type, event) {
  if (!stirrers.value || !stirrers.value.calibration || !stirrers.value.calibration[props.stirrerId]) return;
  deviceStore.setPartCalibrationAction({
    devicePart: 'stirrers',
    partIndex: props.stirrerId,
    newCalibration: {
      low: stirrers.value.calibration[props.stirrerId].low,
      high: stirrers.value.calibration[props.stirrerId].high,
    },
  }).catch((error) => {
    console.error('Error updating stirrer calibration:', error)
  })
}

function playSound(speed) {
  if (!oscillator) {
    oscillator = audioContext.createOscillator()
    gainNode = audioContext.createGain()
    oscillator.type = 'sine'
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)
    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)
    oscillator.start()
  }
  const frequency = 300 + speed * 500
  oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime)
  if (stopSoundTimeout) {
    clearTimeout(stopSoundTimeout)
  }
  stopSoundTimeout = setTimeout(stopSound, 200)
}

function stopSound() {
  if (oscillator) {
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.01)
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime + 0.02)
    oscillator.stop(audioContext.currentTime + 0.02)
    oscillator = null
    gainNode = null
  }
}

function onSliderAttempt(type, event) {
  if ((type === 'high' && currentStirrerState.value !== 'high') || (type === 'low' && currentStirrerState.value !== 'low')) {
    event.preventDefault()
    toast('Enable stirrer to adjust speed', { type: 'info' })
  }
}

onMounted(() => {
  window.addEventListener('resize', () => {})
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', () => {})
})
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
  padding-top: 20px;
  align-items: flex-end;
  border: 1px solid #e3e3e3;
  border-radius: 10px;
  position: relative;
}
.slider {
  height: 100px;
  margin: 0 3px;
  width: 10px;
  writing-mode: vertical-lr;
  direction: rtl;
}
.active {
  opacity: 100%;
  pointer-events: all;
  color: #fff;
}
.button {
  background-color: transparent;
  border: 1px solid #3aab40;
  color: #3aab40;
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
  border: 1px solid #da190b;
  color: #da190b;
  opacity: 40%;
}
.button-off:hover {
  background-color: #da190b;
  opacity:60%;
}
.active {
  opacity: 100%;
  color: #fff;
  background-color: #3aab40;
}
.button-off.active {
  background-color: #da190b;
}
.button:hover, .button-off:hover, .active:hover {
  opacity: 100%;
}
.buttons-container {
  display: flex;
  justify-content: space-between;
  flex-direction: column;
}
.stirrer-name {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translate(-50%, -80%);
  z-index: 1;
  color: #636363;
  font-size: 12px;
}
.slider-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
  background: transparent;
  cursor: not-allowed;
}
.slider-disabled {
  filter: grayscale(1);
  opacity: 0.4;
  pointer-events: none;
}
</style>
