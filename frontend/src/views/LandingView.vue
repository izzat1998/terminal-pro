<script setup lang="ts">
import { onMounted, ref } from 'vue';
import HeaderNav from '@/components/landing/HeaderNav.vue';
import Hero3DView from '@/components/landing/Hero3DView.vue';
import ServicesSection from '@/components/landing/ServicesSection.vue';
import StatsSection from '@/components/landing/StatsSection.vue';
import AboutSection from '@/components/landing/AboutSection.vue';
import GallerySection from '@/components/landing/GallerySection.vue';
import ContactSection from '@/components/landing/ContactSection.vue';
import FooterSection from '@/components/landing/FooterSection.vue';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const heroTextRef = ref<HTMLElement | undefined>(undefined);
const ctaButtonRef = ref<HTMLElement | undefined>(undefined);

function scrollToCta(): void {
  const ctaSection = document.getElementById('contact');
  ctaSection?.scrollIntoView({ behavior: 'smooth' });
}

function scrollToServices(): void {
  const servicesSection = document.getElementById('services');
  servicesSection?.scrollIntoView({ behavior: 'smooth' });
}

onMounted(() => {
  // Animate hero text
  if (heroTextRef.value) {
    gsap.fromTo(
      heroTextRef.value,
      { opacity: 0, y: 60 },
      { opacity: 1, y: 0, duration: 1, ease: 'power3.out', delay: 0.3 }
    );
  }

  // Pulse CTA button
  if (ctaButtonRef.value) {
    gsap.to(ctaButtonRef.value, {
      boxShadow: '0 0 0 8px rgba(0, 119, 182, 0.2)',
      duration: 1.5,
      ease: 'power1.inOut',
      repeat: -1,
      yoyo: true,
    });
  }
});
</script>

<template>
  <div class="landing-view">
    <!-- Header Navigation -->
    <HeaderNav />

    <!-- Hero Section with 3D -->
    <section class="hero-section">
      <Hero3DView />

      <div class="hero-content">
        <div ref="heroTextRef" class="hero-text">
          <div class="hero-badge">
            <span class="badge-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
                <circle cx="12" cy="10" r="3"/>
              </svg>
            </span>
            Ташкентская область
          </div>

          <h1 class="hero-title">
            Грузовой терминал<br />
            <span class="highlight">90 000 м²</span>
          </h1>
          <p class="hero-subtitle">
            Услуги по хранению, обработке и таможенному оформлению грузов.
            Современная IT-инфраструктура и AI-мониторинг в реальном времени.
          </p>

          <div class="hero-features">
            <div class="feature-tag">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              Сокращаем издержки
            </div>
            <div class="feature-tag">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              Удобное расположение
            </div>
            <div class="feature-tag">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              Контроль 24/7
            </div>
            <div class="feature-tag">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              До 15 000 контейнеров
            </div>
          </div>

          <div class="hero-actions">
            <button ref="ctaButtonRef" class="cta-primary" @click="scrollToCta">
              Начать сотрудничество
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12 5 19 12 12 19"/>
              </svg>
            </button>
            <button class="cta-secondary" @click="scrollToServices">
              Узнать больше
            </button>
          </div>
        </div>
      </div>

      <!-- Scroll indicator -->
      <div class="scroll-indicator">
        <div class="scroll-mouse">
          <div class="scroll-wheel"></div>
        </div>
        <span>Прокрутите вниз</span>
      </div>
    </section>

    <!-- Stats Section -->
    <StatsSection />

    <!-- Services Section -->
    <ServicesSection />

    <!-- About Section -->
    <AboutSection />

    <!-- Gallery Section -->
    <GallerySection />

    <!-- Contact Section -->
    <ContactSection />

    <!-- Footer -->
    <FooterSection />
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.landing-view {
  background: #FFFFFF;
  overflow-x: hidden;
}

/* Hero Section */
.hero-section {
  position: relative;
  min-height: 100vh;
}

.hero-content {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 60px;
  pointer-events: none;
}

.hero-text {
  pointer-events: auto;
  max-width: 640px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 119, 182, 0.15);
  border-radius: 50px;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 500;
  color: #0077B6;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0, 119, 182, 0.1);
}

.badge-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 64px;
  font-weight: 800;
  line-height: 1.1;
  color: #1E293B;
  margin: 0 0 24px 0;
}

.hero-title .highlight {
  background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-family: 'DM Sans', sans-serif;
  font-size: 18px;
  color: #64748B;
  line-height: 1.7;
  margin: 0 0 32px 0;
  max-width: 500px;
}

.hero-features {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 40px;
}

.feature-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  font-family: 'DM Sans', sans-serif;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.feature-tag svg {
  color: #22C55E;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.cta-primary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 32px;
  background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
  color: white;
  border: none;
  border-radius: 14px;
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 30px rgba(0, 119, 182, 0.35);
}

.cta-primary:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(0, 119, 182, 0.45);
}

.cta-secondary {
  padding: 16px 32px;
  background: white;
  color: #1E293B;
  border: 2px solid #E5E7EB;
  border-radius: 14px;
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.cta-secondary:hover {
  border-color: #0077B6;
  color: #0077B6;
}

/* Scroll Indicator */
.scroll-indicator {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #64748B;
  font-family: 'DM Sans', sans-serif;
  font-size: 12px;
  font-weight: 500;
  animation: fadeInUp 1s ease 1s both;
}

.scroll-mouse {
  width: 26px;
  height: 40px;
  border: 2px solid #CBD5E1;
  border-radius: 13px;
  position: relative;
}

.scroll-wheel {
  width: 4px;
  height: 8px;
  background: #0077B6;
  border-radius: 2px;
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  animation: scrollWheel 1.5s ease-in-out infinite;
}

@keyframes scrollWheel {
  0%, 100% {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  50% {
    opacity: 0.5;
    transform: translateX(-50%) translateY(12px);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

/* Responsive */
@media (max-width: 1024px) {
  .hero-content {
    padding: 0 40px;
  }

  .hero-title {
    font-size: 48px;
  }
}

@media (max-width: 768px) {
  .hero-content {
    padding: 100px 24px 0;
    justify-content: flex-start;
  }

  .hero-title {
    font-size: 36px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .hero-features {
    gap: 8px;
  }

  .feature-tag {
    padding: 8px 12px;
    font-size: 12px;
  }

  .hero-actions {
    flex-direction: column;
  }

  .cta-primary,
  .cta-secondary {
    width: 100%;
    justify-content: center;
  }

  .scroll-indicator {
    display: none;
  }
}
</style>
