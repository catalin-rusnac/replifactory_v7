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
    </v-container>
  </v-app>
</template>

<script>
import { mapState } from "vuex";
import { defineAsyncComponent } from "vue";
import '@mdi/font/css/materialdesignicons.css';

const components = {
  ExperimentTab: () => import("@/client/components/ExperimentTab/ExperimentTab.vue"),
  PredictionTab: () => import("@/client/components/PredictionTab/PredictionTab.vue"),
  DeviceControl: () => import("./components/DeviceControl/DeviceControl.vue"),
  NgrokTab: () => import("@/client/components/Remote/NgrokTab.vue"),
  HelpTab: () => import("@/client/components/HelpTab/HelpTab.vue"),
  StatusTab: () => import("@/client/components/StatusTab/StatusTab.vue"),
  LogsTab: () => import("@/client/components/LogsTab/LogsTab.vue"),
  SelfTest: () => import("@/client/components/DeviceControl/SelfTest/SelfTest.vue"),
};

export default {
  name: "App",
  data() {
    return {
      drawer: true,
      currentTab: "Experiment",
      tabs: [
        { name: "Experiment", component: "ExperimentTab", icon: "mdi-flask" },
        { name: "Prediction", component: "PredictionTab", icon: "mdi-chart-bell-curve-cumulative" },
        { name: "Device Control", component: "DeviceControl", icon: "mdi-robot-industrial" },
        { name: "Device Test", component: "SelfTest", icon: "mdi-robot" },
        { name: "Ngrok", component: "NgrokTab", icon: "mdi-remote-desktop" },
        { name: "Docs", component: "HelpTab", icon: "mdi-book-open-variant" },
        { name: "Status", component: "StatusTab", icon: "mdi-monitor-eye" },
        { name: "Logs", component: "LogsTab", icon: "mdi-file-document-alert-outline" },
      ],
    };
  },
  computed: {
    ...mapState(["hostname"]),
    currentComponent() {
      const activeTab = this.tabs.find((tab) => tab.name === this.currentTab);
      return activeTab ? activeTab.component : null;
    },
  },
  async mounted() {
    await this.$store.dispatch("fetchHostname");
    document.title = this.hostname;
  },
  methods: {
    selectTab(tabName) {
      this.currentTab = tabName;
    },
  },
  components: {
    ...Object.fromEntries(
      Object.entries(components).map(([key, value]) => [key, defineAsyncComponent(value)])
    ),
  },
};
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
