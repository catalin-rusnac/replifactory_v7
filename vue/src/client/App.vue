<template>
  <v-app :dark="true">
    <v-container>
      <!-- Navigation Drawer -->
      <v-navigation-drawer v-model="drawer" expand-on-hover rail>
<!--        <v-list-item v-if="drawer" title="Replifactory" subtitle="Experimental Evolution System" />-->
        <v-divider />
        <v-list density="compact" nav>
          <v-list-item
            v-for="tab in tabs"
            :key="tab.name"
            link
            @click="selectTab(tab.name)"
            :active="currentTab === tab.name"
            :title="tab.name"
            :prepend-icon="tab.icon"
            :value="tab.name"
          ></v-list-item>
        </v-list>
      </v-navigation-drawer>

      <!-- Tab Content -->
      <div class="tab-content">
        <component :is="currentComponent" v-if="currentComponent" />
      </div>

      <ConfirmDialog
        v-if="dialogState.show"
        :title="dialogState.title"
        :message="dialogState.message"
        :show-cancel="dialogState.showCancel"
        v-model="dialogState.show"
        @confirm="() => handle('yes')"
        @no="() => handle('no')"
        @cancel="() => handle('cancel')"
      />
    </v-container>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineAsyncComponent } from 'vue'
import { useHostStore } from '@/client/stores/host'
import '@mdi/font/css/materialdesignicons.css';
import { useDialog } from '@/client/composables/useDialog'
const { dialogState, handle } = useDialog()
import ConfirmDialog from '@/client/components/ConfirmDialog.vue'
import { useExperimentStore } from '@/client/stores/experiment'
const hostStore = useHostStore()

const components = {
  ExperimentTab: defineAsyncComponent(() => import("@/client/components/ExperimentTab/ExperimentTab.vue")),
  PredictionTab: defineAsyncComponent(() => import("@/client/components/PredictionTab/PredictionTab.vue")),
  DeviceControl: defineAsyncComponent(() => import("@/client/components/DeviceControl/DeviceControl.vue")),
  // NgrokTab: defineAsyncComponent(() => import("@/client/components/Remote/NgrokTab.vue")),
  PlotTab: defineAsyncComponent(() => import("@/client/components/PlotTab/PlotTab.vue")),
  GrowthRateTab: defineAsyncComponent(() => import("@/client/components/GrowthRateTab/GrowthRateTab.vue")),
  HelpTab: defineAsyncComponent(() => import("@/client/components/HelpTab/HelpTab.vue")),
  CameraTab: defineAsyncComponent(() => import("@/client/components/CameraTab/CameraTab.vue")),
  StatusTab: defineAsyncComponent(() => import("@/client/components/StatusTab/StatusTab.vue")),
  // LogsTab: defineAsyncComponent(() => import("@/client/components/LogsTab/LogsTab.vue")),
  SelfTest: defineAsyncComponent(() => import("@/client/components/DeviceControl/SelfTest/SelfTest.vue")),
};

const drawer = ref(true)
const currentTab = ref("Experiment")
const tabs = [
  { name: "Experiment", component: "ExperimentTab", icon: "mdi-flask" },
  { name: "Prediction", component: "PredictionTab", icon: "mdi-chart-bell-curve-cumulative" },
  { name: "Device Control", component: "DeviceControl", icon: "mdi-robot-industrial" },
  { name: "Device Test", component: "SelfTest", icon: "mdi-robot" },
  { name: "Camera", component: "CameraTab", icon: "mdi-camera" },
  // { name: "Ngrok", component: "NgrokTab", icon: "mdi-remote-desktop" },
  { name: "Docs", component: "HelpTab", icon: "mdi-book-open-variant" },
  { name: "Plot", component: "PlotTab", icon: "mdi-chart-line-variant" },
  { name: "Growth Rate", component: "GrowthRateTab", icon: "mdi-trending-up" },
  { name: "Export Data", component: "StatusTab", icon: "mdi-cloud-download" },
  // { name: "Logs", component: "LogsTab", icon: "mdi-file-document-alert-outline" },
]

const currentComponent = computed(() => {
  const activeTab = tabs.find((tab) => tab.name === currentTab.value)
  return activeTab ? components[activeTab.component] : null
})

onMounted(async () => {
  await hostStore.fetchHostname()
  document.title = hostStore.hostname
  const experimentStore = useExperimentStore()
  experimentStore.connectWebSocket()
})

watch(() => hostStore.hostname, (newVal) => {
  if (newVal) document.title = newVal
})

const selectTab = (tabName) => {
  currentTab.value = tabName
}
</script>

<style scoped>
#app {
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin: 0 auto;
}

.tab-content {
  padding: 20px;
}
</style>

<style>
/* Global styles for passive event optimization */
* {
  /* Optimize touch and scroll performance */
  touch-action: manipulation;
}

/* Specific optimizations for scrollable elements */
.v-container,
.v-main,
[class*="scroll"],
[class*="table"],
[class*="grid"] {
  -webkit-overflow-scrolling: touch;
  touch-action: manipulation;
}

/* RevoGrid specific optimizations */
revogrid-data,
revo-grid,
.rgCell,
.rgHeaderCell {
  touch-action: manipulation !important;
}
</style>
