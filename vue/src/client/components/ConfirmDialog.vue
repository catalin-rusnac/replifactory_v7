<template>
  <v-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    max-width="400"
  >
    <v-card>
      <v-card-title class="headline">{{ title }}</v-card-title>
      <v-card-text>{{ message }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="success" text @click="handleConfirm">Confirm</v-btn>
        <v-btn color="grey" text @click="handleCancel">Cancel</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { useDialog } from '@/client/composables/useDialog'
const { handle } = useDialog()

const props = defineProps({
  modelValue: Boolean,
  title: { type: String, default: 'Are you sure?' },
  message: { type: String, default: 'Do you want to proceed?' },
  showCancel: { type: Boolean, default: true }
});

function handleConfirm() {
  handle(true)
}
function handleCancel() {
  handle(false)
}
</script>

<style scoped>
/* Custom overlay color for the dialog */
.v-overlay__scrim {
  background-color: rgba(0, 0, 0, 0.6) !important;
}

.v-card {
  border-radius: 12px;
}

.v-card-title.headline {
  font-weight: bold;
  font-size: 1.2rem;
}

.v-btn {
  min-width: 80px;
}
</style>
