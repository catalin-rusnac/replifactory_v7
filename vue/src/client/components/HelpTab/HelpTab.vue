<template>
  <div class="documentation">
    <iframe :src="docUrl" class="documentation-frame"></iframe>
  </div>
</template>

<script>
export default {
  data() {
    return {
      docUrl: 'sphinx/_build/html/index.html'
    };
  },
}
</script>

<style scoped>
.documentation .documentation-frame {
  width: 100%;
  height: 120vh;  /* You can set the height to your liking */
  border: none;   /* Removes the border */
}
</style>
