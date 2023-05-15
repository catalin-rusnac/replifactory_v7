export default {
  state: {
    input: '',
    keyPress: '',
  },
  mutations: {
    SET_INPUT(state, input) {
      state.input = input;
    },
    SET_KEY_PRESS(state, key) {
      state.keyPress = key;
    },
  },
  actions: {
    changeInput({ commit }, input) {
      commit('SET_INPUT', input);
    },
    keyPress({ commit }, key) {
      commit('SET_KEY_PRESS', key);
    },
  },
  getters: {
    getInput: state => state.input,
    getKeyPress: state => state.keyPress,
  },
};
