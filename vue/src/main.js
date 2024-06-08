import { createApp } from 'vue';
import App from './client/App.vue';
import store from './client/store';

import { BootstrapVue, IconsPlugin } from 'bootstrap-vue';

import 'bootstrap/dist/css/bootstrap.css';
import '@coreui/coreui/dist/css/coreui.css';

const app = createApp(App);

app.directive('click-outside', {
  beforeMount(el, binding) {
    el.clickOutsideEvent = event => {
      // check that click was outside the el and his children, and not an element with class "input"
      if (!(el === event.target || el.contains(event.target)) && !event.target.classList.contains('input')) {
        // if it did, call method provided in attribute value
        binding.value();
      }
    };
    document.addEventListener('click', el.clickOutsideEvent);
  },
  beforeUnmount(el) {
    document.removeEventListener('click', el.clickOutsideEvent);
  },
});


app.use(BootstrapVue)
  .use(IconsPlugin)
  .use(store) // This line adds your Vuex store to your Vue app
  .mount('#app');