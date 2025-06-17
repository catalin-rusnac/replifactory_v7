import { ref } from 'vue';

const guideState = ref({
  show: false,
  title: '',
  content: '',
  resolve: null,
});

export function useGuideDialog() {
  function openGuide({ title, content }) {
    return new Promise((resolve) => {
      guideState.value = {
        show: true,
        title,
        content,
        resolve,
      };
    });
  }
  function closeGuide(result) {
    guideState.value.show = false;
    guideState.value.resolve?.(result);
  }
  return { guideState, openGuide, closeGuide };
} 