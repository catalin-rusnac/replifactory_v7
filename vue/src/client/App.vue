<template>
  <div id="app">
    <ul class="nav nav-tabs" id="myTab">
      <li class="nav-item" v-for="tab in tabs" :key="tab">
        <a class="nav-link" :class="{ active: currentTab === tab }" href="#" @click="currentTab = tab">{{ tab }}</a>
      </li>
    </ul>
    <div class="tab-content">
<!--      <HomeTab v-if="currentTab === 'Home'"/>-->
      <ExperimentTab v-if="currentTab === 'Experiment'"/>
      <DeviceControl v-if="currentTab === 'Device'" />
      <NgrokTab v-if="currentTab === 'Remote'" />
      <HelpTab v-if="currentTab === 'Help'" />
      <StatusTab v-if="currentTab === 'Status'"/>
      <LogsTab v-if="currentTab === 'Logs'"/>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';

import DeviceControl from './components/DeviceControl/DeviceControl';
// import HomeTab from '@/client/components/HomeTab/HomeTab';
import ExperimentTab from "@/client/components/ExperimentTab/ExperimentTab";
import NgrokTab from "@/client/components/Remote/NgrokTab";
import HelpTab from "@/client/components/HelpTab/HelpTab";
import StatusTab from "@/client/components/StatusTab/StatusTab";
import LogsTab from "@/client/components/LogsTab/LogsTab";

export default {
  name: 'App',
  computed: {
  ...mapState(['hostname']),
  },
  async mounted() {
    await this.$store.dispatch('fetchHostname');
  document.title = this.hostname;
},

  components: {
    ExperimentTab,
    DeviceControl,
    NgrokTab,
    HelpTab,
    StatusTab,
    LogsTab
  },
  data() {
    return {
      currentTab: 'Experiment',
      tabs: ['Experiment', 'Device', 'Remote', 'Help', "Status", "Logs"]
    };
  },
};
</script>

<style>
#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin: 0 auto;
  max-width: 1024px;
}
</style>