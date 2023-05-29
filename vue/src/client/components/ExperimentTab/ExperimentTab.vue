<template>
  <div>
    <ExperimentSetup/>
    <ExperimentChart/>
  </div>
</template>

<script>
import ExperimentSetup from './ExperimentSetup.vue';
import ExperimentChart from './ExperimentChart.vue';

export default {
  components: {
    ExperimentSetup,
    ExperimentChart,
  },
};
</script>
