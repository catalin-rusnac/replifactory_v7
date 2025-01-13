<template>
  <div class="stirrer-controls">
      <StirrerCalibration v-for="index in 7" :key="index" :stirrerId="index" />
  </div>
</template>



<script>
import StirrerCalibration from "@/client/components/DeviceControl/StirrerCalibration.vue";

export default {
  name: 'StirrerControl',
  components: {
    StirrerCalibration,
  },
}
</script>

<style scoped>
.stirrer-controls {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  width: 850px;
  margin: 0 auto;
}

.stirrer-control {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0 auto;
}

.stirrer-label {
  font-size: 1.2rem;
  margin-bottom: 10px;
}

.slider {
  width: 60px;
  height: 100px;
  background: #d3d3d3;
  outline: none;
  opacity: 0.7;
  writing-mode: vertical-lr;
  direction: rtl;
}

.stirrer-spinner {
  width: 1rem;
  height: 1rem;
  margin-bottom: 10px;
  justify-content: center;
  align-items: center;
}

.spinner-border {
  --cui-spinner-animation-name: spinner-border;
  --cui-spinner-animation-speed: 2s;
  vertical-align: middle;
}
</style>
