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
          :disabled="currentExperiment.status === 'running' || currentExperiment.status === 'stopping' || isLoadingExperiments"
          :loading="isLoadingExperiments"
        ></v-select>
        <v-btn
          color="primary"
          @click="handleNewExperimentButton"
          class="mt-3"
          :style="{ height: '60px' }"
          title="New Experiment"
          :disabled="currentExperiment.status === 'running' || currentExperiment.status === 'stopping' || isLoadingExperiments"
          :loading="isLoadingExperiments"
        >+</v-btn>
      </div>

      <!-- Second Line: Start, Pause, Stop Buttons -->
      <div class="d-flex line-container">
        <v-btn
          class="start-button"
          :class="{ 'active': currentExperiment.status === 'running' }"
          :style="{
            'background-color': currentExperiment.status === 'running' ? '#28a745' : 'transparent',
            'opacity': currentExperiment.status === 'running' ? 0.5 : 1
          }"
          @click="startExperiment"
          color="success"
          title="Start the experiment loop - measure OD every minute and dilute the cultures as necessary, according to the parameters."
          :disabled="currentExperiment.status === 'running' || currentExperiment.status === 'stopping' || isLoadingExperiments"
          :loading="isLoadingExperiments"
        >
          Start
        </v-btn>
        <v-btn
          class="start-button"
          :class="{ 'active': currentExperiment.status === 'stopped' }"
          :style="{
            'background-color': currentExperiment.status === 'stopped' ? '#dc3545' : 'transparent',
            'opacity': currentExperiment.status === 'stopped' ? 0.5 : 1
          }"
          @click="stopExperiment"
          color="error"
          title="Stop gracefully - wait for the current dilution to finish."
          :disabled="currentExperiment.status === 'stopped' || currentExperiment.status === 'stopping' || isStoppingExperiment || isLoadingExperiments"
          :loading="isStoppingExperiment"
        >
          Stop
        </v-btn>
      </div>

      <!-- Create New Experiment - Moved to appear before experiment checks -->
      <div v-if="showCreate" class="new-experiment-form">
        <div class="form-header">
          <div class="form-note">
            New experiment will copy parameters from <strong>{{ getExperimentDisplayName() }}</strong>
          </div>
          <v-btn
            icon
            size="small"
            @click="showCreate = false"
            class="close-btn"
            title="Close"
          >
            <v-icon size="18">mdi-close</v-icon>
          </v-btn>
        </div>
        <div class="form-content">
          <div class="form-input-row">
            <v-text-field
              v-model="newExperimentname"
              label="New Experiment Name"
              outlined
              dense
              class="flex-grow-1"
              @keyup.enter="createAndSelectExperiment"
            ></v-text-field>
            <v-btn color="primary" @click="createAndSelectExperiment" class="ml-3 create-btn">Create Experiment</v-btn>
          </div>
        </div>
      </div>

      <!-- Experiment Checks - Hide when experiment is running -->
      <ExperimentChecks 
        v-if="currentExperiment && currentExperiment.status !== 'running'" 
        ref="experimentChecks" 
      />

      <!-- Experiment Parameters -->
      <div v-if="currentExperiment">
        <BottleDisplay />
        <!-- <ExperimentParameters /> -->
      </div>
    </div>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useExperimentStore } from '@/client/stores/experiment';
// import ExperimentParameters from './ExperimentParameters.vue';
import BottleDisplay from './BottleDisplay.vue';
import ExperimentChecks from './ExperimentChecks.vue';
import { toast } from 'vue3-toastify';
import 'vue3-toastify/dist/index.css';
import { useDialog } from '@/client/composables/useDialog';

const experimentStore = useExperimentStore();
const { openDialog } = useDialog();
const newExperimentname = ref('');
const showCreate = ref(false);
const currentExperimentId = ref(null);
const experimentChecks = ref(null);
const isStoppingExperiment = ref(false);
const isLoadingExperiments = ref(true);

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
  // Validate that name is not empty
  if (!newExperimentname.value || newExperimentname.value.trim() === '') {
    toast('Experiment name cannot be empty', { type: 'error' });
    return;
  }
  
  const trimmedName = newExperimentname.value.trim();
  
  // Check for invalid characters that could cause filesystem problems
  const invalidChars = /[<>:"/\\|?*\x00-\x1f]/;
  if (invalidChars.test(trimmedName)) {
    toast('Experiment name contains invalid characters. Avoid: < > : " / \\ | ? *', { type: 'error' });
    return;
  }
  
  // Check for reserved names (Windows)
  const reservedNames = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i;
  if (reservedNames.test(trimmedName)) {
    toast('Experiment name cannot be a reserved system name', { type: 'error' });
    return;
  }
  
  // Check if name starts or ends with dots or spaces (problematic on many systems)
  if (trimmedName.startsWith('.') || trimmedName.endsWith('.') || trimmedName.endsWith(' ')) {
    toast('Experiment name cannot start or end with dots or spaces', { type: 'error' });
    return;
  }
  
  // Check length (most filesystems have limits)
  if (trimmedName.length > 255) {
    toast('Experiment name is too long (maximum 255 characters)', { type: 'error' });
    return;
  }
  
  try {
    currentExperimentId.value = await experimentStore.createExperiment({ name: trimmedName });
    await experimentStore.selectExperiment(currentExperimentId.value);
    showCreate.value = false;
    newExperimentname.value = currentExperiment.value.name;
    toast(`New experiment "${trimmedName}" created`, { type: 'success' });
  } catch (error) {
    toast(error.message || 'Failed to create experiment', { type: 'error' });
  }
}

function getExperimentDisplayName() {
  if (!currentExperiment.value) {
    return 'Default Template';
  }
  if (currentExperiment.value.id === 0) {
    return 'Default Template';
  }
  return currentExperiment.value.name || 'Default Template';
}

async function startExperiment() {
  // Check if all pre-experiment checks have passed
  if (experimentChecks.value) {
    const checks = experimentChecks.value.checks;
    const failedChecks = checks.filter(check => check.status === 'failed');
    const pendingChecks = checks.filter(check => check.status === 'pending');
    
    if (failedChecks.length > 0 || pendingChecks.length > 0) {
      const failedNames = failedChecks.map(c => c.name);
      const pendingNames = pendingChecks.map(c => c.name);
      
      let message = '';
      if (failedChecks.length > 0 && pendingChecks.length > 0) {
        message = 'Some checks failed and some are pending.';
      } else if (failedChecks.length > 0) {
        message = 'Some checks failed.';
      } else {
        message = 'Some checks are pending.';
      }
      message += '\n\nStart experiment anyway?';
      
      const confirmed = await openDialog({
        title: 'Pre-experiment Checks Warning',
        message: message
      });
      if (!confirmed) {
        return; // Don't start experiment
      }
    }
  }
  
  try {
    await experimentStore.startExperiment();
    await experimentStore.fetchCurrentExperiment();
    toast('Experiment started!', { type: 'success' });
  } catch (error) {
    toast(error.message, { type: 'error' });
  }
}

async function stopExperiment() {
  console.log('Stop experiment clicked, setting loading to true');
  isStoppingExperiment.value = true;
  try {
    console.log('Calling experimentStore.stopExperiment()');
    await experimentStore.stopExperiment();
    console.log('Stop experiment request sent, polling for actual status change');
    
    // Poll until experiment is actually stopped
    let attempts = 0;
    const maxAttempts = 30; // Max 30 seconds of polling
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
      await experimentStore.fetchCurrentExperiment();
      
      const status = experimentStore.currentExperiment?.status;
      console.log(`Polling attempt ${attempts + 1}: status = ${status}`);
      
      if (status === 'stopped' || status === 'inactive' || !status) {
        console.log('Experiment confirmed stopped');
        toast('Experiment stopped!', { type: 'success' });
        return; // Exit successfully
      }
      
      // Continue polling if still stopping
      if (status === 'stopping') {
        console.log('Experiment still stopping, continuing to poll...');
        // Continue the loop
      }
      
      attempts++;
    }
    
    // If we reach here, polling timed out
    console.warn('Stop polling timed out, but experiment may have stopped');
    toast('Stop command sent, but status confirmation timed out', { type: 'warning' });
    
  } catch (error) {
    console.error('Error stopping experiment:', error);
    toast(error.message || 'Failed to stop experiment', { type: 'error' });
  } finally {
    console.log('Setting loading to false');
    isStoppingExperiment.value = false;
  }
}

onMounted(async () => {
  try {
    await experimentStore.fetchExperiments();
    await experimentStore.fetchCurrentExperiment();
    if (experimentStore.currentExperiment) {
      currentExperimentId.value = experimentStore.currentExperiment.id;
    }
  } finally {
    isLoadingExperiments.value = false;
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
}

.new-experiment-form {
  margin: 20px 0;
  background-color: rgba(33, 150, 243, 0.05);
  border: 2px solid rgba(33, 150, 243, 0.3);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 20px 0 20px;
}

.form-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 20px 20px 20px;
}

.close-btn {
  opacity: 0.7;
  transition: opacity 0.2s;
}

.close-btn:hover {
  opacity: 1;
}

.form-note {
  color: #666;
  font-size: 0.9em;
  font-style: italic;
}

.form-input-row {
  display: flex;
  align-items: center;
}

.create-btn {
  height: 40px !important;
  min-height: 40px !important;
}

@media (max-width: 768px) {
  .line-container {
    flex-direction: column; /* Stack items vertically on smaller screens */
  }
}

.loading-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  width: 100%;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.loading-text {
  color: #fff;
  font-size: 1.1em;
}
</style>
