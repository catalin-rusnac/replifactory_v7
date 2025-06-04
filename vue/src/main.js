import { createApp } from 'vue';
import App from './client/App.vue';
import { createPinia } from 'pinia';

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import Vue3Toastify from 'vue3-toastify';

const vuetify = createVuetify({
  theme: {
        defaultTheme: 'dark'
  },
  components,
  directives,
})

const app = createApp(App);

app.use(vuetify)
   .use(createPinia())
   .use(Vue3Toastify, {
    autoClose: 4000,
    theme: 'dark',
    position: 'top-right',
   })
   .mount('#app');
