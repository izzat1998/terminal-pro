<script setup lang="ts">
import { ref, onMounted } from 'vue';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface Service {
  icon: string;
  title: string;
  description: string;
  area?: string;
  features: string[];
  color: string;
}

const services: Service[] = [
  {
    icon: 'terminal',
    title: 'Терминальные услуги',
    description: 'Полный спектр услуг по приёму, хранению и отгрузке контейнеров. Профессиональная обработка контейнеровозов от 45 до 60 единиц в сутки.',
    area: '90 000 м²',
    features: [
      'Приём и выдача контейнеров 24/7',
      'Сортировка и перегрузка',
      'Взвешивание и досмотр',
      'Формирование партий'
    ],
    color: '#0077B6'
  },
  {
    icon: 'customs',
    title: 'Таможенный склад',
    description: 'Лицензированный склад временного хранения для товаров под таможенным контролем. Полный цикл таможенного оформления.',
    area: '1 944 м²',
    features: [
      'Хранение товаров до 4 лет',
      'Растаможка и перетаможка',
      'Оформление документов',
      'Консультации по ВЭД'
    ],
    color: '#023E8A'
  },
  {
    icon: 'rental',
    title: 'Услуги по аренде',
    description: 'Гибкие условия аренды складских и офисных помещений. Индивидуальный подход к каждому клиенту.',
    features: [
      'Открытые площадки от 100 м²',
      'Крытые склады от 50 м²',
      'Офисные помещения',
      'Долгосрочная аренда'
    ],
    color: '#00B4D8'
  },
  {
    icon: 'cold',
    title: 'Холодильный склад',
    description: 'Современный рефрижераторный склад с контролем температуры для скоропортящихся товаров.',
    area: '800 м²',
    features: [
      'Температура от -18°C до +8°C',
      'Мониторинг 24/7',
      'Сертифицированное хранение',
      'Быстрая загрузка/выгрузка'
    ],
    color: '#48CAE4'
  }
];

const sectionRef = ref<HTMLElement | null>(null);

onMounted(() => {
  if (sectionRef.value) {
    const cards = sectionRef.value.querySelectorAll('.service-card');

    gsap.fromTo(cards,
      { opacity: 0, y: 60 },
      {
        opacity: 1,
        y: 0,
        duration: 0.8,
        stagger: 0.15,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: sectionRef.value,
          start: 'top 70%',
        }
      }
    );
  }
});

function getIconPath(icon: string): string {
  const icons: Record<string, string> = {
    terminal: `<path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
               <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
               <line x1="12" y1="22.08" x2="12" y2="12"/>`,
    customs: `<rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18"/>
              <path d="M9 21V9"/>`,
    rental: `<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
             <polyline points="9 22 9 12 15 12 15 22"/>`,
    cold: `<path d="M12 2v20"/>
           <path d="M2 12h20"/>
           <path d="M12 2l4 4-4 4"/>
           <path d="M12 2l-4 4 4 4"/>
           <path d="M12 22l4-4-4-4"/>
           <path d="M12 22l-4-4 4-4"/>
           <path d="M2 12l4 4 4-4"/>
           <path d="M22 12l-4-4-4 4"/>`
  };
  return icons[icon] || '';
}
</script>

<template>
  <section id="services" ref="sectionRef" class="services-section">
    <div class="section-container">
      <div class="section-header">
        <span class="section-badge">Услуги</span>
        <h2 class="section-title">Все виды услуг в одной локации</h2>
        <p class="section-subtitle">
          Комплексное обслуживание грузов: от приёма на терминал до таможенного оформления и хранения
        </p>
      </div>

      <div class="services-grid">
        <div
          v-for="(service, index) in services"
          :key="index"
          class="service-card"
          :style="{ '--accent-color': service.color }"
        >
          <div class="card-header">
            <div class="service-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" v-html="getIconPath(service.icon)" />
            </div>
            <div v-if="service.area" class="service-area">
              {{ service.area }}
            </div>
          </div>

          <h3 class="service-title">{{ service.title }}</h3>
          <p class="service-description">{{ service.description }}</p>

          <ul class="feature-list">
            <li v-for="(feature, fIndex) in service.features" :key="fIndex">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ feature }}
            </li>
          </ul>

          <div class="card-decoration"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.services-section {
  padding: 120px 0;
  background: #FFFFFF;
}

.section-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.section-header {
  text-align: center;
  margin-bottom: 64px;
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
  font-size: 42px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 16px 0;
  line-height: 1.2;
}

.section-subtitle {
  font-family: 'DM Sans', sans-serif;
  font-size: 18px;
  color: #64748B;
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.6;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.service-card {
  position: relative;
  padding: 32px;
  background: #FFFFFF;
  border-radius: 20px;
  border: 1px solid #E5E7EB;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.service-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 60px rgba(0, 119, 182, 0.12);
  border-color: var(--accent-color);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.service-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 119, 182, 0.08) 0%, rgba(0, 180, 216, 0.08) 100%);
  border-radius: 14px;
  transition: all 0.3s ease;
}

.service-card:hover .service-icon {
  background: var(--accent-color);
}

.service-icon svg {
  color: var(--accent-color);
  transition: color 0.3s ease;
}

.service-card:hover .service-icon svg {
  color: white;
}

.service-area {
  padding: 8px 16px;
  background: rgba(0, 119, 182, 0.06);
  border-radius: 8px;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--accent-color);
}

.service-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 12px 0;
  transition: color 0.3s ease;
}

.service-card:hover .service-title {
  color: var(--accent-color);
}

.service-description {
  font-family: 'DM Sans', sans-serif;
  font-size: 15px;
  color: #64748B;
  line-height: 1.6;
  margin: 0 0 24px 0;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  color: #475569;
}

.feature-list svg {
  color: #22C55E;
  flex-shrink: 0;
}

.card-decoration {
  position: absolute;
  top: -50px;
  right: -50px;
  width: 150px;
  height: 150px;
  background: radial-gradient(circle, var(--accent-color) 0%, transparent 70%);
  opacity: 0.04;
  border-radius: 50%;
  transition: all 0.4s ease;
}

.service-card:hover .card-decoration {
  opacity: 0.08;
  transform: scale(1.3);
}

@media (max-width: 900px) {
  .services-grid {
    grid-template-columns: 1fr;
  }

  .section-title {
    font-size: 32px;
  }
}

@media (max-width: 600px) {
  .services-section {
    padding: 80px 0;
  }

  .section-title {
    font-size: 28px;
  }

  .service-card {
    padding: 24px;
  }

  .feature-list {
    grid-template-columns: 1fr;
  }
}
</style>
