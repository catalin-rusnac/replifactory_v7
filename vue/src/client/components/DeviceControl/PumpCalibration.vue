<template>
  <div class="pump-data">
    <table>
      <tr>
        <th>Rots</th>
        <th>Reps</th>
        <th></th>
        <th>Total mLs</th>
        <th>mL per Rot</th>
      </tr>
      <tr v-for="(row, index) in rows" :key="index">
        <td>{{ row.rotations }}</td>
        <td>{{ row.iterations }}</td>
        <td>
          <button @click="toggleButtonState(index)" :class="{ 'stop-button': isStopButton[index] }">
            <span v-if="!isStopButton[index]">Pump</span>
            <span v-else>Stop</span>
          </button>
        </td>
        <td><input v-model="row.total_ml" @change="onTotalMlInput(row)" type="number" /></td>
        <td>{{pumps.calibration[pumpId][row.rotations].toFixed(3)}}</td>
      </tr>
    </table>

    <div class="chart-container">
          <Bar
            id="my-chart-id"
            :options="chartOptions"
            class="pump-calibration-chart"
            v-if="chartData && chartData.labels && chartData.labels.length"
            :data="chartData"

          />
        </div>

  </div>
</template>
<script>
import { mapActions, mapState } from "vuex";
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip,  BarElement, CategoryScale, LinearScale } from 'chart.js'

ChartJS.register(Title, Tooltip, BarElement, CategoryScale, LinearScale)

export default {
  components: { Bar },
  data() {
    return {
      chartData: {
        labels: [],
        datasets: [{ data: [] }]
      },
      chartOptions: {
        responsive: true,
        scales: {
          x: {
            title: {
              display: true,
              text: 'Rotations',
            },
          },
          y: {
            title: {
              display: true,
              text: 'mL/Rotation',
            },
          },
        },
      },
      isStopButton: {},
      rows: [
        { rotations: 1, iterations: 50, total_ml: NaN },
        { rotations: 5, iterations: 10, total_ml: NaN },
        { rotations: 10, iterations: 5, total_ml: NaN },
        { rotations: 50, iterations: 1, total_ml: NaN },
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
    isValveOpen() {
      return Object.values(this.valves?.states).some(valve => valve === 'open');
    }
  },
  methods: {
    ...mapActions('device', ['setPartCalibrationAction', 'startPumpCalibrationSequence', 'setPartStateAction']),

    createChartData() {
      return {
        labels: Object.keys(this.pumpIdCalibrationData),
        datasets: [{
          label: 'Calibration Data',
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
      this.$set(this.isStopButton, index, !this.isStopButton[index]);
      if (this.isStopButton[index]) {
        this.promptForMl(this.rows[index]);
      } else {
        this.setPartStateAction({devicePart: 'pumps', partIndex: this.pumpId, newState: 'stopped'});
      }
    },
    resetButton(row) {
      this.$set(this.isStopButton, row, false);
    },
    onTotalMlInput(row) {
      if (row.total_ml) {
        this.pumps.calibration[this.pumpId][row.rotations] = row.total_ml / row.rotations / row.iterations;
        this.setPartCalibrationAction({
          devicePart: 'pumps',
          partIndex: this.pumpId,
          newCalibration: this.pumps.calibration[this.pumpId]
        });
      }
    },
    promptForMl(row) {
      console.log("starting pump calibration sequence for pumpId: " + this.pumpId);
      // alert("Starting pump calibration sequence for pumpId: " + this.pumpId + ". Blank the scale and make sure ~10mL are available."); // Add alert here
      alert("Pumping " + row.rotations + " rotations " + row.iterations + " times. Please blank the scale"); // Add alert here
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
  align-items: center;
  margin-top: 20px;
  width: 250px; /* setting the width of the container to 250px */
}

table {
  border-collapse: collapse;
  width: 100%; /* setting the width of the table to 100% so it fills the container */
}

th, td {
  border: 1px solid #ddd;
  padding: 4px; /* reduced padding to save space */
  text-align: center;
  font-size: 0.8rem; /* reduced font size to save space */
}

th {
  background-color: #f2f2f2;
}

button {
  padding: 3px 5px; /* reduced padding to save space */
  background-color: #008CBA; /* Blue background */
  color: white; /* White text */
  border: none; /* Remove borders */
  cursor: pointer; /* Mouse pointer on hover */
  border-radius: 8px;
  font-size: 0.7rem; /* reduced font size to save space */
}
button stop-button {
  background-color: #f44336;
}

button:hover {
  background-color: #007B9A;
}
td:nth-child(1), td:nth-child(2){
  width: 40px; /* set the width of the first 3 columns */
}

td:nth-child(4) {
  width: 60px; /* set the width of the 4th column */
}

input[type="number"] {
  width: 100%; /* make the input fields take up the full width of the cell */
}
.pump-calibration-chart {
  width: 250px;
  height: 350px;
}

</style>
