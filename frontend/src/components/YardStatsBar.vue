<script setup lang="ts">
/**
 * YardStatsBar - Toggleable horizontal stats bar for 3D yard view
 *
 * Displays terminal statistics above the 3D canvas:
 * - На терминале (occupied)
 * - Свободно (available)
 * - Груженых (laden)
 * - Порожних (empty)
 *
 * Company-aware: When a company is selected, shows only that company's numbers.
 * Height: 56px with glass morphism effect for modern look.
 */

import {
  ContainerOutlined,
  CheckCircleOutlined,
  InboxOutlined,
  CodeSandboxOutlined,
} from '@ant-design/icons-vue';

interface Props {
  occupied: number;
  available: number;
  ladenCount: number;
  emptyCount: number;
  selectedCompany: string | null;
}

defineProps<Props>();
</script>

<template>
  <Transition name="slide-down">
    <div class="yard-stats-bar">
      <div class="stats-content">
        <!-- Company badge (when filtered) -->
        <a-tag v-if="selectedCompany" color="blue" class="company-badge">
          {{ selectedCompany }}
        </a-tag>

        <div class="stats-group">
          <div class="stat-item">
            <ContainerOutlined class="stat-icon occupied" />
            <div class="stat-info">
              <span class="stat-value">{{ occupied }}</span>
              <span class="stat-label">На терминале</span>
            </div>
          </div>

          <div class="stat-divider" />

          <div class="stat-item">
            <CheckCircleOutlined class="stat-icon available" />
            <div class="stat-info">
              <span class="stat-value available">{{ available }}</span>
              <span class="stat-label">Свободно</span>
            </div>
          </div>

          <div class="stat-divider" />

          <div class="stat-item">
            <InboxOutlined class="stat-icon laden" />
            <div class="stat-info">
              <span class="stat-value laden">{{ ladenCount }}</span>
              <span class="stat-label">Груженых</span>
            </div>
          </div>

          <div class="stat-divider" />

          <div class="stat-item">
            <CodeSandboxOutlined class="stat-icon empty" />
            <div class="stat-info">
              <span class="stat-value empty">{{ emptyCount }}</span>
              <span class="stat-label">Порожних</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.yard-stats-bar {
  height: 56px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  z-index: 10;
}

.stats-content {
  height: 100%;
  max-width: 900px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.company-badge {
  font-weight: 500;
  padding: 4px 12px;
  font-size: 13px;
}

.stats-group {
  display: flex;
  align-items: center;
  gap: 24px;
  flex: 1;
  justify-content: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-icon {
  font-size: 18px;
  color: #8c8c8c;
}

.stat-icon.occupied {
  color: #1677ff;
}

.stat-icon.available {
  color: #52c41a;
}

.stat-icon.laden {
  color: #52c41a;
}

.stat-icon.empty {
  color: #1890ff;
}

.stat-info {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

.stat-value.available {
  color: #52c41a;
}

.stat-value.laden {
  color: #389e0d;
}

.stat-value.empty {
  color: #1890ff;
}

.stat-label {
  font-size: 11px;
  color: #8c8c8c;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.stat-divider {
  width: 1px;
  height: 28px;
  background: rgba(0, 0, 0, 0.08);
}

/* Slide transition */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
  transform-origin: top;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .yard-stats-bar {
    background: rgba(30, 30, 30, 0.85);
    border-bottom-color: rgba(255, 255, 255, 0.08);
  }

  .stat-value {
    color: #f0f0f0;
  }

  .stat-label {
    color: #8c8c8c;
  }

  .stat-divider {
    background: rgba(255, 255, 255, 0.12);
  }
}
</style>
