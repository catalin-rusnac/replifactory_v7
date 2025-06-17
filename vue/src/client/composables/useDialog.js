import { ref } from 'vue';

const dialogState = ref({
  show: false,
  title: '',
  message: '',
  showCancel: true,
  resolve: null,
});

export function useDialog() {
  function openDialog({ title, message, showCancel = true }) {
    return new Promise((resolve) => {
      dialogState.value = {
        show: true,
        title,
        message,
        showCancel,
        resolve,
      };
    });
  }
  function handle(result) {
    dialogState.value.show = false;
    dialogState.value.resolve?.(result);
  }
  return { dialogState, openDialog, handle };
} 