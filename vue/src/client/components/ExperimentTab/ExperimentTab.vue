<template>
  <div className="single-chart-container">
<!--    <Line :data="chartData" :options="chartOptions"/>-->
  </div>
</template>

<!--<script>-->
<!--import {Line} from 'vue-chartjs';-->
<!--import {-->
<!--  Chart as ChartJS,-->
<!--  Title,-->
<!--  Tooltip,-->
<!--  Legend,-->
<!--  LineElement,-->
<!--  CategoryScale,-->
<!--  LinearScale,-->
<!--  PointElement-->
<!--} from 'chart.js';-->
<!--import {mapState} from 'vuex';-->

<!--ChartJS.register(Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement);-->

<!--export default {-->
<!--  name: 'LineChart',-->
<!--  components: {Line},-->
<!--  props: {-->
<!--    partId: {-->
<!--      type: Number,-->
<!--      required: true,-->
<!--    },-->
<!--  },-->
<!--  computed: {-->
<!--    ...mapState('device', ['ods', 'calibrationModeEnabled']),-->
<!--    partData() {-->
<!--      return this.ods?.calibration[this.partId];-->
<!--    },-->
<!--    chartData() {-->
<!--      if (this.partData && typeof this.partData === 'object') {-->
<!--        const labels = Object.values(this.partData).map(Number).sort((a, b) => a - b);-->
<!--        const data = Object.keys(this.partData).reverse();-->
<!--        return {-->
<!--          labels,-->
<!--          datasets: [-->
<!--            {-->
<!--              label: `Vial ${this.partId} OD`,-->
<!--              borderColor: '#f87979',-->
<!--              backgroundColor: 'transparent',-->
<!--              data,-->
<!--            },-->
<!--          ],-->
<!--        };-->
<!--      }-->
<!--      return {};-->
<!--    },-->
<!--    chartOptions() {-->
<!--      return {-->
<!--        devicePixelRatio: 4,-->
<!--        responsive: true,-->
<!--        maintainAspectRatio: false,-->
<!--        plugins: {-->
<!--          legend: {-->
<!--            display: false,-->
<!--          },-->
<!--          title: {-->
<!--            display: true,-->
<!--            text: `Vial ${this.partId}`,-->
<!--          },-->
<!--        },-->
<!--        scales: {-->
<!--          x: {-->
<!--            title: {-->
<!--              display: true,-->
<!--              text: 'Signal',-->
<!--            },-->
<!--            suggestedMax: 120,-->
<!--            suggestedMin: 0,-->
<!--          },-->
<!--          y: {-->
<!--            title: {-->
<!--              display: true,-->
<!--              text: 'OD',-->
<!--            },-->
<!--            suggestedMax: 5,-->
<!--            suggestedMin: 0,-->
<!--          },-->
<!--        },-->
<!--      };-->
<!--    },-->
<!--  },-->
<!--};-->
<!--</script>-->
