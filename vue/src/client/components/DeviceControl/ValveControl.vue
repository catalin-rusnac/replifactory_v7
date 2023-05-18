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
<script>
import { mapState, mapActions } from 'vuex';


export default {
  name: 'ValveControl',
  computed: mapState('device', ['valves']),
  data() {
    return {
      audioContext: new (window.AudioContext || window.webkitAudioContext)(),
      togglingValves: {},
    };
  },
  methods: {
    ...mapActions('device', ['setPartStateAction']),
    toggleValve(valveIndex) {
      const currentState = this.valves.states[valveIndex];

      if (this.togglingValves[valveIndex]) {
        return; // exit if already toggling
      }
      this.togglingValves = { ...this.togglingValves, [valveIndex]: true };

      const oscillator = this.playValveSound(currentState);

      this.setPartStateAction({
        devicePart: 'valves',
        partIndex: valveIndex,
        newState: currentState === 'open' ? 'closed' : 'open',
      })
        .then(() => {
          oscillator.stop();
          this.togglingValves = { ...this.togglingValves, [valveIndex]: false };
        })
        .catch((error) => {
          console.error(error);
        });
    },
    playValveSound(valveState) {
      const startFrequency = valveState === 'open' ? 500 : 300;
      const endFrequency = valveState === 'open' ? 300 : 500;

      const oscillator = this.audioContext.createOscillator();
      oscillator.type = 'sine';

      const gainNode = this.audioContext.createGain();
      gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      oscillator.frequency.setValueAtTime(startFrequency, this.audioContext.currentTime);
      oscillator.frequency.linearRampToValueAtTime(endFrequency, this.audioContext.currentTime + 0.3);

      oscillator.start();
      oscillator.stop(this.audioContext.currentTime + 0.3); // Stops the oscillator after 0.3 seconds

      return oscillator;
    },

  },
};
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

.btn-danger, .btn-success, .btn-warning{
  font-size: 20px;
  padding: 10px;
  width: 90px;
  text-align: center;
  margin: 10px;
  box-shadow: 0px 5px 10px rgba(0, 0, 0, 0.2);
  /*border: 2px solid red;*/
  color: black;
}

.btn-danger, .active{
  background-color: transparent;
  color: #960000;
}

.btn-success, .active{
  /*background-color: transparent;*/
  color: white;
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
