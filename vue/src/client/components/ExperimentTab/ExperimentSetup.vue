<template>
  <v-container>
    <div class="experiment-setup">
      <!-- First Line: Select Experiment and New Experiment Button -->
      <div class="d-flex line-container">
        <v-select
          v-model="currentExperimentId"
          :items="reversedExperiments"
          item-title="name"
          item-value="id"
          label="Select Experiment"
          dense
          outlined
          class="flex-grow-1 mt-3 experiment-select"
          :style="{ minWidth: '150px' }"
          @update:modelValue="handleExperimentSelected"
          :disabled="currentExperiment.status === 'running'"
        ></v-select>
        <v-btn
          color="primary"
          @click="handleNewExperimentButton"
          class="mt-3"
          :style="{ height: '60px' }"
          title="New Experiment"
          :disabled="currentExperiment.status === 'running'"
        >+</v-btn>
      </div>

      <!-- Second Line: Start, Pause, Stop Buttons -->
      <div class="d-flex line-container">
        <v-btn
          class="start-button"
          :class="{ 'active': currentExperiment.status === 'running' }"
          :style="{ 'background-color': currentExperiment.status === 'running' ? '#28a745' : 'transparent' }"
          @click="startExperiment"
          color="success"
          title="Start the experiment loop - measure OD every minute and dilute the cultures as necessary, according to the parameters."
        >
          Start
        </v-btn>
        <v-btn
          class="start-button"
          :class="{ 'active': currentExperiment.status === 'stopped' }"
          :style="{ 'background-color': currentExperiment.status === 'stopped' ? '#dc3545' : 'transparent' }"
          @click="stopExperiment"
          @dblclick="forceStopExperiment"
          color="error"
          title="Stop gracefully - wait for the current dilution to finish."
        >
          Stop
        </v-btn>
      </div>

      <!-- Create New Experiment -->
      <div v-if="showCreate" class="d-flex">
        <v-text-field
          v-model="newExperimentname"
          label="New Experiment Name"
          outlined
          dense
          class="flex-grow-1 mt-3"
        ></v-text-field>
        <v-btn color="success" @click="createAndSelectExperiment" class="ml-3 mt-3">Create Experiment</v-btn>
      </div>

      <!-- Experiment Parameters -->
      <div v-if="currentExperiment">
        <ExperimentParameters />
      </div>
    </div>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useExperimentStore } from '@/client/stores/experiment';
import ExperimentParameters from './ExperimentParameters.vue';
import { toast } from 'vue3-toastify';
import 'vue3-toastify/dist/index.css';

const experimentStore = useExperimentStore();
const newExperimentname = ref('');
const showCreate = ref(false);
const currentExperimentId = ref(null);

const experiments = computed(() => experimentStore.experiments);
const currentExperiment = computed(() => experimentStore.currentExperiment || {});
const reversedExperiments = computed(() => [...experiments.value].reverse());

async function handleExperimentSelected() { 
  if (currentExperiment.value.status === 'running') {
    await experimentStore.stopExperiment();
  }
  await experimentStore.selectExperiment(currentExperimentId.value);
}

async function handleNewExperimentButton() {
  showCreate.value = !showCreate.value;
  if (currentExperiment.value.status === 'running') {
    await experimentStore.stopExperiment();
  }
}

async function createAndSelectExperiment() {
  if (currentExperiment.value) {
    currentExperimentId.value = await experimentStore.createExperiment({ name: newExperimentname.value, parameters: currentExperiment.value.parameters });
  } else {
    currentExperimentId.value = await experimentStore.createExperiment({ name: newExperimentname.value });
  }
  await handleExperimentSelected();
  showCreate.value = false;
  newExperimentname.value = '';
}

async function startExperiment() {
  await experimentStore.startExperiment();
  toast('Experiment started!', { type: 'success' });
}
async function stopExperiment() {
  await experimentStore.stopExperiment();
}
function forceStopExperiment() {
  // Optionally implement force stop logic
}

onMounted(async () => {
  await experimentStore.fetchExperiments();
  await experimentStore.fetchCurrentExperiment();
  if (experimentStore.currentExperiment) {
    currentExperimentId.value = experimentStore.currentExperiment.id;
  }
});
</script>

<style scoped>
.experiment-setup {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
}

.line-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: center; /* Center items if wrapping */
  gap: 1rem; /* Space between items */
}

.experiment-select {
  min-width: 150px;
}

.button-container {
  display: flex;
  justify-content: center;
  align-items: stretch;
  flex-grow: 1;
  margin-left: 1rem;
}

.start-button {
  margin-top: 10px;
  width: 220px;
  display: flex;
  align-items: center;
}

@media (max-width: 768px) {
  .line-container {
    flex-direction: column; /* Stack items vertically on smaller screens */
  }
}
</style>
