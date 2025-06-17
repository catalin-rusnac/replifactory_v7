<template>
    <div class="od-control-container">
      <div class="elements-container" v-for="(od, index) in ods.states" :key="index">
        <button class="od-button" @click="handleOdClick(index)" :disabled="loadingOdIndex === index">
          <v-progress-circular
            v-if="loadingOdIndex === index"
            indeterminate
            color="white"
            size="24"
          ></v-progress-circular>
          <span v-else>OD {{ index }}</span>
        </button>
        <span class="od-output-value error-message" 
              v-if="odErrors[index]">{{ odErrors[index] }}</span>
        <span class="od-output-value" 
              :class="{ 'value-being-replaced': loadingOdIndex === index }"
              v-else-if="ods.states && ods.states[index] !== undefined && ods.states[index] !== 0">{{ parseFloat(ods.states[index].toFixed(2))}}</span>
        <span class="od-output-value" 
              :class="{ 'value-being-replaced': loadingOdIndex === index }"
              v-else>---</span>
        <div style="height: 0.5px;"></div>
        <span class="signal-output-value error-message" 
              v-if="odErrors[index]"></span>
        <span class="signal-output-value" 
              :class="{ 'value-being-replaced': loadingOdIndex === index }"
              v-else-if="ods.odsignals && ods.odsignals[index] !== undefined && ods.odsignals[index] !== 0">({{ parseFloat(ods.odsignals[index].toFixed(2)) }}mV)</span>
        <span class="signal-output-value" 
              :class="{ 'value-being-replaced': loadingOdIndex === index }"
              v-else>(---)</span>
      </div>
    </div>
  
    <div v-if="calibrationModeEnabled" class="calibration-section">
      <div class="probe-table-outer-container" style="margin-bottom: 18px;">
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
        </div>
        <div class="table-controls">
          <div style="flex:1"></div>
          <div class="mode-controls">
            <button 
              class="control-button mode-toggle" 
              :class="{ 'active': currentMode === TABLE_MODES.MEASURE }"
              @click="currentMode = currentMode === TABLE_MODES.MEASURE ? TABLE_MODES.VIEW : TABLE_MODES.MEASURE">
              <v-icon>mdi-pencil</v-icon>
              Edit
            </button>
          </div>
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
                <div class="od-value-container">
                  <span v-if="!editingOdValue || editingOdValue !== odValue"
                        class="od-value-display"
                        @dblclick="startEditingOdValue(odValue, idx)"
                        title="Double click to edit">
                    {{ idx < probeOdValues.length ? (tempProbeValues[idx] !== undefined ? tempProbeValues[idx] : probeOdValues[idx]) : odValue }}
                  </span>
                  <input v-else
                         :value="tempProbeValues[idx] !== undefined ? tempProbeValues[idx] : probeOdValues[idx]"
                         @input="handleProbeValueInput($event, idx)"
                         @blur="updateProbeValue(odValue, idx, $event)"
                         @keyup.enter="updateProbeValue(odValue, idx, $event)"
                         @keyup.esc="cancelOdValueEditing"
                         type="number"
                         step="0.1"
                         class="od-value-input"
                         ref="odValueInput" />
                </div>
              </td>
              <td v-for="vial in vials" :key="vial"
                  :class="{ 
                    'has-data': ods.calibration && ods.calibration[vial] && ods.calibration[vial][odValue] !== undefined
                  }"
                  :style="{ 'background': getSignalBackgroundStyle(vial, odValue).background }">
                <!-- View Mode -->
                <template v-if="currentMode === TABLE_MODES.VIEW">
                  <template v-if="ods.calibration && ods.calibration[vial] && ods.calibration[vial][odValue] !== undefined && ods.calibration[vial][odValue] !== null">
                    <template v-if="parseFloat(odValue) === 0">
                      <div class="signal-value-with-status" :title="getOD0SignalStatus(ods.calibration[vial][odValue]).tooltip">
                        {{ ods.calibration[vial][odValue].toFixed(2) }}
                        <v-icon :color="getOD0SignalStatus(ods.calibration[vial][odValue]).color" size="small" style="margin-left: 4px;">
                          {{ getOD0SignalStatus(ods.calibration[vial][odValue]).icon }}
                        </v-icon>
                      </div>
                    </template>
                    <template v-else>
                      <div class="signal-value">
                        {{ ods.calibration[vial][odValue].toFixed(2) }}
                      </div>
                    </template>
                  </template>
                  <template v-else>
                    <div class="signal-value">---</div>
                  </template>
                </template>
                
                <!-- Measure Mode -->
                <template v-else-if="currentMode === TABLE_MODES.MEASURE">
                  <div class="measure-cell-container">
                    <span v-if="ods.calibration && ods.calibration[vial] && ods.calibration[vial][odValue] !== undefined && ods.calibration[vial][odValue] !== null" 
                          class="signal-value measure-background-value"
                          @dblclick="startEditing(vial, odValue)"
                          title="Double click to edit">
                      {{ parseFloat(ods.calibration[vial][odValue]).toFixed(2) }}mV
                    </span>
                    <span v-else
                          class="signal-value measure-background-value empty-value"
                          @dblclick="startEditing(vial, odValue)"
                          title="Double click to edit">
                      ———
                    </span>
                    <input v-if="editingCell && editingCell.vial === vial && editingCell.odValue === odValue"
                           :value="getCalibrationInputValue(vial, odValue)"
                           @input="handleSignalInput($event, vial, odValue)"
                           @blur="finishEditing(vial, odValue)"
                           @keyup.enter="finishEditing(vial, odValue)"
                           @keyup.esc="cancelEditing"
                           type="number" 
                           class="calibration-signal"
                           ref="editingInput" />
                    <button 
                      class="measure-cell-button"
                      @click="handleCellMeasure(vial, odValue)"
                      :disabled="isRemeasuring"
                      :title="`Calibrate OD ${parseFloat(odValue).toFixed(2)} signal in vial ${vial} (measure now)`">
                      <span v-if="isRemeasuring" class="measure-button-content">
                        <span class="loading-spinner"></span>
                      </span>
                      <span v-else class="measure-button-content">
                        <v-icon>mdi-camera-metering-center</v-icon>
                      </span>
                    </button>
                  </div>
                </template>
              </td>
              <!-- Delete button column - visible in measure mode -->
              <td v-if="currentMode === TABLE_MODES.MEASURE && parseFloat(allOdValues[idx]) !== 0" style="text-align: center; width: 36px; padding: 4px;">
                <button class="delete-od-row" @click="deleteODRow(idx)" :disabled="deletingRows.has(allOdValues[idx])" title="Delete row">
                  <v-icon>mdi-delete</v-icon>
                </button>
              </td>
              <td v-else-if="currentMode === TABLE_MODES.MEASURE" style="width: 36px;"></td>
            </tr>
            <!-- Add row button - visible in measure mode -->
            <tr v-if="currentMode === TABLE_MODES.MEASURE">
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

      <!-- Scaling Factor Row moved below the table -->
      <div class="scaling-factor-container">
        <table class="calibration-table">
          <tbody>
            <tr class="scaling-factor-row">
              <th class="scaling-factor-label">Scaling Factor</th>
              <th v-for="(sf, idx) in scalingFactorsLocal" :key="'sf-head-' + idx" class="scaling-factor-cell" :title="getScalingFactorStatus(sf, idx + 1).tooltip">
                <template v-if="editMode">
                  <input type="number" step="0.01" min="0.1" v-model.number="scalingFactorsLocal[idx]" style="width: 60px; text-align: center; background: #23272e; color: #90caf9; border: 1px solid #444; border-radius: 4px;" />
                </template>
                <template v-else>
                  <div class="scaling-factor-value">
                    {{ typeof sf === 'number' ? sf.toFixed(2) : sf }}
                    <v-icon :color="getScalingFactorStatus(sf, idx + 1).color" size="small" style="margin-left: 4px;">
                      {{ getScalingFactorStatus(sf, idx + 1).icon }}
                    </v-icon>
                  </div>
                </template>
              </th>
              <th v-if="currentMode === TABLE_MODES.MEASURE" style="width: 40px;"></th>
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
  import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
  import { storeToRefs } from 'pinia'
  import { useDeviceStore } from '../../stores/device'
  import ODChart from './ODChart.vue'
  import { useGuideDialog } from '@/client/composables/useGuideDialog'
  import ODGuide from './ODGuide.vue'
  import { useDialog } from '@/client/composables/useDialog'
import { toast } from 'vue3-toastify'
import ConfirmDialog from '@/client/components/ConfirmDialog.vue'
import api from '@/api'
  
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
  const showODGuide = ref(false)
  const isRemeasuring = ref(false)
  const loadingOdIndex = ref(null)
  const odErrors = ref({})
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

  onMounted(() => {
    deviceStore.fetchDeviceData();
    // Add document click handler
    document.addEventListener('click', handleDocumentClick);
    

  });

  onUnmounted(() => {
    // Remove document click handler
    document.removeEventListener('click', handleDocumentClick);
  });

  function handleDocumentClick(event) {
    // If we're editing and the click is outside the input
    if (editingCell.value && !event.target.closest('.calibration-signal')) {
      finishEditing(editingCell.value.vial, editingCell.value.odValue);
    }
    // If we're editing OD value and the click is outside the input
    if (editingOdValue.value && !event.target.closest('.od-value-input')) {
      const idx = probeOdValues.value.indexOf(editingOdValue.value);
      if (idx !== -1) {
        updateProbeValue(editingOdValue.value, idx, event);
      }
      editingOdValue.value = null;
    }
  }

  async function handleOdClick(odIndex) {
    console.log('handleOdClick called with odIndex:', odIndex, typeof odIndex);
    if (loadingOdIndex.value !== null) {
      return; // Prevent multiple simultaneous measurements
    }

    loadingOdIndex.value = odIndex;
    // Clear any previous error for this OD
    delete odErrors.value[odIndex];
    
    try {
      console.log('Starting OD measurement for index:', odIndex);
      // Make direct API call to properly catch errors
      const response = await api.post('/measure-ods', { partIndex: odIndex });
      console.log('Raw API response:', response);
      
      if (response.data.success) {
        console.log('OD measurement successful for index:', odIndex);
        // Update device data on success
        await deviceStore.fetchDeviceData();
        // Clear any error if measurement succeeds
        delete odErrors.value[odIndex];
      } else {
        console.log('API returned failure for index:', odIndex);
        throw new Error(response.data.message || 'Measurement failed');
      }
    } catch (error) {
      console.error('Error measuring OD:', error);
      console.log('Setting error for OD index:', odIndex);
      // Store error message for this specific OD
      const errorMessage = error.response?.data?.message || 
                          error.message || 
                          'Measurement failed';
      // Force reactivity by creating a new object
      odErrors.value = { ...odErrors.value, [odIndex]: errorMessage };
      console.log('Error set for odIndex:', odIndex, 'error:', errorMessage);
      console.log('Full odErrors object:', odErrors.value);
    } finally {
      loadingOdIndex.value = null;
    }
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
  
  async function updateProbeValue(odValue, idx, event) {
    if (tempProbeValues.value[idx] !== undefined) {
      const newValue = tempProbeValues.value[idx];
      
      // Check if newValue already exists in probeOdValues (excluding current idx)
      const exists = probeOdValues.value.some((v, i) => i !== idx && parseFloat(v) === parseFloat(newValue));
      
      if (exists) {
        const proceed = await openDialog({
          title: 'Duplicate OD Value',
          message: `An OD probe value of ${newValue} already exists. Are you sure you want to overwrite?`,
          showCancel: true
        });
        
        if (!proceed) {
          // Reset temp value and do not update
          delete tempProbeValues.value[idx];
          return;
        }
      }

      // Update the probe value
      probeOdValues.value[idx] = newValue;
      delete tempProbeValues.value[idx];

      // Update calibration data for all vials
      try {
        for (let vial in ods.value.calibration) {
          const old_calibration = ods.value.calibration[vial];
          const new_calibration = JSON.parse(JSON.stringify(old_calibration));
          
          // Only update if the old value exists
          if (old_calibration[odValue] !== undefined) {
            delete new_calibration[odValue];
            new_calibration[newValue] = old_calibration[odValue];
            
            await deviceStore.setPartCalibrationAction({ 
              devicePart: 'ods', 
              partIndex: vial, 
              newCalibration: new_calibration 
            });
          }
        }
        // Fetch updated device data to get new calibration coefficients
        await deviceStore.fetchDeviceData();
      } catch (error) {
        console.error('Error updating calibration:', error);
        toast.error('Failed to update calibration values');
      }
    }
  }
  
  function handleProbeValueInput(event, idx) {
    console.log("handleProbeValueInput", event.target.value)
    tempProbeValues.value[idx] = parseFloat(event.target.value)
  }
  
  function openODGuide() {
    showODGuide.value = true;
  }
  
  function closeODGuide() {
    showODGuide.value = false;
  }
  
  function getNextODValue() {
    // Find the next OD value (e.g., max + 0.1)
    if (!probeOdValues.value.length) return 0.1;
    const max = Math.max(...probeOdValues.value);
    return parseFloat((max + 0.1).toFixed(2));
  }

  async function addODProbe() {
    const newOD = getNextODValue();
    // Add the new OD value to all vials with null
    for (const vial of vials) {
      if (!ods.value.calibration[vial]) ods.value.calibration[vial] = {};
      ods.value.calibration[vial][newOD] = null;
      // Update backend for each vial
      await deviceStore.setPartCalibrationAction({ 
        devicePart: 'ods', 
        partIndex: vial, 
        newCalibration: ods.value.calibration[vial]
      });
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
  
  // Replace the TypeScript code with JavaScript version
  const TABLE_MODES = {
    VIEW: 'view',
    MEASURE: 'measure'
  };

  // Replace the editMode ref with a mode ref
  const currentMode = ref(TABLE_MODES.VIEW);

  // Add a computed property for mode-specific classes
  const modeClasses = computed(() => ({
    'view-mode': currentMode.value === TABLE_MODES.VIEW,
    'measure-mode': currentMode.value === TABLE_MODES.MEASURE
  }));

  // Add a function to handle cell clicks in measure mode
  async function handleCellMeasure(vial, odValue) {
    try {
      // First measure the signal
      await deviceStore.measureDevicePart({
        devicePart: 'ods',
        partIndex: vial
      });

      // Get the new signal value from the ods ref
      const newSignal = ods.value.odsignals[vial];
      
      // Update the calibration value with the new measurement
      await deviceStore.updateODCalibrationValueAction({
        od: odValue,
        vial: vial,
        newValue: newSignal
      });

      // Refresh the device data to show the updated values
      await deviceStore.fetchDeviceData();
    } catch (error) {
      console.error('Error measuring cell:', error);
    }
  }
  
  const editingCell = ref(null);
  const editingInput = ref(null);

  function startEditing(vial, odValue) {
    editingCell.value = { vial, odValue };
    // Wait for the input to be rendered before focusing
    nextTick(() => {
      const input = document.querySelector('.calibration-signal');
      if (input) {
        input.focus();
      }
    });
  }

  function finishEditing(vial, odValue) {
    if (tempCalibrationValues.value[vial] && tempCalibrationValues.value[vial][odValue] !== undefined) {
      updateSignalValue(vial, odValue);
    }
    editingCell.value = null;
  }

  function cancelEditing() {
    editingCell.value = null;
    // Reset any temporary values
    if (editingCell.value) {
      const { vial, odValue } = editingCell.value;
      if (tempCalibrationValues.value[vial]) {
        delete tempCalibrationValues.value[vial][odValue];
      }
    }
  }
  
  const editingOdValue = ref(null);

  function startEditingOdValue(odValue, idx) {
    editingOdValue.value = odValue;
    nextTick(() => {
      const input = document.querySelector('.od-value-input');
      if (input) {
        input.focus();
      }
    });
  }

  function cancelOdValueEditing() {
    editingOdValue.value = null;
    if (editingOdValue.value) {
      const idx = probeOdValues.value.indexOf(editingOdValue.value);
      if (idx !== -1 && tempProbeValues.value[idx]) {
        delete tempProbeValues.value[idx];
      }
    }
  }
  
  // Modify the getScalingFactorStatus function
  const getScalingFactorStatus = (value, vial) => {
    return { 
      icon: '',
      color: '#90caf9',
      tooltip: 'Scaling factor'
    };
  };
  
  // Add this function after getScalingFactorStatus
  const getOD0Status = (vial) => {
    const od0Value = ods.value.calibration?.[vial]?.['0'];
    if (typeof od0Value !== 'number') return { icon: 'mdi-help-circle-outline', color: 'grey' };
    
    if (od0Value >= 20) {
      return { icon: 'mdi-check-circle', color: '#4caf50' }; // green
    } else if (od0Value >= 12) {
      return { icon: 'mdi-alert-circle', color: '#ffc107' }; // yellow
    } else {
      return { icon: 'mdi-close-circle', color: '#f44336' }; // red
    }
  };
  
  // Modify the getOD0SignalStatus function
  const getOD0SignalStatus = (value) => {
    if (typeof value !== 'number') {
      return { 
        icon: 'mdi-help-circle-outline', 
        color: 'grey',
        tooltip: 'No signal value available'
      };
    }
    
    if (value >= 20) {
      return { 
        icon: 'mdi-check-circle', 
        color: '#4caf50',
        tooltip: 'Signal value within expected range'
      };
    } else if (value >= 12) {
      return { 
        icon: 'mdi-alert-circle', 
        color: '#ffc107',
        tooltip: 'Signal value slightly low. Consider recalibrating'
      };
    } else {
      return { 
        icon: 'mdi-close-circle', 
        color: '#f44336',
        tooltip: 'Signal value too low. Check OD sensor'
      };
    }
  };
  
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
    border: 1px solid #444;
    background: rgba(52, 52, 52, 0.9);
    color: #fff;
    position: absolute;
    left: 4px;
    z-index: 3;
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
    background-color: rgba(52, 52, 52, 0.8);
  }
  
  .icon-button.mode-toggle:hover {
    background-color: rgba(76, 76, 76, 0.9);
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
    background-color: rgba(52, 52, 52, 0.8);
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  
  .control-button.mode-toggle:hover {
    background-color: rgba(76, 76, 76, 0.9);
  }
  
  .control-button.mode-toggle.active {
    background-color: #2196f3;
    font-weight: bold;
  }
  
  .control-button.mode-toggle.active:hover {
    background-color: #1976d2;
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
  .scaling-factor-container {
    margin-top: 20px;
    width: 100%;
  }

  .scaling-factor-container .calibration-table {
    margin-bottom: 0;
  }

  .scaling-factor-row {
    background: #23272e;
  }

  .scaling-factor-label {
    background: #23272e;
    color: #90caf9;
    font-weight: 700;
    border: 1px solid #444;
    text-align: center;
    width: 110px;
  }

  .scaling-factor-cell {
    background: #23272e;
    color: #90caf9;
    font-weight: 500;
    border: 1px solid #444;
    text-align: center;
    width: 90px;
  }
  
  .measure-cell-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .measure-background-value {
    position: absolute;
    color: rgba(200, 200, 200, 0.4);
    z-index: 1;
    left: 1px;
  }
  
  .measure-cell-button {
    position: relative;
    background: rgba(168, 92, 92, 0.6);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    width: 28px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    z-index: 2;
    margin-left: auto;
  }
  
  .measure-button-content {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .measure-cell-button:hover:not(:disabled) {
    background: rgba(168, 92, 92, 0.8);
  }
  
  .measure-cell-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .empty-value {
    color: rgba(200, 200, 200, 0.3);
    cursor: pointer;
    letter-spacing: 2px;
  }
  
  .empty-value:hover {
    color: rgba(200, 200, 200, 0.5);
  }
  
  .od-value-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .od-value-display {
    color: rgba(255, 120, 120, 0.9);
    font-weight: bold;
    cursor: pointer;
  }
  
  .od-value-input {
    width: 70px;
    text-align: center;
    padding: 5px;
    border-radius: 4px;
    border: 1px solid #444;
    background: rgba(52, 52, 52, 0.9);
    color: #fff;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    z-index: 3;
  }
  
  .scaling-factor-value {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }
  
  .od-value-with-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }
  
  .signal-value-with-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }

  .value-being-replaced {
    color: #666;
    transition: color 0.3s ease;
  }

  .error-message {
    color: #ff6b6b !important;
    font-size: 11px !important;
    font-weight: bold;
    text-align: center;
    max-width: 80px;
    word-wrap: break-word;
    line-height: 1.2;
  }
  </style>
  