import Vue from 'vue';
import Vuex from 'vuex';
import device from './deviceStore.js';

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    device,
  }});

