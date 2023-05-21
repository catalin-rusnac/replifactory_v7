<template>
  <div class="od-control-container">
        <div class="elements-container" v-for="(od, index) in ods.states" :key="index">
          <button class="od-button" @click="handleOdClick(index)">
            <span>OD {{ index }}</span>
          </button>
              <span class="od-output-value" v-if="ods.states && ods.states[index] !== undefined">{{ parseFloat(ods.states[index].toFixed(2))}}</span>
          <div style="height: 0.5px;"></div>
              <span class="signal-output-value" v-if="ods.odsignals && ods.odsignals[index] !== undefined">({{ parseFloat(ods.odsignals[index].toFixed(2)) }}mV)</span>
        </div>
  </div>
<!--  Header "OD calibration"-->
  <div v-if="calibrationModeEnabled">
      <table>
    <thead>
      <tr>
        <th>OD value</th>
        <th></th>
        <th v-for="vial in vials" :key="vial">{{ 'vial ' + vial }}</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="odValue in allOdValues" :key="odValue">
        <td>
          <input :value="odValue" @change="updateODCalibrationKeyAction({oldOD: odValue, newOD: $event.target.value})" type="number" step="0.1" />
        </td>
        <td>
          <button @click="measureODCalibrationAction({odValue:odValue})">Measure</button>
        </td>
        <td v-for="vial in vials" :key="vial">
          <input class="calibration-signal" @change="updateODCalibrationValueAction({od: odValue, odsIndex:vial, newValue:$event.target.value})" v-model="ods.calibration[vial][odValue]" type="number" style="opacity: 60%" />
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
          <button class="button button-new" @click="measureODCalibrationAction({odValue: newRowValue})">Measure new probe</button>
        </td>
      </tr>
    </tbody>
  </table>

      <div class="chart-container">
        <ODChart v-for="vial in vials" :partId="vial" :key="vial"></ODChart>
      </div>
  </div>
</template>

<script>
import {mapState, mapActions} from 'vuex';
import ODChart from './ODChart.vue';

export default {
  components: {
    ODChart,
  },
  data() {
    return {
      // odValues: [0.00788, 0.0158, 0.0315, 0.0630, 0.126, 0.252, 0.504, 1.01, 2.02, 4.03],
      vials: [1,2,3,4,5,6,7],
      newRowValue: null,
    }
  },
  computed: {
    ...mapState('device', ['ods', "calibrationModeEnabled"]),
    allOdValues() {
      let allOdValuesSet = new Set();
      for(let vial in this.ods.calibration) {
        for(let odValue in this.ods.calibration[vial]) {
          allOdValuesSet.add(odValue);
        }
      }
      return Array.from(allOdValuesSet);
    }
  },
  methods: {
    ...mapActions("device", ["getAllDeviceData", "setPartStateAction", "measureDevicePart", "measureODCalibrationAction",
      "setPartCalibrationAction","removeODCalibrationRowAction", 'updateODCalibrationKeyAction', "updateODCalibrationValueAction"]),
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
.chart-container {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  width: 850px;
  justify-content: center;
  align-items: center;
  margin: 0 auto;
}

.chart-container > div {
  /*flex: 1;*/
  width: 270px;
  height: 200px;
  margin-right: 10px;
  margin-bottom: 10px;
}

table {
  justify-content: center;
  width: 780px;
  margin: 0 auto;
  margin-top: 10px;
}

th, td {
  border: none;
  /*padding: 8px;*/
  text-align: center;
}

.calibration-signal {
  width: 60px;
}

.od-control-container {
  display: flex;
  justify-content: center;
  /*flex-wrap: wrap;*/
  width: 850px;
  margin: 0 auto;
  /*margin-top: 10px;*/
}


.elements-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  margin-right: 10px;
  margin-left: 10px;
  margin-top: 0;
  width: 90px;
  /*height: 300px;*/
  border: 1px solid #e3e3e3; /* Sets the color of the border */
  border-radius: 10px; /* Adjust as needed to create the level of roundness you desire */
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
  color: #651717;
  font-size: 15px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background-color: #f2d388;
  border: none;
  box-shadow: 0px 5px 10px rgba(0, 0, 0, 0.2);
  transition: background-color 0.05s;
  /*margin: 0 20px;*/
  margin-top: 10px;
}

.od-button:active {
  background-color: #f26b6b;
  transition: background-color 0.05s;
}

.od-output-value {
  font-size: 14px;
  font-weight: bold;
  color: rgba(103, 76, 76, 0.54);
  margin-top: 5px;
  padding: 0;
}

.signal-output-value {
  font-size: 9px;
  color: #808080;
  margin-top: 0px;
}

input {
  width: 70px;
  box-sizing: border-box;
  font-size: 12px;
/*  hide arrows*/
}
</style>
