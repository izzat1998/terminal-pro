<script setup lang="ts">
/**
 * PlacementSteps - Step progress indicator for placement workflow
 *
 * Steps:
 * 1. Выбор контейнера (Container selection)
 * 2. Позиция (Position selection)
 * 3. Задача (Task creation)
 */

defineProps<{
  currentStep: number;
}>();
</script>

<template>
  <a-steps :current="currentStep" size="small" class="placement-steps">
    <a-step title="Выбор" description="Контейнер" />
    <a-step title="Позиция" description="Рекомендация" />
    <a-step title="Задача" description="Создание" />
  </a-steps>
</template>

<style scoped>
.placement-steps {
  margin-bottom: 16px;
}

.placement-steps :deep(.ant-steps-item-title) {
  font-size: 13px;
}

.placement-steps :deep(.ant-steps-item-description) {
  font-size: 11px;
}
</style>
