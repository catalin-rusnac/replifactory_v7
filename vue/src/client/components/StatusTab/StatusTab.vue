<template>
  <div>
    <!-- Button Row -->
    <div class="d-flex justify-content-start mt-3">
      <!-- Camera button -->
      <CButton color="info" class="mr-3" @click="capture_image">
          <CIcon :icon="cilCamera" size="xl"/> photo
      </CButton>

<!--       Download button -->
      <CButton color="success" class="mr-3" @click="download_db">
<CIcon :icon="cilCloudDownload" size="xl"/>
      download database
      </CButton>

      <!-- Status button -->
      <CButton color="primary" @click="get_info">
        <CIcon :icon="cilInfo" size="xl"/>
      </CButton>
    </div>

        <!-- Export buttons -->
    <div class="d-flex flex-wrap mt-3">
      <!-- Export Label -->
      <div class="d-flex align-items-center mr-3">
<!--        <CIcon name="cil-file"></CIcon> -->
        Export Data
      </div>

      <!-- Format Dropdown -->
      <CFormSelect :model-value="selectedFormat" @update:model-value="v => selectedFormat = v" class="mr-3">
        <option disabled value="">Please select a format</option>
        <option>csv</option>
        <option>html</option>
      </CFormSelect>


      <!-- Vial Buttons -->
      <div>
        <CButton color="info" v-for="i in 7" :key="'vial'+i" class="mr-1" @click="export_data(i, selectedFormat)">
          Vial {{ i }}
        </CButton>
      </div>
    </div>


    <!-- Image display -->
    <div class="mt-3">
      <img :src="camera_image" class="img-fluid">
    </div>

    <!-- Display status text field -->
    <div class="mt-3" v-html="status_text"></div>
  </div>
</template>




<script>
import api from "@/api";
import { CButton, CFormSelect } from "@coreui/vue";
import { CIcon } from "@coreui/icons-vue";
import { cilCamera, cilCloudDownload, cilGraph, cilInfo } from '@coreui/icons';



export default {
  components: {
    CButton,
    CIcon,
    CFormSelect,
  },
  name: 'StatusTab',
  data () {
    return {
      status_text: '',
      msg: 'StatusTab',
      camera_image: null,
      selectedFormat: 'html',
      cilCamera,
      cilCloudDownload,
      cilGraph,
      cilInfo,
    }
  },

  methods: {
    download_db: function() {
      api.get('/download_db', { responseType: 'blob' }) // set responseType to 'blob' to tell Axios to download the file
        .then((response) => {
          // Create a blob from the response
          const file = new Blob([response.data], { type: 'application/octet-stream' });
          // Create a link element
          const a = document.createElement('a');
          // URL.createObjectURL creates a URL representing the file
          a.href = URL.createObjectURL(file);
          a.download = document.title + '_replifactory.db';
          // Add the link to the document
          document.body.appendChild(a);
          // Simulate click on the link
          a.click();
          // Clean up: remove the link from the document
          document.body.removeChild(a);
        })
        .catch(error => {
          console.error(error);
          // handle the error
        });
    },

    get_info: function () {
      // display text on screen, do not download
      api.get('/status')
      .then(response => {
            this.status_text = response.data.replace(/\n/g, "<br />");
          })
          .catch(error => {
            console.error(error);
            // handle the error
          });
    },

    export_data: function(vial, filetype) {
  api.get(`/export/${vial}/${filetype}`, { responseType: 'blob' })
    .then((response) => {
      // Create a blob from the response
      const file = new Blob([response.data], { type: 'application/octet-stream' });
      // Create a link element
      const a = document.createElement('a');
      // URL.createObjectURL creates a URL representing the file
      a.href = URL.createObjectURL(file);
      a.download = `vial_${vial}_data.${filetype}`;
      // Add the link to the document
      document.body.appendChild(a);
      // Simulate click on the link
      a.click();
      // Clean up: remove the link from the document
      document.body.removeChild(a);
    })
    .catch(error => {
      console.error(error);
      // handle the error
    });
},


    capture_image: function() {
      api.get('/capture', { responseType: 'arraybuffer' })
        .then(response => {
          // Convert the array buffer to a base64-encoded string
          const base64 = btoa(
            new Uint8Array(response.data)
              .reduce((data, byte) => data + String.fromCharCode(byte), '')
          );

          // Set the image data for the img element
          this.camera_image = 'data:image/jpeg;base64,' + base64;
        })
        .catch(error => {
          console.error(error);
          // handle the error
        });
    },

  }
}
</script>

<style scoped>

</style>
