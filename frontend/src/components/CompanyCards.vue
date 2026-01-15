<script setup lang="ts">
/**
 * Company Cards - Horizontal scrollable row of company statistics
 * Click a card to filter containers by company in 3D view and tables
 * Uses Ant Design Vue components for consistency
 */

import { BankOutlined, AppstoreOutlined } from '@ant-design/icons-vue';
import type { CompanyStats } from '../types/placement';

interface Props {
  companies: CompanyStats[];
  selectedCompany: string | null;
  totalCount: number;
}

defineProps<Props>();

const emit = defineEmits<{
  select: [companyName: string | null];
}>();

function handleCardClick(companyName: string | null): void {
  emit('select', companyName);
}
</script>

<template>
  <div class="company-cards-wrapper">
    <div class="company-cards-scroll">
      <!-- "All" card - always first -->
      <a-card
        hoverable
        size="small"
        class="company-card all-card"
        :class="{ selected: !selectedCompany }"
        :body-style="{ padding: '16px 20px', textAlign: 'center' }"
        @click="handleCardClick(null)"
      >
        <a-statistic
          title="Все"
          :value="totalCount"
          :value-style="{ fontSize: '28px', fontWeight: 700, color: !selectedCompany ? '#52c41a' : '#262626' }"
        >
          <template #prefix>
            <AppstoreOutlined style="font-size: 16px; margin-right: 4px;" />
          </template>
        </a-statistic>
      </a-card>

      <!-- Company cards -->
      <a-card
        v-for="company in companies"
        :key="company.name"
        hoverable
        size="small"
        class="company-card"
        :class="{ selected: selectedCompany === company.name }"
        :body-style="{ padding: '16px 20px', textAlign: 'center' }"
        @click="handleCardClick(selectedCompany === company.name ? null : company.name)"
      >
        <a-statistic
          :value="company.containerCount"
          :value-style="{ fontSize: '28px', fontWeight: 700, color: selectedCompany === company.name ? '#1677ff' : '#262626' }"
        >
          <template #title>
            <a-tooltip :title="company.name" placement="top">
              <div class="card-title">
                <BankOutlined style="margin-right: 4px;" />
                {{ company.name.length > 18 ? company.name.slice(0, 18) + '…' : company.name }}
              </div>
            </a-tooltip>
          </template>
        </a-statistic>
        <div class="card-breakdown">
          <a-tag color="green" :bordered="false">{{ company.ladenCount }} гр.</a-tag>
          <a-tag color="blue" :bordered="false">{{ company.emptyCount }} пор.</a-tag>
        </div>
      </a-card>
    </div>
  </div>
</template>

<style scoped>
.company-cards-wrapper {
  margin-bottom: 16px;
}

.company-cards-scroll {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding: 4px 0 8px 0;
  scrollbar-width: thin;
  scrollbar-color: var(--ant-color-border) transparent;
}

.company-cards-scroll::-webkit-scrollbar {
  height: 8px;
}

.company-cards-scroll::-webkit-scrollbar-track {
  background: var(--ant-color-bg-container);
  border-radius: 4px;
}

.company-cards-scroll::-webkit-scrollbar-thumb {
  background: var(--ant-color-border);
  border-radius: 4px;
}

.company-cards-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--ant-color-text-quaternary);
}

.company-card {
  flex-shrink: 0;
  min-width: 180px;
  border: 2px solid transparent;
  transition: all 0.2s ease;
}

.company-card.selected {
  border-color: var(--ant-color-primary);
  background: var(--ant-color-primary-bg);
}

.company-card.all-card.selected {
  border-color: var(--ant-color-success);
  background: var(--ant-color-success-bg);
}

.card-title {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
  display: inline-flex;
  align-items: center;
}

.card-breakdown {
  margin-top: 8px;
  display: flex;
  justify-content: center;
  gap: 4px;
}

/* Override ant-card hover shadow for selected state */
.company-card.selected:hover {
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.15);
}

.company-card.all-card.selected:hover {
  box-shadow: 0 4px 12px rgba(82, 196, 26, 0.15);
}

/* Ant Design statistic title override */
.company-card :deep(.ant-statistic-title) {
  margin-bottom: 4px;
  color: var(--ant-color-text-secondary);
}
</style>
