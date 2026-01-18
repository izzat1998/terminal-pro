<script setup lang="ts">
/**
 * PlacementActions - Footer action buttons for placement workflow
 *
 * Displays Cancel and primary action button based on current workflow step.
 */

defineProps<{
  loading: boolean;
  disabled: boolean;
  primaryText: string;
  showBack?: boolean;
}>();

const emit = defineEmits<{
  cancel: [];
  primary: [];
  back: [];
}>();
</script>

<template>
  <div class="placement-actions">
    <div class="actions-left">
      <a-button @click="emit('cancel')">Отмена</a-button>
      <a-button v-if="showBack" type="link" size="small" @click="emit('back')">
        ← Назад
      </a-button>
    </div>
    <a-button
      type="primary"
      :loading="loading"
      :disabled="disabled"
      @click="emit('primary')"
    >
      {{ primaryText }}
    </a-button>
  </div>
</template>

<style scoped>
.placement-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  margin-top: 12px;
}

.actions-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
