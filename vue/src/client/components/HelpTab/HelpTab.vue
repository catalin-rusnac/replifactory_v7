<template>
  <div class="documentation">
    <!-- Tabbed content -->
    <div>
      <iframe :src="docUrl" class="documentation-frame"></iframe>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      docUrl: 'https://docs.replifactory.com',
    };
  },
}
</script>

<style scoped>
.documentation {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;  /* Make sure that this container takes the full width */
}


.tabs button {
  flex-grow: 1;
  text-align: center;
}

.documentation .documentation-frame {
  width: 100vw; /* Adjust this to vw so it takes the viewport's width */
  height: 120vh;
  border: none;
}

</style>
