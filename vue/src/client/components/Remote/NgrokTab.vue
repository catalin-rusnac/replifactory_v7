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

const ngrokaxios = axios.create({
  baseURL: window.location.origin + '/tunnels',
  timeout: 5000,
});
console.log("Created ngrokAxios with baseURL: " + window.location.origin + '/tunnels',);


export default {
  data() {
    return {
      authtoken: '',
      ngrokUrl: '',
    };
  },
  created() {
      ngrokaxios.get('/get-ngrok-url')
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
      ngrokaxios.post('/set-ngrok-authtoken', {
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
