<script setup lang="ts">
/**
 * ManualPositionForm - Zone/Row/Bay/Tier inline form for manual position override
 *
 * Collapsible form that allows manual position input when auto-suggestion
 * is not desired or needs to be overridden.
 */

import { ref, watch } from 'vue';
import type { Position, ZoneCode, SubSlot } from '../../types/placement';

const props = defineProps<{
  enabled: boolean;
  position: Position;
}>();

const emit = defineEmits<{
  'update:enabled': [value: boolean];
  'update:position': [position: Position];
}>();

// Local position state
const localPosition = ref<Position>({ ...props.position });

// Sync local state with prop changes
watch(() => props.position, (newPos) => {
  localPosition.value = { ...newPos };
}, { deep: true });

// Update position and emit
function updateField<K extends keyof Position>(field: K, value: Position[K]): void {
  localPosition.value[field] = value;
  emit('update:position', { ...localPosition.value });
}

// Toggle enabled state
function toggleEnabled(): void {
  emit('update:enabled', !props.enabled);
}

// Currently only Zone A
const zones: ZoneCode[] = ['A'];
const subSlots: SubSlot[] = ['A', 'B'];
</script>

<template>
  <a-collapse
    :activeKey="enabled ? ['manual'] : []"
    ghost
    class="manual-position-collapse"
  >
    <template #expandIcon>
      <span></span>
    </template>
    <a-collapse-panel key="manual" :showArrow="false">
      <template #header>
        <div class="collapse-header" @click.stop="toggleEnabled">
          <a-checkbox :checked="enabled" @click.stop>
            Указать позицию вручную
          </a-checkbox>
        </div>
      </template>

      <div class="manual-form">
        <div class="form-row">
          <div class="form-field">
            <label>Зона</label>
            <a-select
              :value="localPosition.zone"
              style="width: 70px"
              @change="(v: ZoneCode) => updateField('zone', v)"
            >
              <a-select-option v-for="z in zones" :key="z" :value="z">
                {{ z }}
              </a-select-option>
            </a-select>
          </div>

          <div class="form-field">
            <label>Ряд</label>
            <a-input-number
              :value="localPosition.row"
              :min="1"
              :max="10"
              style="width: 65px"
              @change="(v: number | null) => v !== null && updateField('row', v)"
            />
          </div>

          <div class="form-field">
            <label>Отсек</label>
            <a-input-number
              :value="localPosition.bay"
              :min="1"
              :max="10"
              style="width: 65px"
              @change="(v: number | null) => v !== null && updateField('bay', v)"
            />
          </div>

          <div class="form-field">
            <label>Ярус</label>
            <a-input-number
              :value="localPosition.tier"
              :min="1"
              :max="4"
              style="width: 60px"
              @change="(v: number | null) => v !== null && updateField('tier', v)"
            />
          </div>

          <div class="form-field">
            <label>Слот</label>
            <a-select
              :value="localPosition.sub_slot"
              style="width: 60px"
              @change="(v: SubSlot) => updateField('sub_slot', v)"
            >
              <a-select-option v-for="s in subSlots" :key="s" :value="s">
                {{ s }}
              </a-select-option>
            </a-select>
          </div>
        </div>

        <div class="position-preview">
          Позиция: <code>{{ localPosition.zone }}-R{{ localPosition.row.toString().padStart(2, '0') }}-B{{ localPosition.bay.toString().padStart(2, '0') }}-T{{ localPosition.tier }}-{{ localPosition.sub_slot }}</code>
        </div>
      </div>
    </a-collapse-panel>
  </a-collapse>
</template>

<style scoped>
.manual-position-collapse {
  margin-bottom: 12px;
}

.manual-position-collapse :deep(.ant-collapse-header) {
  padding: 8px 0 !important;
}

.manual-position-collapse :deep(.ant-collapse-content-box) {
  padding: 0 0 8px 0 !important;
}

.collapse-header {
  display: flex;
  align-items: center;
}

.manual-form {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 12px;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-field label {
  font-size: 11px;
  color: #8c8c8c;
  text-transform: uppercase;
}

.position-preview {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
  color: #595959;
}

.position-preview code {
  background: #e6f4ff;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  color: #1677ff;
}
</style>
