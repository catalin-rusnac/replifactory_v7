<template>
  <div :id="`vial-${vial}`" class="graph-container"></div>
</template>

<script>
import Plotly from 'plotly.js';

export default {
  name: "VialPlot",
  props: {
    vial: {
      type: Number,
      required: true,
    },
    data: {
      type: Array,
      default: () => [],
    },
  },
  watch: {
    data: {
      handler: 'plotData',
      deep: true,
    },
  },
  mounted() {
    this.plotData();
  },
  methods: {
    plotData() {
      const data = this.data || [];

      // Find the maximum values for each trace type
      let maxRpm = 0, maxOd = 0, maxGeneration = 0, maxConcentration = 0, maxGrowthRate = 0;
      data.forEach(trace => {
        const traceMax = Math.max(...trace.y);
        switch (trace.yaxis) {
          case 'y5':
            if (traceMax > maxRpm) maxRpm = traceMax;
            break;
          case 'y':
            if (traceMax > maxOd) maxOd = traceMax;
            break;
          case 'y2':
            if (traceMax > maxGeneration) maxGeneration = traceMax;
            break;
          case 'y3':
            if (traceMax > maxConcentration) maxConcentration = traceMax;
            break;
          case 'y4':
            if (traceMax > maxGrowthRate) maxGrowthRate = traceMax;
            break;
        }
      });

      // Determine the y-axis range for each trace type
      const rpmRange = maxRpm <= 4000 ? [0, 4000] : [0, maxRpm * 1.05];
      const odRange = maxOd <= 1 ? [0, 1] : [0, maxOd * 1.05];
      const generationRange = maxGeneration <= 50 ? [0, 50] : [0, maxGeneration * 1.05];
      const concentrationRange = maxConcentration <= 10 ? [0, 10] : [0, maxConcentration * 1.05];
      const growthRateRange = maxGrowthRate <= 1.5 ? [0, 1.5] : [0, maxGrowthRate * 1.05];

      const layout = {
        title: `Culture ${this.vial}`,
        xaxis: {
          title: 'Time',
        },
        yaxis: {
          title: 'Optical Density',
          range: odRange,
          automargin: true,
          mode: 'lines+markers',
        },
        yaxis2: {
          title: 'Generation',
          range: generationRange,
          overlaying: 'y',
          side: 'right',
          automargin: true,
        },
        yaxis3: {
          title: 'Concentration',
          range: concentrationRange,
          overlaying: 'y',
          side: 'right',
          position: 0.92,
          automargin: true,
        },
        yaxis4: {
          title: 'Growth Rate',
          range: growthRateRange,
          overlaying: 'y',
          side: 'left',
          position: 0.08,
          automargin: true,
        },
        yaxis5: {
          title: 'RPM',
          range: rpmRange,
          overlaying: 'y',
          side: 'right',
          position: 0.1,
          automargin: true,
        },
      };

      const graphDiv = document.getElementById(`vial-${this.vial}`);
      if (graphDiv) {
        Plotly.react(graphDiv, data, layout);
      }
    },
  },
};
</script>

<style scoped>
.graph-container {
  width: 90vw;
  height: 80vh;
  display: flex;
  justify-content: center;
  flex-direction: column;
  align-items: center;
  margin-top: 20px;
}
</style>
