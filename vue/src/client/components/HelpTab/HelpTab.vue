<template>
  <div class="documentation">
    <!-- Tabbed navigation -->
    <div>
      <button v-bind:class="{ active: activeTab === 'documentation' }" v-on:click="activeTab = 'documentation'">Documentation</button>
      <button v-bind:class="{ active: activeTab === 'feedback' }" v-on:click="activeTab = 'feedback'">Feedback</button>
    </div>

    <!-- Tabbed content -->
    <div v-if="activeTab === 'documentation'">
      <iframe :src="docUrl" class="documentation-frame"></iframe>
    </div>
    <div v-if="activeTab === 'feedback'" class="form-container">
      <iframe src="https://docs.google.com/forms/d/e/1FAIpQLSdScm5LWwZyZjB7B9atJi6om0ldYv7Apjcb6gDFtDJ2HHrBRw/viewform?embedded=true" class="google-form-frame">Loading…</iframe>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      docUrl: 'sphinx/_build/html/index.html',
      activeTab: 'documentation', // Set the default tab
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

.tabs {
  width: 100%;
  display: flex;
  justify-content: space-evenly;
}

.tabs button {
  flex-grow: 1;
  text-align: center;
}

.tab-content, .form-container {
  width: 100%;
}

.documentation .documentation-frame {
  width: 100vw; /* Adjust this to vw so it takes the viewport's width */
  height: 120vh;
  border: none;
}

/* Style the Google Form iframe */
.documentation .google-form-frame {
  width: 640px;
  height: 540px;
  border: none;
}

/* Center the Google Form iframe */
.form-container {
  display: flex;
  justify-content: center;
  width: 100%; /* Make sure that this container takes the full width */
}

/* Active tab button style */
button.active {
  background-color: #007bff;
  color: white;
}
</style>
