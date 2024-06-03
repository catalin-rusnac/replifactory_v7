<template>
    <div v-if="Object.keys(currentExperiment?.parameters?.growth_parameters || {}).length > 0">
      <TableComponent
        :key="currentExperiment.id"
        :fetchData="fetchCulturesData"
        :updateData="updateCulturesData"
        tableTitle="Culture Growth Parameters"
        :columnHeaders="['Vial 1', 'Vial 2', 'Vial 3', 'Vial 4', 'Vial 5', 'Vial 6', 'Vial 7']"
        rowHeaderLabel="Parameter"
        :rowHeaderWidth="270"
      />
    </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import TableComponent from "../PredictionTab/TableComponent.vue";

export default {
  components: {
    TableComponent,
  },
  computed: {
    ...mapState('experiment', ['currentExperiment']),
  },
  methods: {
    ...mapActions('experiment', ['updateExperimentParameters']),
    async handleInputChange(key, value) {
      await this.updateExperimentParameters({
        experimentId: this.currentExperiment.id,
        parameters: {
          ...this.currentExperiment.parameters, [key]: value,
        },
      });
    },
    fetchCulturesData() {
      const cultures = this.currentExperiment.parameters.growth_parameters;
      const keys = Object.keys(cultures[1]);
      const data = keys.map(key => Object.keys(cultures).map(vial => cultures[vial][key]));

      return { data, keys };
    },
    async updateCulturesData(data) {
      const rowNames = Object.keys(this.currentExperiment.parameters.growth_parameters[1]);
      const columnNames = Object.keys(this.currentExperiment.parameters.growth_parameters);
      for (let v = 0; v < columnNames.length; v++) {
        for (let r = 0; r < rowNames.length; r++) {
          this.currentExperiment.parameters.growth_parameters[columnNames[v]][rowNames[r]] = data[r][v];
        }
      }
      await this.updateExperimentParameters({
        experimentId: this.currentExperiment.id,
        parameters: this.currentExperiment.parameters,
      });
    },
  },
};
</script>

<style scoped>
</style>
