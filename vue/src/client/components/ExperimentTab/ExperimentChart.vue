<template>
  <div id="CulturePlot">
    <div class="control-container">
      <div class="button-row">
        <CButton class="plot-button" color="success" @click="plotAllData">Plot Data</CButton>
        <div class="button-container">
          <div v-for="vial in vials" :key="vial" class="button-item">
            <CButton
              :color="selectedVials[vial] ? 'primary' : 'secondary'"
              :style="{ 'background-color': selectedVials[vial] ? '#007bff' : 'transparent' }"
              @click="toggleVial(vial, $event)"
              :id="`vial-button-${vial}`"
            >
              {{ `Vial ${vial}` }}
            </CButton>
          </div>
        </div>
      </div>
    </div>

    <div v-for="vial in filteredVials" :key="vial">
      <VialPlot :vial="vial" :data="plot_data[vial]" />
    </div>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { CButton } from '@coreui/vue';
import VialPlot from './VialPlot.vue';

export default {
  components: {
    CButton,
    VialPlot,
  },
  name: "ExperimentChart",
  computed: {
    ...mapState('experiment', ['currentExperiment', 'selectedVials', 'plot_data']),
    filteredVials() {
      return this.vials.filter(vial => this.selectedVials[vial]);
    }
  },
  data() {
    return {
      vials: [1, 2, 3, 4, 5, 6, 7], // 7 vials
    };
  },
  methods: {
    ...mapActions('experiment', ['fetchCulturePlot', 'setSelectedVials']),

    async plotAllData() {
      if (!this.currentExperiment) {
        return;
      }
      for (let vial of this.filteredVials) {
        await this.fetchCulturePlot(vial);
      }
    },

    async toggleVial(vial, event) {
      let updatedVials;
      if (event.ctrlKey) {
        updatedVials = { [vial]: true };
      } else {
        updatedVials = { ...this.selectedVials, [vial]: !this.selectedVials[vial] };
      }
      this.setSelectedVials(updatedVials);
      if (updatedVials[vial]) {
        await this.fetchCulturePlot(vial);
      }
    },
  },
  mounted() {
    this.plotAllData();
  },
}
</script>

<style scoped>
#CulturePlot {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
}
.control-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 800px;
  margin-bottom: 20px;
}

.button-row {
  display: flex;
  align-items: center;
}

.plot-button {
  width: fit-content;
  min-width: 120px;
  height: 60px;
}

.button-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  width: 100%;
}

.button-item {
  margin: 5px;
}
</style>
