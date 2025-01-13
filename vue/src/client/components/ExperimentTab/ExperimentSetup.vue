<template>
  <v-container>
    <v-snackbar v-model="errorMessage" timeout="4000">
      {{ errorMessage }}
    </v-snackbar>

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
        ></v-select>
<!--        make button same height as dropdown-->
        <v-btn color="primary" @click="handleNewExperimentButton" class="mt-3" :style="{ height: '60px' }" title="New Experiment">+</v-btn>
      </div>

      <!-- Second Line: Start, Pause, Stop Buttons -->
      <div class="d-flex line-container">
        <v-btn
          class="start-button"
          :class="{ 'active': currentExperiment.status === 'running' }"
          :style="{ 'background-color': currentExperiment.status === 'running' ? '#28a745' : 'transparent' }"
          @click="startExperiment()"
          color="success"
          title="Start the experiment loop - measure OD every minute and dilute the cultures as necessary, according to the parameters."
        >
          Start
        </v-btn>
        <v-btn
          class="start-button"
          :class="{ 'active': currentExperiment.status === 'paused' }"
          :style="{ 'background-color': currentExperiment.status === 'paused' ? '#ffc107' : 'transparent' }"
          @click="pauseExperiment()"
          title="Pause the dilutions, but keep measuring the OD every minute."
          color="warning"
        >
          Pause
        </v-btn>
        <v-btn
          class="start-button"
          :class="{ 'active': currentExperiment.status === 'stopped' }"
          :style="{ 'background-color': currentExperiment.status === 'stopped' ? '#dc3545' : 'transparent' }"
          @click="stopExperiment()"
          @dblclick="forceStopExperiment()"
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

<script>
import { mapActions, mapState } from "vuex";
import ExperimentParameters from "./ExperimentParameters.vue";

export default {
  components: {
    ExperimentParameters,
  },
  data() {
    return {
      newExperimentname: null,
      showCreate: false,
      currentExperimentId: null,
    };
  },
  computed: {
    ...mapState('experiment', ['experiments', 'currentExperiment', 'errorMessage']),
    reversedExperiments() {
      return [...this.experiments].reverse();
    },
  },
  methods: {
    ...mapActions('experiment', ['setCurrentExperimentAction', 'createExperiment', 'fetchExperiments', 'fetchCurrentExperiment', 'startExperiment', 'pauseExperiment', 'stopExperiment']),
    async handleExperimentSelected() {
      if (this.currentExperiment.status === 'running' || this.currentExperiment.status === 'paused') {
        await this.stopExperiment(this.currentExperiment.id);
      }
      await this.setCurrentExperimentAction(this.currentExperimentId);
    },
    async handleNewExperimentButton() {
      this.showCreate = !this.showCreate;
      if (this.currentExperiment.status === 'running' || this.currentExperiment.status === 'paused') {
        await this.stopExperiment(this.currentExperiment.id);
      }
    },
    async createAndSelectExperiment() {
      if (this.currentExperiment) {
        this.currentExperimentId = await this.createExperiment({ name: this.newExperimentname, parameters: this.currentExperiment.parameters });
      } else {
        this.currentExperimentId = await this.createExperiment({ name: this.newExperimentname });
      }
      await this.handleExperimentSelected(this.currentExperimentId);
      this.showCreate = false;
      this.newExperimentname = '';
    },
  },
  async created() {
    await this.fetchExperiments();
    await this.fetchCurrentExperiment();
    this.currentExperimentId = this.currentExperiment.id;
  },
};
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
