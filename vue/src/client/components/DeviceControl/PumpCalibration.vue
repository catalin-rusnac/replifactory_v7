<template>
  <div class="pump-data">
    <table>
      <thead>
        <tr>
          <th>Calibration Sequence</th>
          <th></th>
          <th>Volume (mL)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="index">
          <td>
            <div class="iteration-rotation-wrapper">
              <div class="iteration">{{ row.iterations }}</div>
              <div class="multiplier">x</div>
              <div class="rotation">{{ row.rotations }} rots</div>
            </div>
          </td>
          <td>
            <button @click="toggleButtonState(index)" :class="{ 'stop-button': isStopButton[index] }">
              <span v-if="!isStopButton[index]">Start</span>
              <span v-else>Stop</span>
            </button>
          </td>
          <td>
            <input v-model="row.total_ml" @change="onTotalMlInput(row)" type="float" />
          </td>
        </tr>
      </tbody>
    </table>

    <div class="chart-container">
      <Bar
        id="pump-calibration-chart"
        :options="chartOptions"
        class="pump-calibration-chart"
        v-if="chartData.datasets[0].data.length > 0"
        :data="chartData"
      />
    </div>
  </div>
</template>
<script>
import { mapActions, mapState } from "vuex";
import { Bar } from 'vue-chartjs';
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, Title, Tooltip, Legend } from 'chart.js';
ChartJS.register(BarElement, CategoryScale, LinearScale, Title, Tooltip, Legend);

export default {
  components: {Bar},
  data() {
    return {
      chartData: {
        datasets: [{data: []}]
      },
      chartOptions: {
        responsive: true,
        devicePixelRatio: 4,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        backgroundColor: 'rgba(0, 140, 186, 0.3)',
        layout: {
          padding: {
            top: 20
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'rotations',
            },
          },
          y: {
            title: {
              display: true,
              text: 'mL / rotation',
            },
            beginAtZero: false,
            suggestedMin: 0.1,
            suggestedMax: 0.22,
          },
        },
      },
      isStopButton: {},
      rows: [
        {rotations: 1, iterations: 50, total_ml: NaN},
        {rotations: 5, iterations: 10, total_ml: NaN},
        {rotations: 10, iterations: 5, total_ml: NaN},
        {rotations: 50, iterations: 1, total_ml: NaN},
      ]
    };
  },
  props: {
    pumpId: {
      type: Number,
      required: true
    }
  },
  computed: {
    ...mapState('device', ['calibrationModeEnabled', 'pumps', 'valves']),
    pumpIdCalibrationData() {
      return this.pumps?.calibration[this.pumpId];
    },
  },
  methods: {
    ...mapActions('device', ['setPartCalibrationAction', 'startPumpCalibrationSequence', 'setPartStateAction']),

    createChartData() {
      return {
        labels: Object.keys(this.pumpIdCalibrationData),
        datasets: [{
          label: null,
          data: Object.values(this.pumpIdCalibrationData),
          fill: false,
          borderColor: 'rgb(75, 192, 192)',
          tension: 0.1,
        }]
      };
    },
    updateChartData() {
      this.chartData = this.createChartData();
    },
    toggleButtonState(index) {
      const isValveOpen = Object.values(this.valves.states).some((valve) => valve === 'open');

      if (!isValveOpen) {
        alert('At least one valve must be open to start the pump');
        return;
      }
      this.isStopButton[index] = !this.isStopButton[index];
      if (this.isStopButton[index]) {
        this.promptForMl(this.rows[index]);
      } else {
        this.setPartStateAction({devicePart: 'pumps', partIndex: this.pumpId, newState: 'stopped'});
      }
    },
    resetButton(row) {
      this.isStopButton[row] = false;
    },
    onTotalMlInput(row) {
      if (row.total_ml) {
        this.pumps.calibration[this.pumpId][row.rotations] = row.total_ml / row.rotations / row.iterations;
        this.setPartCalibrationAction({
          devicePart: 'pumps',
          partIndex: this.pumpId,
          newCalibration: this.pumps.calibration[this.pumpId]
        });
        this.isStopButton[row] = false;
      }
    },
    promptForMl(row) {
      console.log("starting pump calibration sequence for pumpId: " + this.pumpId);
      alert("Pumping " + row.rotations + " rotations " + row.iterations + " times. Please blank the scale");
      this.startPumpCalibrationSequence({
        pumpId: this.pumpId,
        rotations: row.rotations,
        iterations: row.iterations
      }).then(() => {
        console.log("pump calibration sequence finished");
        this.resetButton(row);
        const total_ml = parseFloat(prompt('Enter total mL pumped'));
        if (!isNaN(total_ml)) {
          row.total_ml = total_ml;
          this.onTotalMlInput(row);
        }
      });
    },
  },
  mounted() {
    if (this.pumpIdCalibrationData) {
      this.updateChartData();
    }
    this.rows.forEach((row) => {
      row.total_ml = this.pumps.calibration[this.pumpId][row.rotations] * row.rotations * row.iterations;
      row.total_ml = row.total_ml.toFixed(2);
    });
  },
  watch: {
    pumpIdCalibrationData: {
      deep: true,
      handler() {
        this.updateChartData();
      },
    },
  },
};
</script>

<style scoped>
.pump-data {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-top: 10px;
  width: 200px;
  border: 1px solid #e3e3e3;
  border-radius: 5px;
  justify-content: center;
  padding-left: 5px;
  padding-right: 5px;
}

table {
  border-collapse: collapse;
  width: 100%;
}

th, td {
  border: none;
  padding: 4px;
  text-align: center;
  font-size: 0.8rem;
}

button {
  padding: 3px 5px;
  background-color: #008CBA;
  color: white;
  border: none;
  cursor: pointer;
  border-radius: 8px;
  font-size: 0.7rem;
}

button stop-button {
  background-color: #f44336;
}

button:hover {
  background-color: #007B9A;
}

td:nth-child(1), td:nth-child(2) {
  width: 40px;
}

td:nth-child(4) {
  width: 60px;
}

input[type="float"] {
  width: 100%;
  font-size: 12px;
}

.pump-calibration-chart {
  margin-top: 0px;
  width: 190px;
  height: 130px;
}

.iteration-rotation-wrapper {
  width: 75px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.iteration {
  width: 15px;
  text-align: right;
}

.multiplier {
  width: 10px;
  text-align: center;
}

.rotation {
  width: 40px;
  text-align: left;
}
</style>
