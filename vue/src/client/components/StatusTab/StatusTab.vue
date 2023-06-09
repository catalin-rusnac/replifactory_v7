<template>
  <div>
    <!--    download button-->
    <button @click="download_db">Download DB</button>
    <!--status button-->
    <button @click="get_info">Info</button>
    <!--    display status text field-->
    <div v-html="status_text"></div>
  </div>
</template>


<script>
//@experiment_routes.route('/download_db', methods=['GET'])
// def download_file():
//     script_dir = os.path.dirname(__file__)
//     rel_path = "../../db/replifactory.db"
//     abs_file_path = os.path.join(script_dir, rel_path)
//     return send_file(abs_file_path, as_attachment=True)
//

// method for downloading the database when the button is clicked

import api from "@/api";

export default {

  name: 'StatusTab',
  data () {
    return {
      status_text: '',
      msg: 'StatusTab'
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
        a.download = 'database.db'; // the file name you want
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
    //  display text on screen, do not download
    api.get('/get_info')
    .then(response => {
          this.status_text = response.data.replace(/\n/g, "<br />");
        })
        .catch(error => {
          console.error(error);
          // handle the error
        });

  }

}


}


</script>

<style scoped>

</style>