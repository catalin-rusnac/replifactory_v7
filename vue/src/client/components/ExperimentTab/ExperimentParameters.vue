<template>
  <div class="experiment-parameters">
    <div class="stock-parameters">
      <template v-for="(value, key) in currentExperiment.parameters" :key="key">
<!--        if key not cultures or growth_parameters-->
        <CFormFloating class="stock-parameter-field" v-if="key !== 'cultures' && key !== 'growth_parameters'">
          <CFormInput
            :class="{ 'active': currentExperiment.status !== 'running' }"
            :model-value="value"
            @update:model-value="v => currentExperiment.parameters[key] = v"
            :id="`floatingInput_${key}`"
            :floating-label="`${key}`"
            :placeholder="`Enter ${key}`"
            :readonly="currentExperiment.status === 'running'"
            @change="handleInputChange(key, $event.target.value)"
          />
        </CFormFloating>
      </template>
    </div>

  </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import { CFormFloating, CFormInput } from "@coreui/vue";
// import TableComponent from "../PredictionTab/TableComponent.vue";

export default {
  components: {
    CFormFloating,
    CFormInput,
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
  },
};
</script>

<style scoped>
.experiment-parameters {
  display: flex;
  flex-direction: column;
  max-width: 100%;
  margin-left: 1rem;
}

.stock-parameters, .culture-parameters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
}

.stock-parameter-field {
  flex: 0 1 220px;
  max-width: 320px;
  margin: 10px;
}

@media (max-width: 768px) {
  .stock-parameters {
    flex-wrap: wrap;
  }
  .stock-parameter-field {
    flex: 1 1 100%;
  }
}
</style>
