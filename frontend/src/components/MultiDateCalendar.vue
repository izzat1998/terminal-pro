<template>
  <div class="multi-date-picker">
    <a-date-picker
      v-model:value="pickerValue"
      placeholder="Выберите дату для добавления"
      style="width: 100%;"
      format="DD.MM.YYYY"
      @change="handleDateAdd" />

    <div v-if="selectedDates.length > 0" class="selected-dates-tags">
      <a-tag
        v-for="(item, index) in sortedSelectedDates"
        :key="`${item.date}-${item.originalIndex}`"
        closable
        color="blue"
        @close="removeDate(item.originalIndex)">
        {{ formatDisplayDate(item.date, index) }}
      </a-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import dayjs, { type Dayjs } from 'dayjs';

interface Props {
  modelValue?: string[];
}

interface Emits {
  (e: 'update:modelValue', value: string[]): void;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => []
});

const emit = defineEmits<Emits>();

const pickerValue = ref<Dayjs | null>(null);
const selectedDates = ref<string[]>([...props.modelValue]);

// Watch for external changes to modelValue
watch(() => props.modelValue, (newValue) => {
  selectedDates.value = [...newValue];
}, { deep: true });

// Sorted selected dates for display (with original indices preserved)
const sortedSelectedDates = computed(() => {
  return selectedDates.value
    .map((date, originalIndex) => ({ date, originalIndex }))
    .sort((a, b) => a.date.localeCompare(b.date));
});

// Handle date addition
const handleDateAdd = (date: Dayjs | null) => {
  if (!date) return;

  const dateStr = date.format('YYYY-MM-DD');

  // Always add the date, allowing duplicates
  selectedDates.value.push(dateStr);
  emit('update:modelValue', [...selectedDates.value]);

  // Clear picker for next selection
  pickerValue.value = null;
};

// Remove a date from selection by index
const removeDate = (index: number) => {
  selectedDates.value.splice(index, 1);
  emit('update:modelValue', [...selectedDates.value]);
};

// Format date for display in tags with occurrence number for duplicates
const formatDisplayDate = (dateStr: string, currentIndex: number): string => {
  const formattedDate = dayjs(dateStr).format('DD.MM.YYYY');

  // Count occurrences of this date up to current index
  const occurrencesBeforeCurrent = sortedSelectedDates.value
    .slice(0, currentIndex)
    .filter(item => item.date === dateStr).length;

  // Count total occurrences of this date
  const totalOccurrences = sortedSelectedDates.value.filter(item => item.date === dateStr).length;

  // Show occurrence number if date appears multiple times
  if (totalOccurrences > 1) {
    return `${formattedDate} #${occurrencesBeforeCurrent + 1}`;
  }

  return formattedDate;
};
</script>

<style scoped>
.multi-date-picker {
  width: 100%;
}

.selected-dates-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
</style>
