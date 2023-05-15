<template>
  <div>
    <input type="text" v-model="authtoken" placeholder="ngrok authtoken" />
    <button @click="sendAuthtoken">Connect</button>
    <a style="margin-left: 30px" href="https://dashboard.ngrok.com/get-started/your-authtoken" target="_blank">Get ngrok authtoken</a>
    <br>
    <br>
    <p>Ngrok URL: <a :href="ngrokUrl" target="_blank">{{ ngrokUrl }}</a></p>

  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      authtoken: '',
      ngrokUrl: '',
    };
  },
  created() {
      axios.get('/api/get-ngrok-url')
        .then(response => {
          console.log(response);
          this.ngrokUrl = response.data.ngrokUrl;
        })
        .catch(error => {
          console.log(error);
        });
    },

  methods: {
    sendAuthtoken() {
      axios
        .post('/api/setNgrokauthtoken', {
          authtoken: this.authtoken,
        })
        .then(response => {
          console.log(response);
          this.ngrokUrl = response.data.ngrokUrl;
        })
        .catch(error => {
          console.log(error);
        });
    },
  },
};
</script>
