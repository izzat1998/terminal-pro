<script setup lang="ts">
import { ref, onMounted } from 'vue';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface Stat {
  value: number;
  suffix: string;
  label: string;
  description: string;
}

const stats: Stat[] = [
  {
    value: 90000,
    suffix: ' м²',
    label: 'Площадь терминала',
    description: 'Общая площадь складских помещений и открытых площадок'
  },
  {
    value: 15000,
    suffix: '',
    label: 'Контейнеров',
    description: 'Максимальная вместимость единовременного хранения'
  },
  {
    value: 100,
    suffix: '+',
    label: 'Компаний',
    description: 'Ежедневно пользуются услугами терминала'
  },
  {
    value: 24,
    suffix: '/7',
    label: 'Режим работы',
    description: 'Круглосуточный контроль и обслуживание'
  }
];

const displayValues = ref<number[]>(stats.map(() => 0));
const sectionRef = ref<HTMLElement | null>(null);

function formatNumber(num: number): string {
  if (num >= 1000) {
    return num.toLocaleString('ru-RU');
  }
  return num.toString();
}

onMounted(() => {
  if (sectionRef.value) {
    ScrollTrigger.create({
      trigger: sectionRef.value,
      start: 'top 75%',
      once: true,
      onEnter: () => {
        stats.forEach((stat, index) => {
          gsap.to(displayValues.value, {
            [index]: stat.value,
            duration: 2,
            ease: 'power2.out',
            onUpdate: () => {
              const val = displayValues.value[index];
              displayValues.value[index] = Math.round(val ?? 0);
            }
          });
        });
      }
    });
  }
});
</script>

<template>
  <section ref="sectionRef" class="stats-section">
    <div class="stats-background">
      <div class="bg-pattern"></div>
    </div>

    <div class="section-container">
      <div class="stats-header">
        <h2 class="stats-title">Цифры говорят сами за себя</h2>
        <p class="stats-subtitle">
          С 2014 года тысячи клиентов доверили нам хранение и оформление грузов
        </p>
      </div>

      <div class="stats-grid">
        <div v-for="(stat, index) in stats" :key="index" class="stat-card">
          <div class="stat-value">
            {{ formatNumber(displayValues[index] ?? 0) }}<span class="stat-suffix">{{ stat.suffix }}</span>
          </div>
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-description">{{ stat.description }}</div>
          <div class="stat-icon">
            <svg v-if="index === 0" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18"/>
              <path d="M9 21V9"/>
            </svg>
            <svg v-else-if="index === 1" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
            </svg>
            <svg v-else-if="index === 2" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 00-3-3.87"/>
              <path d="M16 3.13a4 4 0 010 7.75"/>
            </svg>
            <svg v-else width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.stats-section {
  position: relative;
  padding: 100px 0;
  background: linear-gradient(135deg, #023E8A 0%, #0077B6 50%, #00B4D8 100%);
  overflow: hidden;
}

.stats-background {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.bg-pattern {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 20% 80%, rgba(255, 255, 255, 0.05) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.08) 0%, transparent 50%);
}

.section-container {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.stats-header {
  text-align: center;
  margin-bottom: 60px;
}

.stats-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 36px;
  font-weight: 700;
  color: white;
  margin: 0 0 16px 0;
}

.stats-subtitle {
  font-family: 'DM Sans', sans-serif;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.stat-card {
  position: relative;
  padding: 32px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  text-align: center;
  transition: all 0.3s ease;
  overflow: hidden;
}

.stat-card:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-4px);
}

.stat-value {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 48px;
  font-weight: 800;
  color: white;
  line-height: 1;
  margin-bottom: 8px;
  font-feature-settings: 'tnum';
}

.stat-suffix {
  font-size: 32px;
  font-weight: 600;
}

.stat-label {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  margin-bottom: 8px;
}

.stat-description {
  font-family: 'DM Sans', sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

.stat-icon {
  position: absolute;
  top: 16px;
  right: 16px;
  opacity: 0.15;
}

.stat-icon svg {
  color: white;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .stats-section {
    padding: 80px 0;
  }

  .stats-title {
    font-size: 28px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .stat-card {
    padding: 24px;
  }

  .stat-value {
    font-size: 40px;
  }

  .stat-suffix {
    font-size: 28px;
  }
}
</style>
