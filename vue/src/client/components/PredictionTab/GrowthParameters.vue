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
      const customOrder = [
        'initial_population',
        'doubling_time_mins',
        'carrying_capacity',
        'mu_min',
        'ic50_initial',
        'ic10_ic50_ratio',
        'dose_effective_slope_width_mins',
        'time_lag_drug_effect_mins',
        'adaptation_rate_max',
        'adaptation_rate_ic10_ic50_ratio',
        'drug_concentration',
        'effective_dose'
      ];

      // Function to sort keys based on custom order and alphabetically
      const sortKeys = (keys) => {
        const customOrderSet = new Set(customOrder);
        const customOrderedKeys = customOrder.filter(key => keys.includes(key));
        const remainingKeys = keys.filter(key => !customOrderSet.has(key)).sort();
        return [...customOrderedKeys, ...remainingKeys];
      };

      const sortedKeys = sortKeys(keys);
      const sortedData = sortedKeys.map(key => Object.keys(cultures).map(vial => cultures[vial][key]));

      return { data: sortedData, keys: sortedKeys };
    },
    async updateCulturesData(data) {
      const sortedKeys = this.fetchCulturesData().keys;
      const columnNames = Object.keys(this.currentExperiment.parameters.growth_parameters);

      for (let v = 0; v < columnNames.length; v++) {
        for (let r = 0; r < sortedKeys.length; r++) {
          this.currentExperiment.parameters.growth_parameters[columnNames[v]][sortedKeys[r]] = data[r][v];
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
