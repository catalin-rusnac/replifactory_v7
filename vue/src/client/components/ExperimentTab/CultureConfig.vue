<template>
  <div class="culture-config">
    <h6>Culture {{ vial }}</h6>
      <div v-for="(value, key) in experiment.parameters.cultures[vial]" :key="key">
        <CFormInput
          :value="value"
          :placeholder="key"
          :id="`floatingInput_${key}_vial_${vial}`"
          :floating-label="`${key}`"

          @change="handleInputChange(key, $event.target.value)"
          v-b-tooltip.hover
          :title="`Tooltip for ${key}`"
        >
<!--add 2s delay before tooltip appears-->
          <b-tooltip :target="`floatingInput_${key}_vial_${vial}`" triggers="hover" placement="left" delay="500">
            {{key}}:<br> <span v-html="tooltips[key]"></span>
          </b-tooltip>
        </CFormInput>
      </div>
    </div>
</template>

<script>
import { CFormInput } from "@coreui/vue";
import { mapActions } from "vuex";
import { BTooltip } from 'bootstrap-vue';

export default {
  data() {
    return {
      tooltips: {
        name: "The name of the culture. For example, <i>Escherichia coli</i> or <i>Saccharomyces cerevisiae</i>.",
        description: "A description of the culture. For example, <i>MG1655</i> or <i>BY4741</i>.",
        volume_fixed: "The fixed volume of the culture in milliliters (mL).",
        volume_added: "The total media volume added to the culture at a dilution step in milliliters (mL).",
        od_threshold: "The optical density (OD) threshold for the culture to be diluted.",
        od_threshold_first_dilution: "The optical density (OD) threshold for the culture to be diluted for the first time.",
        stress_dose_first_dilution: "The resulting stress dose after the first dilution.",
        stress_increase_delay_generations: "The number of generations to wait before increasing the stress dose.",
        stress_increase_tdoubling_max_hrs: "The maximum culture doubling time in hours (hrs) for an increase in stress dose to be allowed.",
        stress_decrease_delay_hrs: "How long to wait before decreasing the stress dose if the culture does not reach the <i>od_threshold</i>.",
        stress_decrease_tdoubling_min_hrs: "The minimum culture doubling time in hours (hrs) for a decrease in stress dose to be allowed. If the doubling time is lower than this value, the culture is considered healthy and the stress dose will not be decreased.",
      },
    };
  },
  components: {
    CFormInput,
    BTooltip,
    // CLink,
  },
  props: {
    experiment: {
      type: Object,
      required: true,
    },
    vial: {
      type: Number,
      required: true,
    },
  },
  methods: {
    ...mapActions('experiment', ['updateExperimentParameters']),
    async handleInputChange(key, value) {
      // Update the experiment parameters with the new input value
      await this.updateExperimentParameters({
        experimentId: this.experiment.id,
        parameters: {
          ...this.experiment.parameters,
          cultures: {
            ...this.experiment.parameters.cultures,
            [this.vial]: {
              ...this.experiment.parameters.cultures[this.vial],
              [key]: value,
            },
          },
        },
      });
    },
  },
};
</script>

<style scoped>
@import 'bootstrap/dist/css/bootstrap.css';
@import 'bootstrap-vue/dist/bootstrap-vue.css';

.culture-config {
  width: 150px; /* Adjust the width as desired */
  margin: 0 auto;
  padding-right: 0; /* Remove the right padding */
  padding-left: 0; /* Remove the left padding */
}
</style>