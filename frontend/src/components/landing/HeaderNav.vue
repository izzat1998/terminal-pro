<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

const isScrolled = ref(false);
const isMobileMenuOpen = ref(false);

function handleScroll(): void {
  isScrolled.value = window.scrollY > 50;
}

function toggleMobileMenu(): void {
  isMobileMenuOpen.value = !isMobileMenuOpen.value;
}

function scrollToSection(sectionId: string): void {
  const section = document.getElementById(sectionId);
  section?.scrollIntoView({ behavior: 'smooth' });
  isMobileMenuOpen.value = false;
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll);
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<template>
  <header class="header" :class="{ 'is-scrolled': isScrolled }">
    <div class="header-container">
      <!-- Logo -->
      <div class="logo">
        <div class="logo-icon">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Geometric arrow pattern matching the company logo -->
            <path d="M24 4L28 8L24 12L20 8L24 4Z" fill="#00B4D8"/>
            <path d="M24 36L28 40L24 44L20 40L24 36Z" fill="#00B4D8"/>
            <path d="M4 24L8 20L12 24L8 28L4 24Z" fill="#00B4D8"/>
            <path d="M36 24L40 20L44 24L40 28L36 24Z" fill="#00B4D8"/>
            <path d="M8 8L12 4L16 8L12 12L8 8Z" fill="#0077B6"/>
            <path d="M32 8L36 4L40 8L36 12L32 8Z" fill="#0077B6"/>
            <path d="M8 40L12 36L16 40L12 44L8 40Z" fill="#0077B6"/>
            <path d="M32 40L36 36L40 40L36 44L32 40Z" fill="#0077B6"/>
            <!-- Center octagon -->
            <path d="M18 14H30L36 20V28L30 34H18L12 28V20L18 14Z" stroke="#0077B6" stroke-width="2" fill="none"/>
          </svg>
        </div>
        <div class="logo-text">
          <span class="logo-name">MULTIMODAL TRANS</span>
          <span class="logo-tagline">TERMINAL</span>
        </div>
      </div>

      <!-- Desktop Navigation -->
      <nav class="nav-desktop">
        <button class="nav-link" @click="scrollToSection('services')">Услуги</button>
        <button class="nav-link" @click="scrollToSection('about')">О терминале</button>
        <button class="nav-link" @click="scrollToSection('gallery')">Галерея</button>
        <button class="nav-link" @click="scrollToSection('contact')">Контакты</button>
      </nav>

      <!-- Contact Info -->
      <div class="header-contact">
        <a href="tel:+998991433388" class="phone-link">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/>
          </svg>
          <span>+998 (99) 143-33-88</span>
        </a>
        <button class="cta-button" @click="scrollToSection('contact')">
          Связаться
        </button>
      </div>

      <!-- Mobile Menu Button -->
      <button class="mobile-menu-btn" @click="toggleMobileMenu" :class="{ 'is-open': isMobileMenuOpen }">
        <span></span>
        <span></span>
        <span></span>
      </button>
    </div>

    <!-- Mobile Menu -->
    <Transition name="slide">
      <div v-if="isMobileMenuOpen" class="mobile-menu">
        <nav class="mobile-nav">
          <button class="mobile-nav-link" @click="scrollToSection('services')">Услуги</button>
          <button class="mobile-nav-link" @click="scrollToSection('about')">О терминале</button>
          <button class="mobile-nav-link" @click="scrollToSection('gallery')">Галерея</button>
          <button class="mobile-nav-link" @click="scrollToSection('contact')">Контакты</button>
        </nav>
        <div class="mobile-contact">
          <a href="tel:+998991433388" class="mobile-phone">+998 (99) 143-33-88</a>
          <a href="tel:+998711403388" class="mobile-phone">+998 (71) 140-33-88</a>
        </div>
      </div>
    </Transition>
  </header>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  transition: all 0.3s ease;
}

.header.is-scrolled {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: 0 4px 30px rgba(0, 119, 182, 0.08);
}

.header-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 48px;
  height: 48px;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-name {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: #0077B6;
  letter-spacing: 0.5px;
  line-height: 1.2;
}

.logo-tagline {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 11px;
  font-weight: 600;
  color: #00B4D8;
  letter-spacing: 2px;
}

.nav-desktop {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 10px 20px;
  background: none;
  border: none;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 500;
  color: #1E293B;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.nav-link:hover {
  background: rgba(0, 119, 182, 0.08);
  color: #0077B6;
}

.header-contact {
  display: flex;
  align-items: center;
  gap: 16px;
}

.phone-link {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
  text-decoration: none;
  transition: color 0.2s ease;
}

.phone-link:hover {
  color: #0077B6;
}

.phone-link svg {
  color: #0077B6;
}

.cta-button {
  padding: 12px 24px;
  background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 15px rgba(0, 119, 182, 0.3);
}

.cta-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 119, 182, 0.4);
}

.mobile-menu-btn {
  display: none;
  flex-direction: column;
  gap: 5px;
  padding: 8px;
  background: none;
  border: none;
  cursor: pointer;
}

.mobile-menu-btn span {
  display: block;
  width: 24px;
  height: 2px;
  background: #1E293B;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.mobile-menu-btn.is-open span:nth-child(1) {
  transform: rotate(45deg) translate(5px, 5px);
}

.mobile-menu-btn.is-open span:nth-child(2) {
  opacity: 0;
}

.mobile-menu-btn.is-open span:nth-child(3) {
  transform: rotate(-45deg) translate(5px, -5px);
}

.mobile-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  padding: 24px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 24px;
}

.mobile-nav-link {
  padding: 16px;
  background: none;
  border: none;
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  font-weight: 500;
  color: #1E293B;
  text-align: left;
  cursor: pointer;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.mobile-nav-link:hover {
  background: rgba(0, 119, 182, 0.08);
  color: #0077B6;
}

.mobile-contact {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid #E5E7EB;
}

.mobile-phone {
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #0077B6;
  text-decoration: none;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 1024px) {
  .nav-desktop {
    display: none;
  }

  .header-contact {
    display: none;
  }

  .mobile-menu-btn {
    display: flex;
  }

  .header-container {
    padding: 12px 20px;
  }
}

@media (max-width: 480px) {
  .logo-text {
    display: none;
  }
}
</style>
