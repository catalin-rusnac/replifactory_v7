<template>
  <div id="CulturePlot">
    <!-- This text will be replaced by the Plotly chart -->
  </div>
</template>

<script>
import Plotly from 'plotly.js';
import { mapActions, mapState } from 'vuex';

export default {
  name: "ExperimentChart",
    computed: {
    ...mapState('experiment', ['plot_data', 'currentExperiment']),
  },
  methods: {
    ...mapActions('experiment', ['fetchCulturePlot']),


    plotData() {
  // Get plot data for each vial
  const vials = Object.keys(this.plot_data);
  const data = vials.flatMap(vial => this.plot_data[vial] || []);


  const layout = {
  title: "Culture ",
  xaxis: {
    title: 'Time',
  },
  yaxis: {
    title: 'Optical Density',
    automargin: true,
    mode: 'lines+markers',
  },
  yaxis2: {
    title: 'Generation',
    overlaying: 'y',
    side: 'right',
    automargin: true,
  },
  yaxis3: {
    title: 'Concentration',
    overlaying: 'y',
    side: 'left',
    position: 0.08,
    automargin: true,
  },
};


  Plotly.react('CulturePlot', data, layout);
},


  },
  watch: {
  plot_data: {
    deep: true,
    handler() {
      this.plotData();
    },
  },
  'currentExperiment': {
    deep: true,
    immediate: true,
    async handler(newVal, oldVal) {
      if(newVal && oldVal && newVal.id !== oldVal.id) {
        await this.fetchCulturePlot(2); // replace 5 with the actual vial id
      } else if(newVal && !oldVal) {
        await this.fetchCulturePlot(2);
      }
    },
  }
},

  mounted() {
    this.plotData();
  },
}
</script>



<style scoped>

</style>
