<template>
  <div>
    <!-- Log Tail Selection -->
    <div class="d-flex align-items-center mt-3">
      <CButton
        color="info"
        class="btn mt-3"
        style="width: 20%;"
        @click="fetchLogTails"
      >
        Get Logs
      </CButton>
      <CFormFloating class="mt-3 ml-3" style="width: 20%;">
        <CFormInput
          type="number"
          style="background-color: transparent; border: none;"
          id="floatingInput"
          v-model="lines"
          min="1"
          floatingLabel="Number of Lines"
        />
      </CFormFloating>
    </div>

    <!-- Display Log Tails -->
    <div v-for="(content, fileName) in logs" :key="fileName" class="mt-3">
      <h3>{{ fileName }}</h3>
      <pre>{{ content }}</pre>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { CButton, CFormInput, CFormFloating } from "@coreui/vue";

export default {
  components: {
    CButton,
    CFormInput,
    CFormFloating,
  },
  data() {
    return {
      lines: 100,
      logs: {},
    };
  },
  methods: {
    fetchLogTails() {
      axios.get(`/log/${this.lines}/`)
        .then((response) => {
          this.logs = response.data;
        });
    },
  },
  mounted() {
    this.fetchLogTails();
  },
};
</script>
