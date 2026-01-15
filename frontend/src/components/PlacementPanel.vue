<script setup lang="ts">
/**
 * Placement Panel - Controls for placement workflow
 */

import { ref } from 'vue';
import { usePlacementState } from '../composables/usePlacementState';
import type { Position, ZoneCode, UnplacedContainer } from '../types/placement';

const props = defineProps<{
  selectedContainer?: UnplacedContainer | null;
}>();

const emit = defineEmits<{
  close: [];
  placed: [];
}>();

const {
  currentSuggestion,
  startPlacement,
  confirmPlacement,
  cancelPlacement,
} = usePlacementState();

// Separate loading states for different actions
const loadingSuggest = ref(false);
const loadingConfirm = ref(false);

// Manual position form
const manualPosition = ref<Position>({
  zone: 'A',
  row: 1,
  bay: 1,
  tier: 1,
  sub_slot: 'A',
});

const useManualPosition = ref(false);

// Request suggestion when container selected
async function handleSuggest(): Promise<void> {
  if (!props.selectedContainer || loadingSuggest.value) return;

  loadingSuggest.value = true;
  try {
    await startPlacement(props.selectedContainer.id);
  } finally {
    loadingSuggest.value = false;
  }
}

// Confirm placement
async function handleConfirm(): Promise<void> {
  if (!props.selectedContainer || loadingConfirm.value) return;

  const position = useManualPosition.value
    ? manualPosition.value
    : currentSuggestion.value?.suggested_position;

  if (!position) return;

  loadingConfirm.value = true;
  try {
    await confirmPlacement(props.selectedContainer.id, position);
    emit('placed');
  } finally {
    loadingConfirm.value = false;
  }
}

// Cancel
function handleCancel(): void {
  cancelPlacement();
  emit('close');
}

// Select alternative
function selectAlternative(pos: Position): void {
  manualPosition.value = { ...pos };
  useManualPosition.value = true;
}

// Currently only Zone A for simplified version
const zones: ZoneCode[] = ['A'];
</script>

<template>
  <a-card class="placement-panel" title="Размещение контейнера" size="small">
    <template v-if="selectedContainer">
      <!-- Container info -->
      <a-descriptions :column="1" size="small" bordered class="mb-3">
        <a-descriptions-item label="Номер">
          <strong>{{ selectedContainer.container_number }}</strong>
        </a-descriptions-item>
        <a-descriptions-item label="Тип">
          {{ selectedContainer.iso_type }}
        </a-descriptions-item>
        <a-descriptions-item label="Статус">
          <a-tag :color="selectedContainer.status === 'LADEN' ? 'green' : 'blue'">
            {{ selectedContainer.status === 'LADEN' ? 'Гружёный' : 'Порожний' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="На терминале">
          {{ selectedContainer.dwell_time_days }} дней
        </a-descriptions-item>
      </a-descriptions>

      <!-- Suggest button -->
      <a-button
        type="primary"
        block
        :loading="loadingSuggest"
        @click="handleSuggest"
        class="mb-3"
      >
        Получить рекомендацию
      </a-button>

      <!-- Suggestion result -->
      <template v-if="currentSuggestion">
        <a-alert
          type="info"
          class="mb-3"
          :message="`Рекомендуемая позиция: ${currentSuggestion.suggested_position.coordinate}`"
          :description="currentSuggestion.reason"
        />

        <!-- Alternatives -->
        <div v-if="currentSuggestion.alternatives.length > 0" class="mb-3">
          <div class="text-secondary mb-1">Альтернативы:</div>
          <a-space wrap>
            <a-tag
              v-for="alt in currentSuggestion.alternatives"
              :key="alt.coordinate"
              class="alternative-tag"
              @click="selectAlternative(alt)"
            >
              {{ alt.coordinate }}
            </a-tag>
          </a-space>
        </div>
      </template>

      <!-- Manual position toggle -->
      <a-checkbox v-model:checked="useManualPosition" class="mb-2">
        Указать позицию вручную
      </a-checkbox>

      <!-- Manual position form -->
      <a-form v-if="useManualPosition" layout="inline" class="manual-form mb-3">
        <a-form-item label="Зона">
          <a-select v-model:value="manualPosition.zone" style="width: 70px">
            <a-select-option v-for="z in zones" :key="z" :value="z">{{ z }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="Ряд">
          <a-input-number v-model:value="manualPosition.row" :min="1" :max="10" style="width: 60px" />
        </a-form-item>
        <a-form-item label="Отсек">
          <a-input-number v-model:value="manualPosition.bay" :min="1" :max="10" style="width: 60px" />
        </a-form-item>
        <a-form-item label="Ярус">
          <a-input-number v-model:value="manualPosition.tier" :min="1" :max="4" style="width: 60px" />
        </a-form-item>
      </a-form>

      <!-- Actions -->
      <a-space>
        <a-button @click="handleCancel">Отмена</a-button>
        <a-button
          type="primary"
          :loading="loadingConfirm"
          :disabled="!currentSuggestion && !useManualPosition"
          @click="handleConfirm"
        >
          Разместить
        </a-button>
      </a-space>
    </template>

    <template v-else>
      <a-empty description="Выберите контейнер для размещения" />
    </template>
  </a-card>
</template>

<style scoped>
.placement-panel {
  min-width: 320px;
}

.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }

.text-secondary {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}

.alternative-tag {
  cursor: pointer;
}

.alternative-tag:hover {
  border-color: #1677ff;
  color: #1677ff;
}

.manual-form :deep(.ant-form-item) {
  margin-bottom: 8px;
}
</style>
