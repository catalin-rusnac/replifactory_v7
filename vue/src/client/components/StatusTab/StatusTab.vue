<template>
  <div>
    <!-- Button Row -->
    <div class="d-flex justify-content-start mt-3">
      <!-- Camera button -->
      <v-btn color="info" class="mr-3" @click="capture_image">
        <v-icon size="large">mdi-camera</v-icon> photo
      </v-btn>

      <!-- Download button -->
      <v-btn color="success" class="mr-3" @click="download_db">
        <v-icon size="large">mdi-cloud-download</v-icon>
        download database
      </v-btn>

      <!-- Status button -->
      <v-btn color="primary" @click="get_info">
        <v-icon size="large">mdi-information</v-icon>
      </v-btn>
    </div>

    <!-- Export buttons -->
    <div class="d-flex flex-wrap mt-3">
      <!-- Export Label -->
      <div class="d-flex align-items-center mr-3">
        Export Data
      </div>

      <!-- Format Dropdown -->
      <v-select
        v-model="selectedFormat"
        :items="['csv', 'html']"
        label="Please select a format"
        class="mr-3"
      ></v-select>

      <!-- Vial Buttons -->
      <div>
        <v-btn color="info" v-for="i in 7" :key="'vial'+i" class="mr-1" @click="export_data(i, selectedFormat)">
          Vial {{ i }}
        </v-btn>
      </div>
    </div>

    <!-- Image display -->
    <div class="mt-3">
      <img :src="camera_image" class="img-fluid" />
    </div>

    <!-- Display status text field -->
    <div class="mt-3" v-html="status_text"></div>
  </div>
</template>

<script>
import api from "@/api";

export default {
  name: 'StatusTab',
  data() {
    return {
      status_text: '',
      camera_image: null,
      selectedFormat: 'html',
    };
  },
  methods: {
    download_db() {
      api.get('/download_db', { responseType: 'blob' })
        .then((response) => {
          const file = new Blob([response.data], { type: 'application/octet-stream' });
          const a = document.createElement('a');
          a.href = URL.createObjectURL(file);
          a.download = document.title + '_replifactory.db';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        })
        .catch(error => {
          console.error(error);
        });
    },

    get_info() {
      api.get('/status')
        .then(response => {
          this.status_text = response.data.replace(/\n/g, "<br />");
        })
        .catch(error => {
          console.error(error);
        });
    },

    export_data(vial, filetype) {
      api.get(`/export/${vial}/${filetype}`, { responseType: 'blob' })
        .then((response) => {
          const file = new Blob([response.data], { type: 'application/octet-stream' });
          const a = document.createElement('a');
          a.href = URL.createObjectURL(file);
          a.download = `vial_${vial}_data.${filetype}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        })
        .catch(error => {
          console.error(error);
        });
    },

    capture_image() {
      api.get('/capture', { responseType: 'arraybuffer' })
        .then(response => {
          const base64 = btoa(
            new Uint8Array(response.data)
              .reduce((data, byte) => data + String.fromCharCode(byte), '')
          );
          this.camera_image = 'data:image/jpeg;base64,' + base64;
        })
        .catch(error => {
          console.error(error);
        });
    },
  },
};
</script>

<style scoped>
.d-flex {
  display: flex;
}
.justify-content-start {
  justify-content: flex-start;
}
.align-items-center {
  align-items: center;
}
.mt-3 {
  margin-top: 1rem;
}
.mr-3 {
  margin-right: 1rem;
}
.mr-1 {
  margin-right: 0.25rem;
}
.img-fluid {
  max-width: 100%;
  height: auto;
}
</style>
