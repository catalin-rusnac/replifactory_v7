<template>
    <table>
    </table>
    <table>

      <tbody>
      <tr>
        <td v-for="(od, index) in ods.states" :key="index">
          <button class="od-button" @click="handleOdClick(index)">
            <span>OD {{ index }}</span>
          </button>
        </td>
      </tr>
      <tr>
        <td v-for="(od, index) in ods.states" :key="index">
          <span class="od-output-value" v-if="ods.states && ods.states[index] !== undefined">{{ parseFloat(ods.states[index].toFixed(2))}}</span>
          <div style="height: 0.5px;"></div>
          <span class="od-output-value" v-if="ods.odsignals && ods.odsignals[index] !== undefined">({{ parseFloat(ods.odsignals[index].toFixed(2)) }}mV)</span>
        </td>
      </tr>
      </tbody>
    </table>
<!--  Header "OD calibration"-->
    <table>
    <thead v-if="calibrationModeEnabled">
        <tr>
          <th>OD value</th>
          <th></th>
          <th v-for="vial in vials" :key="vial">{{ 'vial ' + vial }}</th>
          <th></th>
        </tr>
      </thead>
      <tbody v-if="calibrationModeEnabled">
        <tr v-for="(index,odValue) in ods.calibration[1]" :key="index">
          <td>
            <input :value="odValue" @change="updateODCalibrationKeyAction({oldOD: odValue, newOD: $event.target.value})" type="number" step="0.1" />
          </td>

          <td>
            <button @click="measureODCalibrationAction({odValue:odValue})">Measure</button>
          </td>
          <td v-for="vial in vials" :key="vial">
            <input class="calibration-signal" v-model="ods.calibration[vial][odValue]" type="number" style="opacity: 60%"/>
          </td>
          <td>
            <button class="button button-delete" @click="removeODCalibrationRowAction(odValue)">Delete Row</button>
          </td>
        </tr>
        <tr>
          <td>
            <input v-model="newRowValue" type="number" step="0.1" />
          </td>
          <td>
            <button class="button button-new"
                @click="addODCalibrationRowAction(newRowValue)">New Probe</button>
          </td>
        </tr>
      </tbody>
    </table>
</template>

<script>
import {mapState, mapActions} from 'vuex';


export default {
  data() {
    return {
      // odValues: [0.00788, 0.0158, 0.0315, 0.0630, 0.126, 0.252, 0.504, 1.01, 2.02, 4.03],
      vials: [1,2,3,4,5,6,7],
      newRowValue: null,
    }
  },
  computed: {
    ...mapState('device', ['ods', "calibrationModeEnabled"]),
  },
  methods: {
    ...mapActions("device", ["getAllDeviceData", "setPartStateAction", "measureDevicePart", "measureODCalibrationAction",
      "setPartCalibrationAction","removeODCalibrationRowAction", 'updateODCalibrationKeyAction', "addODCalibrationRowAction"]),
      async handleOdClick(odIndex) {
        await this.measureDevicePart({
          devicePart: "ods",
          partIndex: odIndex,
        }).then(() => {
          this.getAllDeviceData();
        });
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
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: #f2d388;
  border: none;
  box-shadow: 0px 5px 10px rgba(0, 0, 0, 0.2);
  transition: background-color 0.05s;
  margin: 0 20px;
}

.od-button:active {
  background-color: #f26b6b;
  transition: background-color 0.05s;
}

.od-output-value {
  font-size: 16px;
  font-weight: bold;
  color: darkred;
  margin: 0;
  padding: 0;
}

input {
  width: 70px;
  box-sizing: border-box;
  font-size: 12px;
/*  hide arrows*/
}
</style>
