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
      <CFormFloating class="flex-grow-1">
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
      <CButton color="primary" @click="handleNewExperimentButton" class="ml-3">+</CButton>
    </div>

    <div v-if="showCreate" class="d-flex">
      <CFormFloating class="flex-grow-1" v-if="showCreate" >
        <CFormInput
            :model-value="newExperimentname"
          @update:model-value="v => newExperimentname = v"
          id="floatingInput"
          floatingLabel="New Experiment Name"
        />
      </CFormFloating>

      <CButton color="success" @click="createAndSelectExperiment" class="ml-3">Create Experiment</CButton>
    </div>

    <div v-if="currentExperiment">
<!--      <h3>Current Experiment:</h3>-->
<!--      <p>{{ currentExperiment.name ?? "No Experiment Selected" }}</p>-->
      <div class="button-container">
        <CButton
          :class="{ 'active': currentExperiment.status === 'running' }"
          :style="{ 'background-color': currentExperiment.status === 'running' ? '#28a745' : 'transparent' }"
          @click="startExperiment(currentExperiment.id)"
          color="success"
        >
          Start
        </CButton>
        <CButton
          :class="{ 'active': currentExperiment.status === 'paused' }"
          :style="{ 'background-color': currentExperiment.status === 'paused' ? '#ffc107' : 'transparent' }"
          @click="pauseExperiment(currentExperiment.id)"
          color="warning"
        >
          Pause
        </CButton>
        <CButton
          :class="{ 'active': currentExperiment.status === 'stopped' }"
          :style="{ 'background-color': currentExperiment.status === 'stopped' ? '#dc3545' : 'transparent' }"
          @click="stopExperiment(currentExperiment.id)"
          color="danger"
        >
          Stop
        </CButton>
      </div>



      <div class="experiment-parameters" style="align-items: center; display: flex; flex-direction: column; margin-top: 20px;">
      <template v-for="(value, key) in currentExperiment.parameters" :key="key">
        <CFormFloating class="flex-grow-1" v-if="key !== 'cultures'">
          <CFormInput
            :model-value="value"
            @update:model-value="v => currentExperiment.parameters[key] = v"
            :id="`floatingInput_${key}`"
            :floating-label="`${key}`"
            :placeholder="`Enter ${key}`"
          />
        </CFormFloating>
      </template>

      <div class = "experiment-cultures" v-if="Object.keys(currentExperiment?.parameters?.cultures || {}).length > 0">
          <CRow class="culture-row">
            <CCol
              v-for="(culture, index) in currentExperiment.parameters.cultures"
              :key="index"
              class="culture-column"
            >
              <CultureConfig :experiment="currentExperiment" :vial="index" />
            </CCol>
          </CRow>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import { CButton, CFormFloating, CFormInput, CFormSelect, CRow, CCol, CToast, CToastBody, CToastHeader } from '@coreui/vue';
import CultureConfig from './CultureConfig.vue';

export default {
  components: {
    CultureConfig,
    CButton,
    CFormFloating,
    CFormInput,
    CFormSelect,
    CRow,
    CCol,
    CToast,
    CToastBody,
    CToastHeader
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
    return [...this.experiments].reverse(); // Reverse a copy of the original array
  },
  },
  methods: {
    ...mapActions('experiment', ['setCurrentExperimentAction', 'createExperiment', 'fetchExperiments', "fetchCurrentExperiment", "startExperiment", "pauseExperiment", "stopExperiment"]),

    async handleNewExperimentButton() {
      this.showCreate = !this.showCreate;
      if (this.currentExperiment.status === 'running' || this.currentExperiment.status === 'paused') {
        await this.stopExperiment(this.currentExperiment.id);
      }
    },

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
    async createAndSelectExperiment() {
      //if current experiment exists, copy parameters
      if (this.currentExperiment) {
        this.currentExperimentId = await this.createExperiment({name: this.newExperimentname, parameters: this.currentExperiment.parameters});
        console.log("created new experiment with same parameters as current experiment")
      }
      else {
        console.log("created new experiment with default parameters")
        this.currentExperimentId = await this.createExperiment({name: this.newExperimentname});
      }
      console.log(this.currentExperimentId)
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

.experiment-cultures {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  width: 1250px;
  margin: 0 auto;
}

</style>