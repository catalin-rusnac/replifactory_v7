<template>
  <div>
    <!-- Log Tail Selection -->
    <div class="d-flex align-items-center mt-3">
      <v-btn
        color="info"
        class="btn mt-3"
        style="width: 20%;"
        @click="fetchLogTails"
      >
        Get Logs
      </v-btn>
      <v-text-field
        v-model="lines"
        class="mt-3 ml-3"
        style="width: 20%; background-color: transparent; border: none;"
        label="Number of Lines"
        type="number"
        outlined
      ></v-text-field>
    </div>

    <!-- Display Log Tails -->
    <div v-for="(content, fileName) in logs" :key="fileName" class="mt-3">
      <h3>{{ fileName }}</h3>
      <pre>{{ content }}</pre>
    </div>
  </div>
</template>

<script>
import api from "@/api";

export default {
  data() {
    return {
      lines: 100,
      logs: {},
    };
  },
  methods: {
    formatNumber(number) {
      return number !== null ? number.toFixed(0) : "N/A";
    },
    fetchLogTails() {
      api.get(`/log/${this.lines}/`)
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

<style scoped>
.d-flex {
  display: flex;
}

.align-items-center {
  align-items: center;
}

.mt-3 {
  margin-top: 1rem;
}

.ml-3 {
  margin-left: 1rem;
}

pre {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
}
</style>
