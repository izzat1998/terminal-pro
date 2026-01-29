<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

interface Testimonial {
  id: number;
  quote: string;
  author: string;
  role: string;
  company: string;
}

const testimonials: Testimonial[] = [
  {
    id: 1,
    quote: 'MTT transformed our terminal operations. Real-time visibility and automated matching reduced our dwell time by 35%.',
    author: 'Алексей Петров',
    role: 'Operations Director',
    company: 'TransContainer Uzbekistan',
  },
  {
    id: 2,
    quote: 'The Telegram bot integration is a game-changer. Our drivers can now report movements instantly from anywhere on the terminal.',
    author: 'Михаил Иванов',
    role: 'Fleet Manager',
    company: 'Asia Transit Group',
  },
  {
    id: 3,
    quote: 'The 3D yard visualization gives us unprecedented control over container placement. Planning has never been more efficient.',
    author: 'Дмитрий Соколов',
    role: 'Terminal Superintendent',
    company: 'Global Ports Tashkent',
  },
  {
    id: 4,
    quote: 'Customer portal provides complete transparency. Our clients love being able to track containers in real-time.',
    author: 'Наталья Кузьмина',
    role: 'Customer Success Manager',
    company: 'Uzbekistan Logistics',
  },
];

const currentIndex = ref(0);
const slideDirection = ref<'left' | 'right'>('right');
let autoplayInterval: ReturnType<typeof setInterval> | null = null;

function nextSlide(): void {
  slideDirection.value = 'right';
  currentIndex.value = (currentIndex.value + 1) % testimonials.length;
}

function prevSlide(): void {
  slideDirection.value = 'left';
  currentIndex.value = currentIndex.value === 0
    ? testimonials.length - 1
    : currentIndex.value - 1;
}

function goToSlide(index: number): void {
  slideDirection.value = index > currentIndex.value ? 'right' : 'left';
  currentIndex.value = index;
}

function startAutoplay(): void {
  autoplayInterval = setInterval(() => {
    nextSlide();
  }, 5000);
}

function stopAutoplay(): void {
  if (autoplayInterval) {
    clearInterval(autoplayInterval);
    autoplayInterval = null;
  }
}

onMounted(() => {
  startAutoplay();
});

onUnmounted(() => {
  stopAutoplay();
});
</script>

<template>
  <div class="testimonials" @mouseenter="stopAutoplay" @mouseleave="startAutoplay">
    <div class="testimonial-container">
      <transition :name="slideDirection === 'right' ? 'slide-right' : 'slide-left'" mode="out-in">
        <div :key="currentIndex" class="testimonial-slide">
          <div class="quote-icon">"</div>
          <blockquote class="testimonial-quote">
            {{ testimonials[currentIndex]?.quote }}
          </blockquote>
          <div class="testimonial-author">
            <div class="author-avatar">
              {{ testimonials[currentIndex]?.author.charAt(0) }}
            </div>
            <div class="author-info">
              <div class="author-name">{{ testimonials[currentIndex]?.author }}</div>
              <div class="author-role">
                {{ testimonials[currentIndex]?.role }} · {{ testimonials[currentIndex]?.company }}
              </div>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <div class="testimonial-nav">
      <button class="nav-btn prev" @click="prevSlide" aria-label="Previous testimonial">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>
      <div class="dots">
        <button
          v-for="(_, index) in testimonials"
          :key="index"
          class="dot"
          :class="{ active: index === currentIndex }"
          @click="goToSlide(index)"
          :aria-label="`Go to testimonial ${index + 1}`"
        />
      </div>
      <button class="nav-btn next" @click="nextSlide" aria-label="Next testimonial">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 18l6-6-6-6" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.testimonials {
  max-width: 800px;
  margin: 0 auto;
}

.testimonial-container {
  position: relative;
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.testimonial-slide {
  text-align: center;
  padding: 0 20px;
}

.quote-icon {
  font-size: 80px;
  line-height: 1;
  color: #e94560;
  opacity: 0.3;
  font-family: Georgia, serif;
  margin-bottom: 16px;
}

.testimonial-quote {
  font-size: 22px;
  line-height: 1.6;
  color: #1f2937;
  margin: 0 0 32px 0;
  font-style: italic;
}

.testimonial-author {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.author-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e94560 0%, #ff6b6b 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
}

.author-info {
  text-align: left;
}

.author-name {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.author-role {
  font-size: 14px;
  color: #6b7280;
}

.testimonial-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
}

.nav-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid #e5e7eb;
  background: white;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.nav-btn:hover {
  border-color: #e94560;
  color: #e94560;
}

.dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: none;
  background: #e5e7eb;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dot:hover {
  background: #d1d5db;
}

.dot.active {
  background: #e94560;
  width: 28px;
  border-radius: 5px;
}

/* Transitions */
.slide-right-enter-active,
.slide-right-leave-active,
.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-right-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.slide-right-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.slide-left-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.slide-left-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

@media (max-width: 768px) {
  .testimonial-quote {
    font-size: 18px;
  }

  .testimonial-container {
    min-height: 350px;
  }
}
</style>
