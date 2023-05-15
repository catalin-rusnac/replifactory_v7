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
        <td><button @click="promptForMl(row)">Pump</button></td>
        <td><input v-model="row.total_ml" @input="onTotalMlInput(row)" type="number" /></td>
        <td>{{pumps.calibration[pumpId][row.rotations].toFixed(3)}}</td>
      </tr>
    </table>
  </div>
</template>

<script>
import {mapActions, mapState} from "vuex";

export default {
  data() {
    return {
      rows: [
        { rotations: 1, iterations: 50, total_ml: NaN},
        { rotations: 5, iterations: 10, total_ml: NaN},
        { rotations: 10, iterations: 5, total_ml: NaN},
        { rotations: 50, iterations: 1, total_ml: NaN},
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
    ...mapState('device', ['calibrationModeEnabled', 'pumps']),
  },
  methods: {
    ...mapActions('device', ['setPartCalibrationAction']),

    onTotalMlInput(row) {
      if (row.total_ml) {
        this.pumps.calibration[this.pumpId][row.rotations] = row.total_ml / row.rotations / row.iterations;
        this.setPartCalibrationAction({devicePart: 'pumps', partIndex: this.pumpId, newCalibration: this.pumps.calibration[this.pumpId]});
      }
    },
    promptForMl(row) {
      const total_ml = parseFloat(prompt('Enter total mL pumped'));
      if (!isNaN(total_ml)) {
        row.total_ml = total_ml;
        this.onTotalMlInput(row);
      }
    }
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

</style>
