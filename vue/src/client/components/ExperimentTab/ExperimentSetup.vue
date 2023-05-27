<template>
  <div class="experiment-setup">
    <div class="d-flex">
      <CFormFloating class="flex-grow-1">
        <CFormSelect
          v-model="selectedExperimentId"
          id="floatingSelect"
          floatingLabel="Select Experiment"
          aria-label="Floating label select example"
          @change="handleExperimentSelected"
        >
          <option v-for="experiment in experiments.reverse()" :key="experiment.id" :value="experiment.id">
            {{ experiment.name }}
          </option>
        </CFormSelect>
      </CFormFloating>
      <CButton color="primary" @click="showCreate = !showCreate" class="ml-3">+</CButton>
    </div>

    <div v-if="showCreate" class="d-flex">
      <CFormFloating class="flex-grow-1">
        <CFormInput
          :model-value="newExperiment.name"
          @update:model-value="v => newExperiment.name = v"
          id="floatingInput"
          floatingLabel="New Experiment Name"
          placeholder="Enter Experiment Name"
        />
      </CFormFloating>
      <CButton color="success" @click="createAndSelectExperiment" class="ml-3">Create Experiment</CButton>
    </div>

    <div v-if=currentExperiment>
               <h3>Selected Experiment:</h3>
      <p>{{ currentExperiment.name }}</p>

      <h3>Experiment Parameters:</h3>
      <pre>{{ currentExperiment.parameters }}</pre>

      <CButtonGroup>
        <CButton color="success" @click="startExperiment">Start Experiment</CButton>
        <CButton color="danger" @click="stopExperiment">Stop Experiment</CButton>
      </CButtonGroup>
    </div>

  </div>
</template>

<script>
import {mapActions, mapState} from "vuex";
import {CButton, CFormFloating, CFormInput, CFormSelect} from '@coreui/vue';

export default {
  components: {
    CButton,
    CFormFloating,
    CFormInput,
    CFormSelect
  },
  data() {
    return {
      newExperiment: {
        name: "",
      },
      showCreate: false,
      selectedExperimentId: null,
    };
  },

  computed: {
    ...mapState('experiment', ['experiments', 'currentExperiment']),
  },
  methods: {
    ...mapActions('experiment', ['setCurrentExperimentAction', 'createExperiment', "fetchExperiments"]),
    async handleExperimentSelected(event) {
      this.selectedExperimentId = event.target.value;
      await this.setCurrentExperimentAction(this.selectedExperimentId);
      console.log(`Selected experiment ${this.selectedExperimentId}`, this.currentExperiment);

    },
    handleCreateExperimentClicked() {
      this.createExperiment({ name: 'New Experiment'});
    },
    async createAndSelectExperiment() {
      this.selectedExperimentId = await this.createExperiment({name: this.newExperiment.name});
      await this.handleExperimentSelected({target: {value: this.selectedExperimentId}});
      this.showCreate = false;
      this.newExperiment.name = '';
    },
  },
  created() {
    this.fetchExperiments();
  },
};
</script>

<style scoped>
.experiment-setup {
  /* Add any necessary styles for the experiment setup component */
}
</style>
