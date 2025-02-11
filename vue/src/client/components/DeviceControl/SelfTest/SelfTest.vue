<template>
  <div>
    <h1>Self Test</h1>
    <!-- Include StirrerTest component -->
    <StirrerTest />
    <!-- Include ODTest component -->
    <ODTest />
  </div>
</template>

<script setup>
import StirrerTest from './StirrerTest.vue';
import ODTest from './ODTest.vue';
</script>

<style scoped>
h1 {
  text-align: center;
  margin-bottom: 20px;
}
</style>
