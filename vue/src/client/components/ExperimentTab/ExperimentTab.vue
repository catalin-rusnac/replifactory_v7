<template>
  <div>
    <div class="d-flex align-items-center">
      <CFormFloating class="mb-3 flex-grow-1">
        <CFormSelect
            v-model="selectedExperimentId"
          id="floatingSelect"
          floatingLabel="Select Experiment"
          aria-label="Floating label select example"
            @change="selectedExperimentId = $event.target.value"
        >
          <option v-for="experiment in experiments" :key="experiment.id" :value="experiment.id">
            {{ experiment.name }}
          </option>
        </CFormSelect>
      </CFormFloating>
      <CButton color="primary" @click="showCreate = !showCreate" class="ml-3">+</CButton>
    </div>
<!--    <div>-->
<!--      <CFormSelect-->
<!--        v-model="selectedExperimentId"-->
<!--        id="floatingSelect"-->
<!--        floatingLabel="Select number from 1 to 20"-->
<!--        aria-label="Floating label select example">-->
<!--        <option v-for="i in 20" :key="i" :value="i">-->
<!--          {{ i }}-->
<!--        </option>-->
<!--      </CFormSelect>-->
<!--    </div>-->

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

    <div v-if="selectedExperiment">
      <h3>Selected Experiment:</h3>
      <p>{{ selectedExperiment.name }}</p>

      <h3>Experiment Parameters:</h3>
      <pre>{{ selectedExperimentParameters }}</pre>

      <CButtonGroup>
        <CButton color="success" @click="startExperiment">Start Experiment</CButton>
        <CButton color="danger" @click="stopExperiment">Stop Experiment</CButton>
      </CButtonGroup>
    </div>
  </div>
</template>

<script>
import { mapActions, mapState, mapGetters } from "vuex";
import { CButton, CButtonGroup, CFormFloating, CFormInput, CFormSelect } from '@coreui/vue';

export default {
  components: {
    CButton,
    CButtonGroup,
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
      selectedExperimentId: "",
    };
  },
  computed: {
    ...mapState("experiment", ["experiments"]),
    ...mapGetters("experiment", ["selectedExperimentParameters"]),
    selectedExperiment() {
      return this.experiments.find(
        (experiment) => experiment.id == this.selectedExperimentId
      );
    },
  },
  watch: {
    selectedExperimentId(newValue) {
      console.log('selectedExperimentId changed to', newValue);

      if (newValue) {
        this.setCurrentExperiment(newValue);
      } else {
        this.setCurrentExperiment(null);
      }
    },
  },
  methods: {
    ...mapActions("experiment", [
      "fetchExperiments",
      "createExperiment",
      "setCurrentExperiment",
      "updateExperimentStatus",
      "resetCurrentExperiment"
    ]),
    async createAndSelectExperiment() {
      const id = await this.createExperiment({ name: this.newExperiment.name });
      this.selectedExperimentId = id;
      this.showCreate = false;
      this.newExperiment.name = '';
    },
    startExperiment() {
      this.updateExperimentStatus({
        id: this.selectedExperimentId,
        status: "running",
      });
    },
    stopExperiment() {
      this.updateExperimentStatus({
        id: this.selectedExperimentId,
        status: "stopped",
      });
    },
  },
  created() {
    this.fetchExperiments();
    this.resetCurrentExperiment();
    this.selectedExperimentId= null;
  },
};
</script>