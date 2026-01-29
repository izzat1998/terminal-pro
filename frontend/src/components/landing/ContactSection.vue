<script setup lang="ts">
import { ref, reactive } from 'vue';

interface ContactForm {
  name: string;
  phone: string;
  email: string;
  company: string;
  message: string;
}

const form = reactive<ContactForm>({
  name: '',
  phone: '',
  email: '',
  company: '',
  message: ''
});

const isSubmitting = ref(false);
const isSubmitted = ref(false);

async function handleSubmit(): Promise<void> {
  isSubmitting.value = true;

  // Simulate form submission
  await new Promise(resolve => setTimeout(resolve, 1500));

  isSubmitting.value = false;
  isSubmitted.value = true;

  // Reset form after success
  Object.assign(form, {
    name: '',
    phone: '',
    email: '',
    company: '',
    message: ''
  });

  // Reset success message after 5 seconds
  setTimeout(() => {
    isSubmitted.value = false;
  }, 5000);
}

const contactInfo = [
  {
    icon: 'phone',
    title: 'Телефон',
    lines: ['+998 (99) 143-33-88', '+998 (71) 140-33-88']
  },
  {
    icon: 'location',
    title: 'Адрес',
    lines: ['Ташкентская область', 'Зангиатинский район']
  },
  {
    icon: 'clock',
    title: 'Режим работы',
    lines: ['Круглосуточно', '24/7']
  }
];

function getIconSvg(icon: string): string {
  const icons: Record<string, string> = {
    phone: `<path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/>`,
    location: `<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
               <circle cx="12" cy="10" r="3"/>`,
    clock: `<circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>`
  };
  return icons[icon] || '';
}
</script>

<template>
  <section id="contact" class="contact-section">
    <div class="section-container">
      <div class="contact-layout">
        <!-- Left: Form -->
        <div class="form-container">
          <div class="form-header">
            <span class="section-badge">Связаться с нами</span>
            <h2 class="section-title">Оставьте заявку</h2>
            <p class="section-subtitle">
              Наши специалисты свяжутся с вами в течение 30 минут
            </p>
          </div>

          <form v-if="!isSubmitted" @submit.prevent="handleSubmit" class="contact-form">
            <div class="form-row">
              <div class="form-group">
                <label for="name">Имя *</label>
                <input
                  id="name"
                  v-model="form.name"
                  type="text"
                  placeholder="Ваше имя"
                  required
                />
              </div>
              <div class="form-group">
                <label for="phone">Телефон *</label>
                <input
                  id="phone"
                  v-model="form.phone"
                  type="tel"
                  placeholder="+998 (__) ___-__-__"
                  required
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="email">Email</label>
                <input
                  id="email"
                  v-model="form.email"
                  type="email"
                  placeholder="email@company.com"
                />
              </div>
              <div class="form-group">
                <label for="company">Компания</label>
                <input
                  id="company"
                  v-model="form.company"
                  type="text"
                  placeholder="Название компании"
                />
              </div>
            </div>

            <div class="form-group full-width">
              <label for="message">Сообщение</label>
              <textarea
                id="message"
                v-model="form.message"
                rows="4"
                placeholder="Опишите ваш запрос..."
              ></textarea>
            </div>

            <button type="submit" class="submit-btn" :disabled="isSubmitting">
              <span v-if="!isSubmitting">Отправить заявку</span>
              <span v-else class="loading">
                <svg class="spinner" width="20" height="20" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4 31.4" stroke-linecap="round"/>
                </svg>
                Отправка...
              </span>
            </button>
          </form>

          <div v-else class="success-message">
            <div class="success-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <h3>Заявка отправлена!</h3>
            <p>Мы свяжемся с вами в ближайшее время</p>
          </div>
        </div>

        <!-- Right: Info + Map -->
        <div class="info-container">
          <div class="contact-cards">
            <div
              v-for="(info, index) in contactInfo"
              :key="index"
              class="contact-card"
            >
              <div class="card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" v-html="getIconSvg(info.icon)" />
              </div>
              <div class="card-content">
                <span class="card-title">{{ info.title }}</span>
                <span v-for="(line, i) in info.lines" :key="i" class="card-line">{{ line }}</span>
              </div>
            </div>
          </div>

          <div class="map-container">
            <iframe
              src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2996.7!2d69.2!3d41.3!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zNDHCsDE4JzAwLjAiTiA2OcKwMTInMDAuMCJF!5e0!3m2!1sen!2s!4v1600000000000!5m2!1sen!2s"
              width="100%"
              height="100%"
              style="border:0;"
              :allowfullscreen="true"
              loading="lazy"
              referrerpolicy="no-referrer-when-downgrade"
            ></iframe>
            <div class="map-overlay">
              <a
                href="https://maps.google.com/?q=41.3,69.2"
                target="_blank"
                rel="noopener noreferrer"
                class="map-link"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
                  <polyline points="15 3 21 3 21 9"/>
                  <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
                Открыть в Google Maps
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.contact-section {
  padding: 120px 0;
  background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
}

.section-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.contact-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
}

.form-container {
  background: white;
  padding: 40px;
  border-radius: 24px;
  box-shadow: 0 10px 50px rgba(0, 119, 182, 0.08);
}

.form-header {
  margin-bottom: 32px;
}

.section-badge {
  display: inline-block;
  padding: 8px 20px;
  background: rgba(0, 119, 182, 0.08);
  color: #0077B6;
  border-radius: 50px;
  font-family: 'DM Sans', sans-serif;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
}

.section-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 32px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 12px 0;
}

.section-subtitle {
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  color: #64748B;
  margin: 0;
}

.contact-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-group label {
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #1E293B;
}

.form-group input,
.form-group textarea {
  padding: 14px 18px;
  background: #F8FAFC;
  border: 2px solid #E5E7EB;
  border-radius: 12px;
  font-family: 'DM Sans', sans-serif;
  font-size: 15px;
  color: #1E293B;
  transition: all 0.2s ease;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #0077B6;
  background: white;
}

.form-group input::placeholder,
.form-group textarea::placeholder {
  color: #94A3B8;
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
}

.submit-btn {
  padding: 16px 32px;
  background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 25px rgba(0, 119, 182, 0.3);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(0, 119, 182, 0.4);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.success-message {
  text-align: center;
  padding: 40px 20px;
}

.success-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(34, 197, 94, 0.1);
  border-radius: 50%;
  margin: 0 auto 20px;
}

.success-icon svg {
  color: #22C55E;
}

.success-message h3 {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 8px 0;
}

.success-message p {
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  color: #64748B;
  margin: 0;
}

.info-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.contact-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.contact-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 24px;
  background: white;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  transition: all 0.3s ease;
}

.contact-card:hover {
  border-color: #0077B6;
  box-shadow: 0 8px 30px rgba(0, 119, 182, 0.1);
}

.card-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
  border-radius: 12px;
  flex-shrink: 0;
}

.card-icon svg {
  color: white;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-title {
  font-family: 'DM Sans', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-line {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
}

.map-container {
  position: relative;
  height: 280px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #E5E7EB;
}

.map-container iframe {
  filter: grayscale(20%);
}

.map-overlay {
  position: absolute;
  bottom: 16px;
  left: 16px;
}

.map-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: white;
  border-radius: 10px;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #0077B6;
  text-decoration: none;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

.map-link:hover {
  background: #0077B6;
  color: white;
}

@media (max-width: 1024px) {
  .contact-layout {
    grid-template-columns: 1fr;
    gap: 40px;
  }
}

@media (max-width: 600px) {
  .contact-section {
    padding: 80px 0;
  }

  .form-container {
    padding: 24px;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .section-title {
    font-size: 26px;
  }
}
</style>
