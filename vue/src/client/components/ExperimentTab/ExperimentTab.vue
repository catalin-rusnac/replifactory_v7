<template>
  <div>
    <ExperimentSetup
      :experiments="experiments"
      :selectedExperimentId="selectedExperimentId"
      @experimentSelected="handleExperimentSelected"
      @createExperimentClicked="handleCreateExperimentClicked"
    />
    <ExperimentChart :experimentId="selectedExperimentId" />
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import ExperimentSetup from './ExperimentSetup.vue';
import ExperimentChart from './ExperimentChart.vue';

export default {
  components: {
    ExperimentSetup,
    ExperimentChart,
  },
  computed: {
    ...mapState('experiment', ['experiments', 'selectedExperimentId']),
  },
  methods: {
    ...mapActions('experiment', ['selectExperiment', 'createExperiment']),
    handleExperimentSelected(experimentId) {
      this.selectExperiment(experimentId);
    },
    handleCreateExperimentClicked() {
      this.createExperiment();
    },
  },
};
</script>
