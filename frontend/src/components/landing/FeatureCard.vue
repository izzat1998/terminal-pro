<script setup lang="ts">
import { ref } from 'vue';

interface Feature {
  icon: string;
  title: string;
  description: string;
}

interface Props {
  feature: Feature;
  index: number;
}

defineProps<Props>();

const isHovered = ref(false);
</script>

<template>
  <div
    class="feature-card"
    :class="{ 'is-hovered': isHovered }"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <div class="feature-icon">
      <span v-html="feature.icon" />
    </div>
    <div class="feature-content">
      <h3 class="feature-title">{{ feature.title }}</h3>
      <p class="feature-description">{{ feature.description }}</p>
    </div>
    <div class="feature-decoration">
      <div class="decoration-circle" />
    </div>
  </div>
</template>

<style scoped>
.feature-card {
  position: relative;
  padding: 32px;
  background: white;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: default;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border-color: transparent;
}

.feature-card.is-hovered {
  border-color: #e94560;
}

.feature-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fef2f2 0%, #fff5f5 100%);
  border-radius: 14px;
  margin-bottom: 20px;
  transition: all 0.3s ease;
}

.feature-card:hover .feature-icon {
  background: linear-gradient(135deg, #e94560 0%, #ff6b6b 100%);
}

.feature-icon :deep(svg) {
  width: 28px;
  height: 28px;
  color: #e94560;
  transition: all 0.3s ease;
}

.feature-card:hover .feature-icon :deep(svg) {
  color: white;
}

.feature-content {
  position: relative;
  z-index: 1;
}

.feature-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 12px 0;
  transition: color 0.3s ease;
}

.feature-card:hover .feature-title {
  color: #e94560;
}

.feature-description {
  font-size: 15px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0;
  transition: color 0.3s ease;
}

.feature-decoration {
  position: absolute;
  top: -30px;
  right: -30px;
  width: 100px;
  height: 100px;
  pointer-events: none;
}

.decoration-circle {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(233, 69, 96, 0.1) 0%, rgba(233, 69, 96, 0.05) 100%);
  border-radius: 50%;
  transition: all 0.5s ease;
}

.feature-card:hover .decoration-circle {
  transform: scale(1.5);
  background: linear-gradient(135deg, rgba(233, 69, 96, 0.15) 0%, rgba(233, 69, 96, 0.08) 100%);
}
</style>
