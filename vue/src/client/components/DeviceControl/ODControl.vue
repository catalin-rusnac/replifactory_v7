<template>
    <table>
    </table>
    <table>
      <thead v-if="calibrationModeEnabled">
        <tr>
          <th>OD values</th>
          <th></th>
          <th v-for="vial in vials" :key="vial">{{ 'vial' + vial }}</th>
          <th></th>
        </tr>
      </thead>
      <tbody v-if="calibrationModeEnabled">
        <tr v-for="(odValue, index) in odValues" :key="index">
          <td>
            <input :value="odValue" @input="updateODValue($event, index)" type="number" step="0.1" />
          </td>
          <td>
            <button @click="measure(odValue)">Measure</button>
          </td>
          <td v-for="vial in vials" :key="vial">
            <input class="calibration-signal" v-model="ods.calibration[vial][odValue]" type="number"/>
          </td>
          <td>
            <button class="button button-delete" @click="clearRow(odValue, index)">Delete Row</button>
          </td>
        </tr>
        <tr>
          <td>
            <input v-model="newRowValue" type="number" step="0.1" />
          </td>
          <td>
            <button class="button button-new"
                @click="addNewRow">New Row</button>
          </td>
        </tr>
      </tbody>
      <tbody v-else>
      <tr>
        <td v-for="(od, index) in ods.states" :key="index">
          <button class="od-button" @click="handleOdClick(index)">
            <span>OD {{ index }}</span>
          </button>
        </td>
      </tr>
      <tr>
        <td v-for="(od, index) in ods.states" :key="index">
          <span class="od-output-value">{{ parseFloat(ods.states[index].toFixed(2))}}<br></span>
          <span class="od-output-value">({{ parseFloat(ods.states[index].toFixed(2)) }}mV)</span>
        </td>
      </tr>

<!--          <td>-->
<!--            <input :value="odValue" @input="updateODValue($event, index)" type="number" step="0.1" />-->
<!--          </td>-->
<!--          <td>-->
<!--            <button @click="measure(odValue)">Measure</button>-->
<!--          </td>-->
<!--          <td v-for="vial in vials" :key="vial">-->
<!--            <input v-model="ods.calibration[vial][odValue]" type="number" readonly />-->
<!--          </td>-->



      </tbody>
    </table>
</template>

<script>
import {mapState, mapActions, mapMutations} from 'vuex';


export default {
  data() {
    return {
      odValues: [0.00788, 0.0158, 0.0315, 0.0630, 0.126, 0.252, 0.504, 1.01, 2.02, 4.03],
      vials: [1,2,3,4,5,6,7],
      newRowValue: null,
    }
  },
  computed: {
    ...mapState('device', ['ods', "calibrationModeEnabled"]),
  },
  methods: {
    ...mapMutations('device', ['addODCalibrationRow']),
    ...mapActions("device", ["getAllDeviceData", "setPartStateAction", "measureDevicePart", 'removeODCalibrationRow','setPartCalibration']),
      async handleOdClick(odIndex) {
        await this.measureDevicePart({
          devicePart: "ods",
          partIndex: odIndex,
        });
        await this.getAllDeviceData();
        console.log(this.ods.states[odIndex]);  // Here is the specific OD state
      },
    clearRow(odValue, index) {
      // Remove the odValue from the odValues array
      this.odValues.splice(index, 1);
      // Dispatch the removeODValue action to update the Vuex state
      // this.removeODValue(odValue);

      // Update your measurements as needed.
    },
    addNewRow() {
      // Add the new row value to the odValues array
      if (this.newRowValue !== null) {
        this.addODCalibrationRow(this.newRowValue)
        const odValue = parseFloat(this.newRowValue);
        this.odValues.push(odValue);
        console.log("pushed new row value", odValue);
        // Clear the input field for the next new row
        this.newRowValue = null;
      }
    },
    updateODValue(event, index) {
      this.odValues[index] = parseFloat(event.target.value)
    },
    measure(odValue) {
      for (let vial of this.vials) {
        this.setPartCalibration({
          devicePart: 'ods',
          partIndex: vial,
          calibration: {
            [odValue]: 0.1,
          },
        });
      }
    },
  }
}
</script>

<style scoped>
table {
  justify-content: center;
  width: 780px;
  margin: 0 auto;
}

th, td {
  border: none;
  /*padding: 8px;*/
  text-align: center;
}

.calibration-signal {
  width: 60px;
}

button {
  background-color: #2a8c93;
  color: white;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 16px;
  cursor: pointer;
  border-radius: 12px;
  /*padding: 5px 5px;*/
  transition-duration: 0.4s;
  opacity: 60%;
}

.button-delete {
  background-color: #f26b6b;
}

.button-new {
  background-color: #04b241;
  opacity: 80%;
  margin: 15px 0px;
  padding: 5px 5px;
}

button:hover {
  cursor: pointer;
  opacity: 100%;
}

.od-button{
  text-align: center;
  font-weight: bold;
  color: darkred;
  font-size: 15px;
  padding: 2px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background-color: #f2d388;
  border: none;
  box-shadow: 0px 5px 10px rgba(0, 0, 0, 0.2);
  transition: background-color 0.05s;
}

.od-button:active {
  background-color: #f26b6b;
  transition: background-color 0.05s;
}

.od-output-value {
  font-size: 15px;
  font-weight: bold;
/*  100px wide*/
}

input {
  width: 70px;
  box-sizing: border-box;
  font-size: 12px;
/*  hide arrows*/
}
</style>
