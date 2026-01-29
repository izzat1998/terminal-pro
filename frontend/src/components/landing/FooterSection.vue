<script setup lang="ts">
const currentYear = new Date().getFullYear();

function scrollToSection(sectionId: string): void {
  const section = document.getElementById(sectionId);
  section?.scrollIntoView({ behavior: 'smooth' });
}
</script>

<template>
  <footer class="footer">
    <div class="footer-container">
      <div class="footer-main">
        <!-- Logo & Description -->
        <div class="footer-brand">
          <div class="footer-logo">
            <div class="logo-icon">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M24 4L28 8L24 12L20 8L24 4Z" fill="#00B4D8"/>
                <path d="M24 36L28 40L24 44L20 40L24 36Z" fill="#00B4D8"/>
                <path d="M4 24L8 20L12 24L8 28L4 24Z" fill="#00B4D8"/>
                <path d="M36 24L40 20L44 24L40 28L36 24Z" fill="#00B4D8"/>
                <path d="M8 8L12 4L16 8L12 12L8 8Z" fill="#0077B6"/>
                <path d="M32 8L36 4L40 8L36 12L32 8Z" fill="#0077B6"/>
                <path d="M8 40L12 36L16 40L12 44L8 40Z" fill="#0077B6"/>
                <path d="M32 40L36 36L40 40L36 44L32 40Z" fill="#0077B6"/>
                <path d="M18 14H30L36 20V28L30 34H18L12 28V20L18 14Z" stroke="#0077B6" stroke-width="2" fill="none"/>
              </svg>
            </div>
            <div class="logo-text">
              <span class="logo-name">MULTIMODAL TRANS</span>
              <span class="logo-tagline">TERMINAL</span>
            </div>
          </div>
          <p class="footer-description">
            Современный мультимодальный терминал для хранения, обработки и таможенного оформления грузов.
            Работаем с 2014 года.
          </p>
          <div class="social-links">
            <a href="#" class="social-link" aria-label="Telegram">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.12.03-1.99 1.27-5.62 3.72-.53.36-1.01.54-1.44.53-.47-.01-1.38-.27-2.06-.49-.83-.27-1.49-.42-1.43-.88.03-.24.37-.49 1.02-.74 3.98-1.73 6.64-2.87 7.97-3.43 3.79-1.6 4.58-1.88 5.1-1.89.11 0 .37.03.53.18.14.12.18.28.2.45-.02.07-.02.14-.03.27z"/>
              </svg>
            </a>
            <a href="#" class="social-link" aria-label="Instagram">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2c2.717 0 3.056.01 4.122.06 1.065.05 1.79.217 2.428.465.66.254 1.216.598 1.772 1.153.509.5.902 1.105 1.153 1.772.247.637.415 1.363.465 2.428.047 1.066.06 1.405.06 4.122 0 2.717-.01 3.056-.06 4.122-.05 1.065-.218 1.79-.465 2.428a4.883 4.883 0 01-1.153 1.772c-.5.508-1.105.902-1.772 1.153-.637.247-1.363.415-2.428.465-1.066.047-1.405.06-4.122.06-2.717 0-3.056-.01-4.122-.06-1.065-.05-1.79-.218-2.428-.465a4.89 4.89 0 01-1.772-1.153 4.904 4.904 0 01-1.153-1.772c-.248-.637-.415-1.363-.465-2.428C2.013 15.056 2 14.717 2 12c0-2.717.01-3.056.06-4.122.05-1.066.217-1.79.465-2.428a4.88 4.88 0 011.153-1.772A4.897 4.897 0 015.45 2.525c.638-.248 1.362-.415 2.428-.465C8.944 2.013 9.283 2 12 2zm0 5a5 5 0 100 10 5 5 0 000-10zm6.5-.25a1.25 1.25 0 10-2.5 0 1.25 1.25 0 002.5 0zM12 9a3 3 0 110 6 3 3 0 010-6z"/>
              </svg>
            </a>
            <a href="#" class="social-link" aria-label="Facebook">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
              </svg>
            </a>
          </div>
        </div>

        <!-- Navigation -->
        <div class="footer-nav">
          <h4>Навигация</h4>
          <ul>
            <li><button @click="scrollToSection('services')">Услуги</button></li>
            <li><button @click="scrollToSection('about')">О терминале</button></li>
            <li><button @click="scrollToSection('gallery')">Галерея</button></li>
            <li><button @click="scrollToSection('contact')">Контакты</button></li>
          </ul>
        </div>

        <!-- Services -->
        <div class="footer-nav">
          <h4>Услуги</h4>
          <ul>
            <li><button @click="scrollToSection('services')">Терминальные услуги</button></li>
            <li><button @click="scrollToSection('services')">Таможенный склад</button></li>
            <li><button @click="scrollToSection('services')">Аренда площадей</button></li>
            <li><button @click="scrollToSection('services')">Холодильный склад</button></li>
          </ul>
        </div>

        <!-- Contact -->
        <div class="footer-contact">
          <h4>Контакты</h4>
          <div class="contact-item">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/>
            </svg>
            <div>
              <a href="tel:+998991433388">+998 (99) 143-33-88</a>
              <a href="tel:+998711403388">+998 (71) 140-33-88</a>
            </div>
          </div>
          <div class="contact-item">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
            <span>Ташкентская область,<br/>Зангиатинский район</span>
          </div>
          <div class="contact-item">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>Круглосуточно 24/7</span>
          </div>
        </div>
      </div>

      <div class="footer-bottom">
        <p>© {{ currentYear }} Multimodal Trans Terminal. Все права защищены.</p>
        <div class="footer-links">
          <a href="#">Политика конфиденциальности</a>
          <span class="separator">•</span>
          <a href="#">Условия использования</a>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.footer {
  background: #0F172A;
  color: white;
  padding: 80px 0 0;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.footer-main {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1.2fr;
  gap: 48px;
  padding-bottom: 60px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.footer-brand {
  max-width: 300px;
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
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
  color: white;
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

.footer-description {
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  color: #94A3B8;
  line-height: 1.7;
  margin: 0 0 24px 0;
}

.social-links {
  display: flex;
  gap: 12px;
}

.social-link {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  color: #94A3B8;
  transition: all 0.2s ease;
}

.social-link:hover {
  background: #0077B6;
  color: white;
}

.footer-nav h4,
.footer-contact h4 {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 15px;
  font-weight: 700;
  color: white;
  margin: 0 0 20px 0;
}

.footer-nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.footer-nav li {
  margin-bottom: 12px;
}

.footer-nav button {
  background: none;
  border: none;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  color: #94A3B8;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s ease;
}

.footer-nav button:hover {
  color: #00B4D8;
}

.footer-contact {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.contact-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.contact-item svg {
  color: #0077B6;
  flex-shrink: 0;
  margin-top: 2px;
}

.contact-item div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.contact-item a,
.contact-item span {
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  color: #94A3B8;
  text-decoration: none;
  line-height: 1.5;
}

.contact-item a:hover {
  color: #00B4D8;
}

.footer-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 0;
}

.footer-bottom p {
  font-family: 'DM Sans', sans-serif;
  font-size: 13px;
  color: #64748B;
  margin: 0;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer-links a {
  font-family: 'DM Sans', sans-serif;
  font-size: 13px;
  color: #64748B;
  text-decoration: none;
  transition: color 0.2s ease;
}

.footer-links a:hover {
  color: #00B4D8;
}

.separator {
  color: #475569;
}

@media (max-width: 1024px) {
  .footer-main {
    grid-template-columns: 1fr 1fr;
    gap: 40px;
  }

  .footer-brand {
    grid-column: 1 / -1;
    max-width: none;
  }
}

@media (max-width: 600px) {
  .footer {
    padding: 60px 0 0;
  }

  .footer-main {
    grid-template-columns: 1fr;
    gap: 32px;
  }

  .footer-bottom {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
}
</style>
