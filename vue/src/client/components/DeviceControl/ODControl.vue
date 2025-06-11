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
  
    <div v-if="calibrationModeEnabled" class="calibration-section">
      <div class="probe-table-outer-container" style="margin-bottom: 18px;">
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
        </div>
        <div class="state-table-container">
          <table class="state-table">
            <thead>
              <tr>
                <th class="state-header-empty"></th>
                <th v-for="(vial, idx) in vials" :key="'vial-header-' + vial" class="state-vial-header">
                  Vial {{ vial }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th class="state-row-label">Probe</th>
                <td v-for="(vial, idx) in vials" :key="'probe-' + vial" class="state-probe-cell" :style="getODBackgroundStyle(getHighlightedOdValue(vial))">
                  {{ getProbeForVial(vial) }}
                </td>
              </tr>
              <tr>
                <th class="state-row-label state-od-label">OD Value</th>
                <td v-for="(vial, idx) in vials" :key="'od-' + vial" class="state-od-cell" :style="getODBackgroundStyle(getHighlightedOdValue(vial))">
                  <span>{{ getHighlightedOdValue(vial) }}</span>
                </td>
              </tr>
              <tr>
                <th class="state-row-label" style="position: relative;">
                  <button class="control-button measure-inline" @click=measureAllODSignals :disabled="!editMode || isRemeasuring" :class="{ 'disabled-measure': !editMode }">
                    <span v-if="isRemeasuring">
                      <span class="loading-spinner"></span> Measuring...
                    </span>
                    <span v-else>
                      <v-icon>mdi-camera-metering-center</v-icon>
                      {{ highlightMode === 'diagonal' ? 'Measure Diagonal ' + (highlightIndex + 1) : 'Measure OD ' + allOdValues[highlightIndex] + ' signals' }}
                    </span>
                  </button>
                  <div v-if="!editMode" class="measure-overlay" @click="toast.error('Enable edit mode to measure calibration signals')"></div>
                </th>
                <td v-for="(vial, idx) in vials" :key="'signal-' + vial" class="state-signal-cell"
                    :class="{'highlighted': isHighlightedCell(getHighlightedOdValue(vial), vial)}"
                    :style="{ 'background': isHighlightedCell(getHighlightedOdValue(vial), vial) ? 'rgba(100, 149, 237, 0.15)' : getSignalBackgroundStyle(vial, getHighlightedOdValue(vial)).background }">
                  <span class="signal-value-text">
                    {{ getHighlightedSignal(vial) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="table-controls">
          <button class="control-button next-button" @click="nextHighlight">
            Select Next
          </button>
          <div class="segmented-toggle">
            <button
              class="toggle-segment"
              :class="{ active: highlightMode === 'diagonal' }"
              @click="highlightMode = 'diagonal'"
              type="button"
            >
              Diagonal
            </button>
            <button
              class="toggle-segment"
              :class="{ active: highlightMode === 'row' }"
              @click="highlightMode = 'row'"
              type="button"
            >
              Row
            </button>
          </div>
          <div class="autofill-group">
            <button class="control-button auto-round" @click=autofillValues() :disabled="isAutofilling.value">
              <span v-if="isAutofilling.value">
                <span class="loading-spinner"></span>
              </span>
              <span v-else>
                Auto
              </span>
            </button>
          </div>
          <div style="flex:1"></div>
          <button class="control-button mode-toggle" :class="{ 'edit-on': editMode }" @click="editMode = !editMode">
            <v-icon>{{ editMode ? 'mdi-pencil' : 'mdi-pencil-outline' }}</v-icon>
            Edit
          </button>
          <button class="control-button help-button" @click="openODGuide">
            <v-icon>mdi-help-circle-outline</v-icon>
          </button>
        </div>
      </div>
      <div class="calibration-controls">
      </div>
  
      <div class="calibration-table-wrapper">
        <table class="calibration-table">
          <thead>
            <tr class="scaling-factor-row">
              <th class="scaling-factor-label">Scaling Factor</th>
              <th v-for="(sf, idx) in scalingFactorsLocal" :key="'sf-head-' + idx" class="scaling-factor-cell">
                <template v-if="editMode">
                  <input type="number" step="0.01" min="0.1" v-model.number="scalingFactorsLocal[idx]" style="width: 60px; text-align: center; background: #23272e; color: #90caf9; border: 1px solid #444; border-radius: 4px;" />
                </template>
                <template v-else>
                  {{ typeof sf === 'number' ? sf.toFixed(2) : sf }}
                </template>
              </th>
              <th v-if="editMode" style="width: 36px;"></th>
            </tr>
            <tr>
              <th style="width: 110px;">OD Value</th>
              <th v-for="vial in vials" :key="vial" style="width: 90px;">Vial {{ vial }}</th>
              <th v-if="editMode" style="width: 36px;"></th>
            </tr>
          </thead>
          <tbody>
            <!-- All OD value rows, including OD 0 (blank) -->
            <tr v-for="(odValue, idx) in allOdValues" :key="odValue" :class="{ 'od-zero-row': parseFloat(odValue) === 0 }">
              <td style="width: 110px;" :style="getODBackgroundStyle(odValue)">
                <input
                  v-if="idx < probeOdValues.length"
                  :value="tempProbeValues[idx] !== undefined ? tempProbeValues[idx] : probeOdValues[idx]"
                  @input="handleProbeValueInput($event, idx)"
                  @blur="updateProbeValue(odValue, idx)"
                  @keyup.enter="updateProbeValue(odValue, idx)"
                  type="number"
                  step="0.1"
                  class="property-value"
                  style="text-align: center;" />
                <input
                  v-else
                  :value="odValue"
                  @change="updateODCalibrationKeyAction({oldOD: odValue, newOD: $event.target.value})"
                  type="number"
                  step="0.1"
                  class="property-value"
                  style="text-align: center;" />
              </td>
              <td v-for="vial in vials" :key="vial"
                  :class="{ 
                    'has-data': ods.calibration && ods.calibration[vial] && ods.calibration[vial][odValue] !== undefined,
                    'diagonal-cell': isHighlightedCell(odValue, vial)
                  }"
                  :style="{ 'background': isHighlightedCell(odValue, vial) ? 'rgba(100, 149, 237, 0.15)' : getSignalBackgroundStyle(vial, odValue).background }">
                <template v-if="editMode">
                  <input 
                    :value="getCalibrationInputValue(vial, odValue)"
                    @input="handleSignalInput($event, vial, odValue)"
                    @blur="updateSignalValue(vial, odValue)"
                    @keyup.enter="updateSignalValue(vial, odValue)"
                    type="number" 
                    class="calibration-signal" />
                </template>
                <template v-else>
                  <span v-if="ods.calibration && ods.calibration[vial] && ods.calibration[vial][odValue] !== undefined" class="signal-value">
                    {{ parseFloat(ods.calibration[vial][odValue]).toFixed(2) }}mV
                  </span>
                  <span v-else>
                    <!-- Removed the little measure button as requested -->
                  </span>
                </template>
              </td>
              <td v-if="editMode" style="text-align: center; width: 36px; padding: 4px;">
                <button class="delete-od-row" @click="deleteODRow(idx)" :disabled="deletingRows.has(allOdValues[idx])">
                  <v-icon>mdi-delete</v-icon>
                </button>
              </td>
            </tr>
            <tr v-if="editMode">
              <td>
                <button class="add-od-probe-table" @click="addODProbe">
                  <v-icon>mdi-plus</v-icon> Add
                </button>
              </td>
              <td v-for="vial in vials" :key="'add-row-' + vial"></td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>
  
      <div class="chart-container" v-if="showCharts">
        <ODChart v-for="vial in vials" :partId="vial" :key="vial"></ODChart>
      </div>
    </div>
    <ODGuide v-if="showODGuide" @close="closeODGuide" />
  </template>
  
  <script setup>
  import { ref, computed, watch, onMounted } from 'vue'
  import { storeToRefs } from 'pinia'
  import { useDeviceStore } from '../../stores/device'
  import ODChart from './ODChart.vue'
  import { useGuideDialog } from '@/client/composables/useGuideDialog'
  import ODGuide from './ODGuide.vue'
  import { useDialog } from '@/client/composables/useDialog'
  import { toast } from 'vue3-toastify'
  import ConfirmDialog from '@/client/components/ConfirmDialog.vue'
  
  const deviceStore = useDeviceStore()
  const {
    ods,
    calibrationModeEnabled
  } = storeToRefs(deviceStore)
  
  const { openGuide } = useGuideDialog()
  const { openDialog } = useDialog()
  
  const vials = [1, 2, 3, 4, 5, 6, 7]
  const editMode = ref(false)
  const showCharts = ref(true)
  const highlightMode = ref('row')
  const highlightIndex = ref(0)
  const isRemeasuring = ref(false)
  const isAutofilling = ref(false)
  const tempProbeValues = ref({})
  const tempCalibrationValues = ref({})
  const allOdValues = computed(() => {
    let allOdValuesSet = new Set()
    if (ods.value.calibration) {
      for (let vial in ods.value.calibration) {
        for (let odValue in ods.value.calibration[vial]) {
          allOdValuesSet.add(odValue)
        }
      }
    }
    const values = Array.from(allOdValuesSet).sort((a, b) => parseFloat(a) - parseFloat(b))
    return values
  })

  const showODGuide = ref(false)

  const probeOdValues = computed(() => {
    // Get all unique OD values from the calibration dict
    if (!ods.value.calibration) return [];
    const odSet = new Set();
    for (const vial in ods.value.calibration) {
      for (const od in ods.value.calibration[vial]) {
        odSet.add(parseFloat(od));
      }
    }
    return Array.from(odSet).sort((a, b) => a - b);
  });

  const deletingRows = ref(new Set());

  // Add computed for scaling factors per vial
  const scalingFactors = computed(() => {
    const coefs = ods.value.calibration_coefs || {};
    return vials.map(vial => coefs[vial]?.[1] ?? '—');
  });

  // Add local editable scaling factors
  const scalingFactorsLocal = ref([]);

  // Sync local scaling factors with backend values when calibration_coefs changes
  watch(scalingFactors, (newFactors) => {
    scalingFactorsLocal.value = [...newFactors];
  }, { immediate: true });

  // Set scalingFactor to the highlighted vial's scaling by default
  watch([highlightIndex, highlightMode, () => ods.value.calibration_coefs], () => {
    const vial = highlightMode.value === 'diagonal'
      ? (vials[(highlightIndex.value) % vials.length])
      : (vials[highlightIndex.value]);
    const scaling = ods.value.calibration_coefs?.[vial]?.[1];
  }, { immediate: true });

  onMounted(() => {
    deviceStore.fetchDeviceData();
  });

  async function handleOdClick(odIndex) {
    await deviceStore.measureDevicePart({
      devicePart: "ods",
      partIndex: odIndex,
    })
    await deviceStore.fetchDeviceData()
  }
  
  function handleSignalInput(event, vial, odValue) {
      // Initialize the vial's temporary values if needed
      if (!tempCalibrationValues.value[vial]) {
        tempCalibrationValues.value[vial] = {};
      }
      
      // Store the temporary value
      tempCalibrationValues.value[vial][odValue] = parseFloat(event.target.value);
    }

function updateSignalValue(vial, odValue) {
    if (tempCalibrationValues.value[vial] && tempCalibrationValues.value[vial][odValue] !== undefined) {
    if (!ods.value.calibration[vial]) {
        ods.value.calibration[vial] = {};
    }
    
    const newValue = tempCalibrationValues.value[vial][odValue]
    
    if (isNaN(tempCalibrationValues.value[vial][odValue])) {
      delete ods.value.calibration[vial][odValue];
    }
    deviceStore.updateODCalibrationValueAction({
        od: odValue,
        vial: vial,
        newValue: newValue
    }).catch(error => {
        console.error(`Error updating calibration for vial ${vial}:`, error);
    });
    delete tempCalibrationValues.value[vial][odValue];
    }
}

  async function measureAllODSignals() {
    isRemeasuring.value = true
    try {
      // Build the vial_ods mapping: {1: od1, 2: od2, ...}
      const vial_ods = {}
      vials.forEach((vial, idx) => {
        vial_ods[vial] = getHighlightedOdValue(vial)
      })
      console.log(vial_ods)
      await deviceStore.measureAllODSignalsAction({ vial_ods })
      await deviceStore.fetchDeviceData()
    } catch (e) {
      // Optionally handle error
    } finally {
      isRemeasuring.value = false
    }
  }
  
  function getCalibrationInputValue(vial, odValue) {
      // Check if we have a temporary value first
      if (tempCalibrationValues.value[vial] && tempCalibrationValues.value[vial][odValue] !== undefined) {
        return tempCalibrationValues.value[vial][odValue];
      }
      
      // Otherwise return the actual calibration value
      return ods.value.calibration && ods.value.calibration[vial] && ods.value.calibration[vial][odValue] !== undefined
        ? ods.value.calibration[vial][odValue]
        : '';
    }

  function getHighlightedOdValue(vial) {
    if (highlightMode.value === 'diagonal') {
      const rowIndex = (vial - 1 - highlightIndex.value + allOdValues.value.length) % allOdValues.value.length
      return allOdValues.value[rowIndex] || '-'
        } else {
      return allOdValues.value[highlightIndex.value] || '-'
    }
  }
  
  function getProbeLabel(index) {
    // Generate Excel-style column labels: A, B, ..., Z, AA, AB, ...
    let label = '';
    index = Math.floor(index);
    while (index >= 0) {
      label = String.fromCharCode(65 + (index % 26)) + label;
      index = Math.floor(index / 26) - 1;
    }
    return label;
  }

  function getProbeForVial(vial) {
    let probeIndex;
    if (highlightMode.value === 'diagonal') {
      probeIndex = (vial - 1 - highlightIndex.value + allOdValues.value.length) % allOdValues.value.length;
    } else {
      probeIndex = highlightIndex.value;
    }
    return getProbeLabel(probeIndex);
  }
  
  function getSignalBackgroundStyle(vial, odValue) {
    if (!ods.value.calibration || !ods.value.calibration[vial] || ods.value.calibration[vial][odValue] === undefined) {
      return { background: '' }
    }
    const signal = parseFloat(ods.value.calibration[vial][odValue])
    const minBrightness = 5
    const maxBrightness = 40
    let brightness
    if (signal <= 0) {
      brightness = minBrightness
            } else {
      const logMin = Math.log(10)
      const logMax = Math.log(1000)
      const logValue = Math.log(Math.max(10, Math.min(1000, signal)))
      const percentage = (logValue - logMin) / (logMax - logMin)
      brightness = minBrightness + percentage * (maxBrightness - minBrightness)
    }
    return { background: `rgba(255, 100, 100, ${brightness / 100})` }
  }
  
  function getODBackgroundStyle(odValue) {
        if (odValue === undefined || odValue === null) {
      return ''
        }
    const od = parseFloat(odValue)
        if (isNaN(od)) {
      return ''
    }
    const minOpacity = 0.02
    const maxOpacity = 0.25
    const clampedOD = Math.max(0, Math.min(4, od))
    const logScale = Math.log(clampedOD + 1) / Math.log(5)
    const opacity = minOpacity + logScale * (maxOpacity - minOpacity)
    return `background: linear-gradient(to right, rgba(255, 235, 156, ${opacity}), rgba(255, 235, 156, ${opacity * 0.6}))`
  }
  
  function getHighlightedSignal(vial) {
    const odValue = getHighlightedOdValue(vial)
    if (odValue === '-') return '-'
    const signal = ods.value.calibration &&
      ods.value.calibration[vial] &&
      ods.value.calibration[vial][odValue] !== undefined
      ? parseFloat(ods.value.calibration[vial][odValue]).toFixed(2) + ' mV' : '-'
    return signal
  }
  
  function isHighlightedCell(odValue, vial) {
    const odRowIndex = allOdValues.value.indexOf(odValue)
    if (odRowIndex === -1) return false
    if (highlightMode.value === 'diagonal') {
      return (vial - 1 - highlightIndex.value + allOdValues.value.length) % allOdValues.value.length === odRowIndex
    } else {
      return odRowIndex === highlightIndex.value
    }
  }
  
  function toggleHighlightMode() {
    highlightMode.value = highlightMode.value === 'diagonal' ? 'row' : 'diagonal';
  }
  
  function nextHighlight() {
    if (allOdValues.value.length === 0) return;
    highlightIndex.value = (highlightIndex.value + 1) % allOdValues.value.length;
  }
  
  // Use local scaling factor for autofill
  async function autofillValues() {
    const confirmed = await openDialog({
      title: 'Autofill Calibration Table?',
      message: 'Use blank and scaling factor to autofill the rest of the table.',
    });
    if (!confirmed) return;

    isAutofilling.value = true;

    // Prepare a new calibration object
    const newCalibration = {};
    vials.forEach((vial, idx) => {
      // OD0 could be stored as "0", "0.0", or 0 - need to check all possibilities
      let blank = null;
      if (ods.value.calibration && ods.value.calibration[vial]) {
        if (ods.value.calibration[vial]["0"] !== undefined) {
          blank = parseFloat(ods.value.calibration[vial]["0"]);
        } else if (ods.value.calibration[vial]["0.0"] !== undefined) {
          blank = parseFloat(ods.value.calibration[vial]["0.0"]);
        } else if (ods.value.calibration[vial][0] !== undefined) {
          blank = parseFloat(ods.value.calibration[vial][0]);
        }
      }
      if (blank === null) {
        blank = 500;
      }
      newCalibration[vial] = {};
      newCalibration[vial]["0"] = blank;
      probeOdValues.value.forEach((od) => {
        if (parseFloat(od) === 0) return;
        // Use local scaling factor for this vial
        const scaling = parseFloat(scalingFactorsLocal.value[idx]) || 1.6;
        const simulated = blank * Math.pow(10, -parseFloat(od / scaling));
        newCalibration[vial][od.toString()] = simulated;
      });
      deviceStore.setPartCalibrationAction({ devicePart: 'ods', partIndex: vial, newCalibration: newCalibration[vial] })
    });
    isAutofilling.value = false
    await deviceStore.fetchDeviceData()
    isAutofilling.value = false
  }
  
  function updateProbeValue(odValue, idx) {
    if (tempProbeValues.value[idx] !== undefined) {
      probeOdValues.value[idx] = tempProbeValues.value[idx]
      delete tempProbeValues.value[idx]
      for (let vial in ods.value.calibration) {
        console.log("changing od value for vial", vial, "from", odValue, "to", probeOdValues.value[idx])  
        console.log("old_calibration", ods.value.calibration[vial])
        const old_calibration = ods.value.calibration[vial]
        const new_calibration = JSON.parse(JSON.stringify(old_calibration))
        delete new_calibration[odValue]
        new_calibration[probeOdValues.value[idx]] = old_calibration[odValue]
        console.log("new_calibration", new_calibration)
        deviceStore.setPartCalibrationAction({ devicePart: 'ods', partIndex: vial, newCalibration: new_calibration })
      }
    }
  }
  
  function handleProbeValueInput(event, idx) {
    console.log("handleProbeValueInput", event.target.value)
    tempProbeValues.value[idx] = parseFloat(event.target.value)
  }

  async function saveCalibration() {
      try {
        await deviceStore.saveCalibrationToBackend();
        console.log('Device calibration saved successfully');
      } catch (error) {
        console.error('Error saving device calibration:', error);
        // Show a more user-friendly error message
        const errorMessage = typeof error === 'string' ? error : 
                           error.response?.data?.message || 
                           error.message || 
                           'Failed to save calibration. Please try again.';
        alert('Failed to save calibration: ' + errorMessage);
      }
    }
    
    
    function onFileSelected(event) {
      const file = event.target.files[0];
      if (!file) return;
      
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const data = JSON.parse(e.target.result);
          
          // Check if we have proper calibration data
          if (!data.calibration) {
            throw new Error('Invalid calibration format: missing calibration data');
          }
          
          // Set the calibration data in our local state first
          ods.value.calibration = { ...data.calibration };
          
          // Then update the calibration curves
          await deviceStore.setAllODCalibrationsAction(data.calibration);
          
        } catch (error) {
          console.error('Error parsing calibration file:', error);
          alert('Invalid calibration file format: ' + error.message);
        }
      };
      reader.readAsText(file);
    }
  
  function openODGuide() {
    showODGuide.value = true;
  }
  
  function closeODGuide() {
    showODGuide.value = false;
  }
  
  async function clearTable() {
    const confirmed = await openDialog({
      title: 'Clear Calibration Table',
      message: 'Are you sure you want to clear all calibration values? This action cannot be undone unless you saved a checkpoint.',
      showCancel: true
    });
    if (confirmed) {
      // Clear all calibration values for all vials
      for (const vial in ods.value.calibration) {
        deviceStore.setPartCalibrationAction({ devicePart: 'ods', partIndex: vial, newCalibration: {} });
      }
      await deviceStore.fetchDeviceData();
    }
  }
  
  function getNextODValue() {
    // Find the next OD value (e.g., max + 0.1)
    if (!probeOdValues.value.length) return 0.1;
    const max = Math.max(...probeOdValues.value);
    return parseFloat((max + 0.1).toFixed(2));
  }

  async function addODProbe() {
    const newOD = getNextODValue();
    // Add the new OD value to all vials in the calibration dict
    for (const vial of vials) {
      if (!ods.value.calibration[vial]) ods.value.calibration[vial] = {};
      ods.value.calibration[vial][newOD] = 0; // Default signal value
      // Update backend for each vial
      await deviceStore.setPartCalibrationAction({ devicePart: 'ods', partIndex: vial, newCalibration: ods.value.calibration[vial] });
    }
    await deviceStore.fetchDeviceData();
  }
  
  async function deleteODRow(idx) {
    const odToDelete = allOdValues.value[idx];
    deletingRows.value.add(odToDelete);
    for (const vial of vials) {
      if (ods.value.calibration[vial]) {
        delete ods.value.calibration[vial][odToDelete];
        await deviceStore.setPartCalibrationAction({ devicePart: 'ods', partIndex: vial, newCalibration: ods.value.calibration[vial] });
      }
    }
    await deviceStore.fetchDeviceData();
    deletingRows.value.delete(odToDelete);
  }
  
  </script>
  
  <style scoped>
  .od-control-container {
    display: flex;
    justify-content: center;
    width: 850px;
    margin: 0 auto;
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
    border: 1px solid #e3e3e3;
    border-radius: 10px;
  }
  
  .od-button {
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
    margin-top: 10px;
  }
  
  .od-button:active {
    background-color: #f26b6b;
    transition: background-color 0.05s;
  }
  
  .od-output-value {
    font-size: 14px;
    font-weight: bold;
    color: rgb(189, 46, 46);
    margin-top: 5px;
    padding: 0;
  }
  
  .signal-output-value {
    font-size: 9px;
    color: #808080;
    margin-top: 0px;
  }
  
  /* New styles for calibration UI */
  .calibration-section {
    width: 850px;
    margin: 20px auto;
  }
  
  .calibration-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
  }
  
  .action-buttons {
    display: flex;
    gap: 10px;
  }
  
  .action-button {
    background-color: #2a8c93;
    color: white;
    border: none;
    padding: 8px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    opacity: 0.8;
  }
  
  .action-button:hover {
    opacity: 1;
  }
  
  .save {
    background-color: #4caf50;
  }
  
  .load {
    background-color: #2196f3;
  }
  
  .calibration-table-wrapper {
    position: relative;
    width: 100%;
  }
  
  .calibration-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
  }
  
  .calibration-table th, 
  .calibration-table td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: center;
  }
  
  .calibration-table th {
    background-color: transparent;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .blank-row {
    background-color: rgba(255, 251, 230, 0.3);
  }
  
  .has-data {
    /* Removed background color for data cells */
  }
  
  .diagonal-cell {
    box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.7) !important;
    border-radius: 2px !important;
    position: relative;
    z-index: 1;
    background-color: rgba(100, 149, 237, 0.15) !important;
  }
  
  .property-value {
    width: 70px;
    text-align: center;
    padding: 5px;
    border-radius: 4px;
    border: 1px solid #ccc;
  }
  
  .calibration-signal {
    width: 70px;
    text-align: center;
    padding: 5px;
    border-radius: 4px;
    border: 1px solid #ccc;
  }
  
  .measure-button {
    background-color: #2a8c93;
    color: white;
    border: none;
    padding: 5px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
  }
  
  .measure-button:hover {
    opacity: 0.9;
  }
  
  .signal-value-text {
    font-size: 13px;
    color: rgba(200, 200, 200, 0.8);
  }
  
  .signal-value {
    font-size: 13px;
    color: rgba(200, 200, 200, 0.8);
    background: transparent !important;
  }
  
  .button-delete {
    background-color: #f26b6b;
    border-radius: 5px;
    width: 95px;
  }
  
  .button-delete:disabled {
    cursor: not-allowed;
    background-color: #f26b6b;
    opacity: 0.3;
  }
  
  .button-new {
    background-color: #04b241;
    opacity: 0.8;
    width: 190px;
    border-radius: 5px;
    padding: 5px 5px;
  }
  
  .chart-container {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    width: 850px;
    justify-content: center;
    align-items: center;
    margin: 20px auto;
  }
  
  .chart-container > div {
    width: 270px;
    height: 200px;
    margin-right: 10px;
    margin-bottom: 10px;
  }
  
  .od-probe-rectangle {
    background: rgba(255,255,255,0.55);
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border: 1px solid #e0e0e0;
    padding: 18px 12px 10px 12px;
    width: 100%;
    max-width: 700px;
    margin: 0 auto 18px auto;
    backdrop-filter: blur(1px);
  }
  
  .state-table-container {
    width: 100%;
    overflow-x: auto;
  }
  
  .state-table {
    width: 100%;
    text-align: center;
    border-collapse: separate;
    border-spacing: 20px 0;
    margin-bottom: 10px;
  }
  
  .state-table th, .state-table td {
    padding: 8px 5px;
    font-weight: 500;
    position: relative;
    width: 90px;
  }
  
  .state-table td {
    width: 90px;
  }
  
  .state-header-empty {
    width: 80px;
  }
  
  .state-vial-header {
    color: rgba(255, 255, 255, 0.9);
    font-size: 14px;
    font-weight: 500;
    padding-bottom: 12px;
    width: 90px;
  }
  
  .state-row-label {
    text-align: right;
    color: rgba(255, 255, 255, 0.8);
    font-weight: 500;
    width: 80px;
  }
  
  .state-od-label {
    color: rgba(255, 120, 120, 0.9);
  }
  
  .state-signal-label {
    color: rgba(200, 200, 200, 0.6);
    font-size: 13px;
  }
  
  .state-probe-cell {
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .state-od-cell {
    color: rgba(255, 120, 120, 0.9);
    font-weight: 600;
    position: relative;
  }
  
  .state-od-cell.highlighted, .state-signal-cell.highlighted {
    box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.7);
    border-radius: 2px;
    position: relative;
    z-index: 1;
    background-color: rgba(100, 149, 237, 0.15) !important;
  }
  
  .state-signal-cell {
    color: rgba(200, 200, 200, 0.6);
    font-size: 13px;
    position: relative;
  }
  
  .measure-button {
    font-size: 13px;
    padding: 6px 10px;
    opacity: 0.9;
  }
  
  .probe-table tr:nth-child(2) th {
    color: #fff;
  }
  
  .loading-spinner {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    border-top-color: white;
    animation: spin 1s linear infinite;
    margin-right: 5px;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .action-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  .state-controls {
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
    width: 100%;
  }
  
  .icon-button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    background-color: rgba(42, 140, 147, 0.8);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .icon-button:hover {
    background-color: rgba(42, 140, 147, 1);
  }
  
  .icon-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .icon-button.save {
    background-color: rgba(76, 175, 80, 0.8);
  }
  
  .icon-button.save:hover {
    background-color: rgba(76, 175, 80, 1);
  }
  
  .icon-button.load {
    background-color: rgba(33, 150, 243, 0.8);
  }
  
  .icon-button.load:hover {
    background-color: rgba(33, 150, 243, 1);
  }
  
  .icon-button.mode-toggle {
    background-color: rgba(150, 150, 150, 0.8);
  }
  
  .icon-button.mode-toggle:hover {
    background-color: rgba(150, 150, 150, 1);
  }
  
  .table-controls {
    display: flex;
    gap: 10px;
    margin-top: 10px;
    margin-bottom: 20px;
    justify-content: flex-start;
    flex-wrap: wrap;
    align-items: center;
  }
  
  .bottom-controls {
    margin-top: 15px;
  }
  
  .control-button {
    background-color: rgba(42, 140, 147, 0.8);
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
    height: 32px;
    display: flex;
    align-items: center;
  }
  
  .control-button:hover {
    background-color: rgba(42, 140, 147, 1);
  }
  
  .control-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .control-button.mode-toggle {
    background-color: rgba(150, 150, 150, 0.8);
  }
  
  .control-button.mode-toggle:hover {
    background-color: rgba(150, 150, 150, 1);
  }
  
  /* Make calibration table OD value styling match state table */
  .calibration-table .property-value {
    color: rgba(255, 120, 120, 0.9);
    font-weight: bold;
  }
  
  /* Fix signal value styling in calibration table */
  .signal-value {
    background: none !important;
    color: rgba(200, 200, 200, 0.8);
  }
  
  .measure-inline {
    width: 100%;
    padding: 12px 5px;
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin: 0;
    height: 64px;
    background-color: rgba(168, 92, 92, 0.8);
  }
  
  .state-row-label .control-button {
    margin-left: auto;
  }
  
  .control-input-group {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0 6px;
  }
  
  .scaling-factor-input {
    width: 60px;
    padding: 6px;
    border-radius: 4px;
    border: 1px solid #ddd;
    font-size: 14px;
    text-align: center;
  }
  
  label {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
  }
  
  .control-button.mode-toggle.edit-on {
    background-color: #2196f3;
    color: #fff;
    border: 2px solid #2196f3;
    font-weight: bold;
  }
  
  .segmented-toggle {
    display: inline-flex;
    border-radius: 999px;
    overflow: hidden;
    border: 2px solid #444;
    background: #222;
    margin-right: 18px;
    height: 32px;
    align-items: center;
  }
  
  .toggle-segment {
    padding: 7px 18px;
    border: none;
    background: none;
    color: #bbb;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s, color 0.2s;
    outline: none;
    font-size: 14px;
    height: 28px;
    line-height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .toggle-segment.active {
    background: rgba(42, 140, 147, 0.8);  
    color: #fff;
    font-weight: bold;
  }
  
  .autofill-group {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0;
    border-radius: 8px;
    background: none;
    border: none;
    margin: 0 10px;
  }
  
  .help-button {
    background: none;
    color: #bbb;
    border: none;
    font-size: 22px;
    padding: 0 8px;
    margin-left: 6px;
    cursor: pointer;
    transition: color 0.2s, box-shadow 0.2s;
  }
  
  .help-button:hover {
    color: #2ac0c7;
    box-shadow: 0 0 6px #2ac0c7;
  }
  
  .add-od-probe {
    background: #388e3c;
    color: #fff;
    font-weight: bold;
    margin-left: 6px;
    transition: background 0.2s, color 0.2s;
  }
  
  .add-od-probe:disabled {
    background: #bbb;
    color: #eee;
    cursor: not-allowed;
  }
  
  .add-od-probe-table {
    background: #388e3c;
    color: #fff;
    font-weight: bold;
    border-radius: 6px;
    border: none;
    padding: 4px 14px;
    font-size: 15px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    transition: background 0.2s, color 0.2s;
  }
  
  .add-od-probe-table:hover {
    background: #2e7031;
  }
  
  .add-od-row-wrapper {
    position: absolute;
    left: 0;
    top: 100%;
    margin-top: 8px;
    margin-bottom: 18px;
    display: flex;
    align-items: flex-start;
    z-index: 2;
  }
  
  .delete-od-row {
    background: #f26b6b;
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 2px 2px;
    cursor: pointer;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
    margin: 0 auto;
    min-width: 0;
  }
  
  .delete-od-row:hover {
    background: #b71c1c;
  }
  
  .disabled-measure {
    background-color: #bbb !important;
    color: #eee !important;
    border: none !important;
    cursor: not-allowed !important;
    opacity: 0.7;
  }
  
  .measure-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 10;
    /* cursor: pointer; */
    cursor: not-allowed;
    background: transparent;
  }
  
  /* Add styles for scaling factor row */
  .scaling-factor-row {
    background: #23272e;
  }
  .scaling-factor-label {
    background: #23272e;
    color: #90caf9;
    font-weight: 700;
    border: 1px solid #444;
    text-align: center;
  }
  .scaling-factor-cell {
    background: #23272e;
    color: #90caf9;
    font-weight: 500;
    border: 1px solid #444;
    text-align: center;
  }
  
  .auto-round {
    border-radius: 50%;
    width: 54px;
    height: 54px;
    min-width: 54px;
    min-height: 54px;
    max-width: 54px;
    max-height: 54px;
    padding: 0;
    font-size: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    background: #43a047;
    color: #fff;
    border: none;
    box-shadow: 0 2px 8px rgba(67,160,71,0.08);
    transition: background 0.2s, color 0.2s;
  }
  .auto-round:hover:not(:disabled) {
    background: #388e3c;
    color: #fff;
  }
  
  .next-button {
    min-width: 64px;
    font-size: 14px;
    font-weight: 500;
  }
  
  .od-zero-row th, .od-zero-row td {
    font-weight: bold;
    color: #fff;
  }
  </style>
  