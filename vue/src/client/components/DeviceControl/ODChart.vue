<template>
  <div className="single-chart-container">
    <Scatter :data="chartData" :options="chartOptions"/>
  </div>
</template>

<script>
import {Scatter} from 'vue-chartjs';
import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip
} from 'chart.js';
import {mapState} from 'vuex';

ChartJS.register(Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement);

function odCalibrationFunction(x, a, b, c, d, g) {
  return d + ((a - d) / Math.pow((1 + Math.pow((x / c), b)), g));
}

export default {
  name: 'LineChart',
  components: {Scatter},
  props: {
    partId: {
      type: Number,
      required: true,
    },
  },

  computed: {
    ...mapState('device', ['ods', 'calibrationModeEnabled']),

        calibrationData() {
      return this.ods?.calibration[this.partId];
    },
    calibrationCoefs() {
      return this.ods?.calibration_coefs[this.partId];
    },
    currentOD() {
      return {od:this.ods?.states[this.partId], signal:this.ods?.odsignals[this.partId]};
    },
    chartData() {
      if (this.calibrationData && typeof this.calibrationData === 'object' && this.calibrationCoefs) {
        const dataPoints = Object.entries(this.calibrationData).map(([key, value]) => ({x: Number(value), y: Number(key)})).sort((a, b) => a.x - b.x);

        const min_x = Math.min(...dataPoints.map(point => point.x));
        const max_x = Math.max(...dataPoints.map(point => point.x));

        const calibrationDataPoints = [];
        for(let x = min_x; x <= max_x; x += 0.1) {
          const y = odCalibrationFunction(x, ...this.calibrationCoefs);
          calibrationDataPoints.push({x, y});
        }

        return {
          datasets: [
            {
              label: `Vial ${this.partId} Calibration OD`,
              data: dataPoints,
              borderColor: '#607ecb',
              backgroundColor: 'rgba(83,158,255,0.64)',
            },
            {
              label: `Vial ${this.partId} Current OD`,
              data: [{x: this.currentOD.signal, y: this.currentOD.od}],
              pointRadius: 5,
              backgroundColor: 'rgba(255,1,60,0.64)',
            },
            {
              label: `Vial ${this.partId} Fit`,
              data: calibrationDataPoints,
              pointRadius: 0,
              borderColor: 'rgba(0,70,220,0.38)',
              //line width
              borderWidth: 2,
              showLine: true,
              fill: false,
              borderDash: [2, 2]
            },
          ],
        };
      }
      return {};
    },

    chartOptions() {
      return {
        devicePixelRatio: 4,
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: true,
            text: `Vial ${this.partId}`,
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Signal (mV)',
            },
            // suggestedMax: 50,
            suggestedMin: 0,
          },
          y: {
            title: {
              display: true,
              text: 'OD',
            },
            suggestedMax: 1.5,
            suggestedMin: 0,
          },
        },
      };
    },
  },
};
</script>
