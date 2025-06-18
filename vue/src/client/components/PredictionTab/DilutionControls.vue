<template>
  <div class="dilution-controls">
    <h3>Configuration helpers</h3>
    <v-table>
      <thead>
        <tr>
          <th></th>
          <th v-for="vial in vials" :key="vial">Vial {{ vial }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td></td>
          <td v-for="vial in vials" :key="vial">
            <v-btn
              color="success"
              @click="openGrowthParametersSettings(vial)"
              class="dilution-button"
            >
              <v-icon left>mdi-chart-bell-curve-cumulative</v-icon>
              Dose Response
            </v-btn>
          </td>
        </tr>
        <tr>
          <td></td>
          <td v-for="vial in vials" :key="vial">
            <v-btn
              color="secondary"
              @click="openChemostatSettings(vial)"
              class="dilution-button"
            >
              <v-icon left>mdi-flask</v-icon>
              Chemostat
            </v-btn>
          </td>
        </tr>
        <tr>
          <td></td>
          <td v-for="vial in vials" :key="vial">
            <v-btn
              color="info"
              @click="openMorbidostatSettings(vial)"
              class="dilution-button"
            >
              <v-icon left>mdi-skull</v-icon>
              Morbidostat
            </v-btn>
          </td>
        </tr>
        <tr>
          <td></td>
          <td v-for="vial in vials" :key="vial">
            <v-btn
              color="warning"
              @click="openSettings(vial)"
              class="dilution-button">
            <v-icon left>mdi-pump-off</v-icon>
              Dilutions Off
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>

    <!-- Add DilutionSettings dialog -->
    <v-dialog v-model="showSettings" max-width="600">
      <DilutionSettings
        v-if="showSettings"
        :vialId="selectedVial"
        @close="handleSettingsClose"
        @confirm="handleSettingsConfirm"
      />
    </v-dialog>

    <!-- Add MorbidostatSettings dialog -->
    <v-dialog v-model="showMorbidostatSettings" max-width="600">
      <MorbidostatSettings
        v-if="showMorbidostatSettings"
        :vialId="selectedVial"
        @close="handleMorbidostatSettingsClose"
        @confirm="handleSettingsConfirm"
      />
    </v-dialog>

    <!-- Add ChemostatSettings dialog -->
    <v-dialog v-model="showChemostatSettings" max-width="600">
      <ChemostatSettings
        v-if="showChemostatSettings"
        :vialId="selectedVial"
        @close="handleChemostatSettingsClose"
        @confirm="handleSettingsConfirm"
      />
    </v-dialog>

    <!-- Add GrowthParametersSettings dialog -->
    <v-dialog v-model="showGrowthParametersSettings" max-width="600">
      <GrowthParametersSettings
        v-if="showGrowthParametersSettings"
        :vialId="selectedVial"
        @close="handleGrowthParametersSettingsClose"
        @confirm="handleSettingsConfirm"
      />
    </v-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import DilutionSettings from './DilutionSettings.vue'
import MorbidostatSettings from './MorbidostatSettings.vue'
import ChemostatSettings from './ChemostatSettings.vue'
import GrowthParametersSettings from './GrowthParametersSettings.vue'
import { useExperimentStore } from '@/client/stores/experiment'

const emit = defineEmits(['settings-updated'])
const vials = [1, 2, 3, 4, 5, 6, 7]
const showSettings = ref(false)
const showMorbidostatSettings = ref(false)
const showChemostatSettings = ref(false)
const showGrowthParametersSettings = ref(false)
const selectedVial = ref(null)
const experimentStore = useExperimentStore()

function openSettings(vial) {
  selectedVial.value = vial
  showSettings.value = true
}

function openMorbidostatSettings(vial) {
  selectedVial.value = vial
  showMorbidostatSettings.value = true
}

function openChemostatSettings(vial) {
  selectedVial.value = vial
  showChemostatSettings.value = true
}

function openGrowthParametersSettings(vial) {
  selectedVial.value = vial
  showGrowthParametersSettings.value = true
}

function handleSettingsClose() {
  showSettings.value = false
}

function handleMorbidostatSettingsClose() {
  showMorbidostatSettings.value = false
}

function handleChemostatSettingsClose() {
  showChemostatSettings.value = false
}

function handleGrowthParametersSettingsClose() {
  showGrowthParametersSettings.value = false
}

async function handleSettingsConfirm() {
  showSettings.value = false
  showMorbidostatSettings.value = false
  showChemostatSettings.value = false
  showGrowthParametersSettings.value = false
  // Refresh the experiment data to show updated values
  await experimentStore.fetchCurrentExperiment()
  // Emit event to refresh the control parameters table
  emit('settings-updated')
}
</script>

<style scoped>
.dilution-controls {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

h3 {
  margin: 0 0 10px 0;
  font-size: 1.2em;
  color: #333;
}

:deep(.v-table) {
  background: transparent !important;
  width: fit-content;
  margin: 0 auto;
}

:deep(.v-table__wrapper) {
  background: transparent !important;
  width: fit-content;
}

:deep(.v-table__wrapper > table) {
  background: transparent !important;
  width: fit-content;
}

:deep(.v-table__wrapper > table > thead > tr > th) {
  color: #fff !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  font-weight: 500;
}

:deep(.v-table__wrapper > table > tbody > tr > td) {
  color: #fff !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  padding: 4px 8px !important;
}

:deep(.v-table__wrapper > table > tbody > tr:hover) {
  background: rgba(255, 255, 255, 0.05) !important;
}

.dilution-button {
  width: 160px;
  height: 32px;
  font-size: 14px;
  font-weight: normal;
}
</style> 