<template>
  <div class="experiment-parameters">
    <div class="stock-parameters">
      <template v-for="(value, key) in currentExperiment.parameters" :key="key">
        <v-text-field
          v-if="key !== 'cultures' && key !== 'growth_parameters'"
          class="stock-parameter-field"
          :label="`${key}`"
          v-model="this.currentExperiment.parameters[key]"
          :readonly="currentExperiment.status === 'running'"
          @update:modelValue="handleInputChange(key, $event)"
        ></v-text-field>
      </template>
<!--      TODO: arrange pump order-->
    </div>
  </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import { VTextField } from "vuetify/components";

export default {
  components: {
    VTextField,
  },
  computed: {
    ...mapState('experiment', ['currentExperiment']),
  },
  methods: {
    ...mapActions('experiment', ['updateExperimentParameters']),
    async handleInputChange(key, value) {
      // Update the parameter in the local state
      this.currentExperiment.parameters[key] = value;

      // Send updated parameters to the Vuex store or backend
      await this.updateExperimentParameters({
        experimentId: this.currentExperiment.id,
        parameters: this.currentExperiment.parameters,
      });
    },
  },
};
</script>

<style scoped>
.experiment-parameters {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.stock-parameters {
  display: flex;
  flex-wrap: wrap; /* Allow wrapping if screen width is too small */
  gap: 10px; /* Space between the fields */
  justify-content: space-between; /* Distribute fields evenly */
  margin-top: 20px; /* Add space above the parameter fields */
}

.stock-parameter-field {
  flex: 1 1 350px; /* Set flexible basis and width */
  max-width: 350px; /* Prevent fields from growing beyond 350px */
  margin: 0; /* Remove margin; spacing is handled by gap */
}

@media (max-width: 768px) {
  .stock-parameters {
    justify-content: center; /* Center fields on smaller screens */
  }
}
</style>
