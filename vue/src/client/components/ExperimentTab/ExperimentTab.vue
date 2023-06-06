<template>
  <div>
    <ExperimentSetup/>
    <ExperimentChart v-if="Object.keys(currentExperiment?.parameters?.cultures || {}).length > 0"/>
  </div>
</template>

<script>
import {mapState} from "vuex";
import ExperimentSetup from './ExperimentSetup.vue';
import ExperimentChart from './ExperimentChart.vue';
export default {
  components: {
    ExperimentSetup,
    ExperimentChart,
  },
  computed: {
    ...mapState('experiment', ['experiments', 'currentExperiment', 'errorMessage']),
  },
};
</script>
