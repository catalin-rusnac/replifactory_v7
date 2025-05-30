import { createApp } from 'vue';
import App from './client/App.vue';
import { createPinia } from 'pinia';
import store from './client/store';

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({
  theme: {
        defaultTheme: 'dark'
  },
  components,
  directives,
})

const app = createApp(App);

// app.directive('click-outside', {
//   beforeMount(el, binding) {
//     el.clickOutsideEvent = (event) => {
//       // Check that the click was outside the element and its children
//       if (!(el === event.target || el.contains(event.target)) && !event.target.classList.contains('input')) {
//         binding.value(event); // Call the method provided in the directive
//       }
//     };
//     document.addEventListener('click', el.clickOutsideEvent);
//   },
//   beforeUnmount(el) {
//     document.removeEventListener('click', el.clickOutsideEvent);
//   },
// });

app.use(vuetify)
   .use(createPinia())
   .use(store)
   .mount('#app');
