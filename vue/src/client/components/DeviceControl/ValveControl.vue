<template>
  <div class="valve-controls">
    <button
      class="btn"
      :class="{
        'btn-danger': valves.states[i] === 'closed' && !togglingValves[i],
        'btn-success': valves.states[i] === 'open' && !togglingValves[i],
        'btn-warning': togglingValves[i]
      }"
      v-for="i in 7"
      :key="i"
      @click="toggleValve(i)"
      :disabled="togglingValves[i]"
    >
      <!-- Conditionally render spinner or valve number -->
      <div v-if="togglingValves[i]" class="spinner-border spinner-custom" role="status"></div>
      <span v-else>Valve {{i}}</span>
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useDeviceStore } from '../../stores/device'

const deviceStore = useDeviceStore()
const { valves } = storeToRefs(deviceStore)

const togglingValves = ref({})

const audioContext = new (window.AudioContext || window.webkitAudioContext)()

function playValveSound(valveState) {
  const startFrequency = valveState === 'open' ? 500 : 300
  const endFrequency = valveState === 'open' ? 300 : 500

  const oscillator = audioContext.createOscillator()
  oscillator.type = 'sine'

  const gainNode = audioContext.createGain()
  gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)

  oscillator.connect(gainNode)
  gainNode.connect(audioContext.destination)

  oscillator.frequency.setValueAtTime(startFrequency, audioContext.currentTime)
  oscillator.frequency.linearRampToValueAtTime(endFrequency, audioContext.currentTime + 0.3)

  oscillator.start()
  oscillator.stop(audioContext.currentTime + 0.3)

  return oscillator
}

async function toggleValve(valveIndex) {
  const currentState = valves.value.states[valveIndex]

  if (togglingValves.value[valveIndex]) {
    return
  }
  togglingValves.value = { ...togglingValves.value, [valveIndex]: true }

  const oscillator = playValveSound(currentState)

  try {
    await deviceStore.setPartStateAction({
      devicePart: 'valves',
      partIndex: valveIndex,
      newState: currentState === 'open' ? 'closed' : 'open',
    })
    oscillator.stop()
  } catch (error) {
    console.error(error)
  } finally {
    togglingValves.value = { ...togglingValves.value, [valveIndex]: false }
  }
}
</script>

<style scoped>
.valve-controls {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  width: 850px;
  margin: 0 auto;
  /*margin-top: 10px;*/
}

.btn-danger, .btn-success{
  font-size: 20px;
  padding: 10px;
  width: 90px;
  text-align: center;
  margin: 10px;
  box-shadow: 0px 5px 10px rgba(0, 0, 0, 0.2);
  border: 2px solid red;
  border-radius: 10px;
}

.btn-warning {
  font-size: 20px;
  padding: 10px;
  width: 90px;
  text-align: center;
  margin: 10px;
  background-color: #ffde17 !important;
  color: black;
  border-radius: 10px;

}


.btn-danger {
  background-color: red;
  color: rgb(255, 255, 255);
  border-color: red;
}

.btn-success {
  background-color: green;
  color: white;
  border-color: green;
}


.btn-danger, .btn-success, .btn-warning:hover {
  cursor: pointer;
  opacity: 0.8;
}

.spinner-custom {
  width: 1.5rem;
  height: 1.5rem;
  border-width: 0.2rem;
}
</style>
