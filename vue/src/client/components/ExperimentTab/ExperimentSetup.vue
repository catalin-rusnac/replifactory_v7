<template>
  <CToast v-if="errorMessage" :autohide="true" :fade="true" @hidden="clearErrorMessage">
    <CToastHeader closeButton>
      Error
    </CToastHeader>
    <CToastBody>
      {{ errorMessage }}
    </CToastBody>
  </CToast>

  <div class="experiment-setup">
    <div class="d-flex">
      <CFormFloating class="flex-grow-1 mt-3">
        <CFormSelect
          v-model="currentExperimentId"
          id="floatingSelect"
          floatingLabel="Select Experiment"
          aria-label="Floating label select example"
          @change="handleExperimentSelected"
        >
          <option v-for="experiment in reversedExperiments" :key="experiment.id" :value="experiment.id">
            {{ experiment.name }}
          </option>
        </CFormSelect>
      </CFormFloating>
      <CButton color="primary" @click="handleNewExperimentButton" class="mt-3 ml-3">+</CButton>

      <div class="button-container">
        <CButton class="start-button"
          :class="{ 'active': currentExperiment.status === 'running' }"
          :style="{ 'background-color': currentExperiment.status === 'running' ? '#28a745' : 'transparent' }"
          @click="startExperiment()"
          color="success"
          title="Start the experiment loop - measure OD every minute and dilute the cultures as necessary, according to the parameters."
        >
          Start
        </CButton>
        <CButton class="start-button"
          :class="{ 'active': currentExperiment.status === 'paused' }"
          :style="{ 'background-color': currentExperiment.status === 'paused' ? '#ffc107' : 'transparent' }"
          @click="pauseExperiment()"
          title="Pause the dilutions, but keep measuring the OD every minute."
          color="warning"
        >
          Pause
        </CButton>
        <CButton class="start-button"
          :class="{ 'active': currentExperiment.status === 'stopped' }"
          :style="{ 'background-color': currentExperiment.status === 'stopped' ? '#dc3545' : 'transparent' }"
          @click="stopExperiment()"
          @dblclick="forceStopExperiment()"
          color="danger"
          title="Stop gracefully - wait for the current dilution to finish."
        >
          Stop
        </CButton>
      </div>
    </div>

    <div v-if="showCreate" class="d-flex">
      <CFormFloating class="new-experiment" v-if="showCreate">
        <CFormInput
          :model-value="newExperimentname"
          @update:model-value="v => newExperimentname = v"
          id="floatingInput"
          floatingLabel="New Experiment Name"
        />
      </CFormFloating>

      <CButton color="success" @click="createAndSelectExperiment" class="ml-3 mt-3">Create Experiment</CButton>
    </div>
    <div v-if="currentExperiment">
      <ExperimentParameters />
    </div>
  </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import { CButton, CFormFloating, CFormInput, CFormSelect, CToast, CToastBody, CToastHeader } from "@coreui/vue";
import ExperimentParameters from "./ExperimentParameters.vue";

export default {
  components: {
    ExperimentParameters,
    CButton,
    CFormFloating,
    CFormInput,
    CFormSelect,
    CToast,
    CToastBody,
    CToastHeader,
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
    async handleExperimentSelected(event) {
      if (this.currentExperiment.status === 'running' || this.currentExperiment.status === 'paused') {
        await this.stopExperiment(this.currentExperiment.id);
      }
      const selectedExperimentId = event.target.value;
      if (selectedExperimentId !== this.currentExperimentId) {
        this.currentExperimentId = selectedExperimentId;
        await this.setCurrentExperimentAction(this.currentExperimentId);
      }
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
      await this.handleExperimentSelected({ target: { value: this.currentExperimentId } });
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
  align-items: center;
  width: 100%;
}

.new-experiment {
  flex: 1 1 100%;
}

.button-container {
  display: flex;
  justify-content: center;
  align-items: stretch;
  flex-grow: 1;
  margin-left: 1rem;
}
.start-button {
  margin-top: 1rem;
  margin-left: 1rem;
  flex-grow: 1;
  display: flex;
  align-items: center;
}

@media (max-width: 768px) {
  .stock-parameters {
    flex-wrap: wrap;
  }
  .stock-parameter-field {
    flex: 1 1 100%;
  }
}
</style>
