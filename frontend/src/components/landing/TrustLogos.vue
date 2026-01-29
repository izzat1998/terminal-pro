<script setup lang="ts">
import { ref } from 'vue';

const clients = [
  { name: 'Maersk', color: '#ffb400' },
  { name: 'MSC', color: '#003399' },
  { name: 'CMA CGM', color: '#ff6b35' },
  { name: 'Hapag-Lloyd', color: '#003580' },
  { name: 'ONE', color: '#e31837' },
  { name: 'COSCO', color: '#c41e3a' },
  { name: 'Evergreen', color: '#006633' },
  { name: 'Yang Ming', color: '#003399' },
];

const hoveredClient = ref<number | null>(null);
</script>

<template>
  <div class="trust-logos">
    <p class="section-label">Trusted by leading companies</p>
    <div class="logos-grid">
      <div
        v-for="(client, index) in clients"
        :key="client.name"
        class="logo-item"
        :class="{ 'is-hovered': hoveredClient === index }"
        @mouseenter="hoveredClient = index"
        @mouseleave="hoveredClient = null"
      >
        <div class="logo-placeholder" :style="{ backgroundColor: client.color }">
          <span class="logo-text">{{ client.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trust-logos {
  padding: 40px 0;
}

.section-label {
  text-align: center;
  font-size: 14px;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: 32px;
}

.logos-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.logo-item {
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-placeholder {
  width: 100%;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  filter: grayscale(100%);
  opacity: 0.5;
  transition: all 0.4s ease;
}

.logo-item:hover .logo-placeholder,
.logo-item.is-hovered .logo-placeholder {
  filter: grayscale(0%);
  opacity: 1;
  transform: scale(1.05);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.logo-text {
  color: white;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
}

@media (max-width: 768px) {
  .logos-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .logo-placeholder {
    height: 60px;
  }

  .logo-text {
    font-size: 14px;
  }
}
</style>
