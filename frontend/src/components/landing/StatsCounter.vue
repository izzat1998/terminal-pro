<script setup lang="ts">
import { ref, onMounted } from 'vue';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface Props {
  target: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
}

const props = withDefaults(defineProps<Props>(), {
  duration: 2,
  suffix: '',
  prefix: '',
});

const displayValue = ref(0);
const containerRef = ref<HTMLElement | undefined>(undefined);

function formatNumber(num: number): string {
  return num.toLocaleString('en-US');
}

onMounted(() => {
  if (!containerRef.value) return;

  ScrollTrigger.create({
    trigger: containerRef.value,
    start: 'top 80%',
    once: true,
    onEnter: () => {
      gsap.to(displayValue, {
        value: props.target,
        duration: props.duration,
        ease: 'power2.out',
        onUpdate: () => {
          displayValue.value = Math.round(gsap.getProperty(displayValue, 'value') as number);
        },
      });
    },
  });
});
</script>

<template>
  <div ref="containerRef" class="stats-counter">
    <div class="counter-value">
      {{ prefix }}{{ formatNumber(displayValue) }}{{ suffix }}
    </div>
    <div class="counter-label">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.stats-counter {
  text-align: center;
  padding: 20px;
}

.counter-value {
  font-size: 56px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1;
  margin-bottom: 12px;
  font-feature-settings: 'tnum';
  font-variant-numeric: tabular-nums;
}

.counter-label {
  font-size: 16px;
  color: #6b7280;
  font-weight: 500;
}

@media (max-width: 768px) {
  .counter-value {
    font-size: 40px;
  }

  .counter-label {
    font-size: 14px;
  }
}
</style>
