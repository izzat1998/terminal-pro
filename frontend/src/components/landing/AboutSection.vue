<script setup lang="ts">
import { ref, onMounted } from 'vue';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface Advantage {
  icon: string;
  title: string;
  description: string;
}

const advantages: Advantage[] = [
  {
    icon: 'location',
    title: 'Транспортная доступность',
    description: 'Удобное расположение вблизи основных автомагистралей. Прямой выход на международные транспортные коридоры.'
  },
  {
    icon: 'area',
    title: 'Площадь склада — 90 000 м²',
    description: 'Крупнейший мультимодальный терминал в регионе. Открытые и крытые площадки для любых типов грузов.'
  },
  {
    icon: 'equipment',
    title: 'Специальная техника',
    description: 'Контейнерные краны, вилочные погрузчики, фронтальные погрузчики. Оборудование для работы с негабаритными грузами.'
  },
  {
    icon: 'control',
    title: 'Учёт и контроль',
    description: 'IT-система отслеживания грузов в реальном времени. Полная прозрачность всех операций для клиентов.'
  }
];

const sectionRef = ref<HTMLElement | null>(null);

function getIconSvg(icon: string): string {
  const icons: Record<string, string> = {
    location: `<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
               <circle cx="12" cy="10" r="3"/>`,
    area: `<rect x="3" y="3" width="7" height="7"/>
           <rect x="14" y="3" width="7" height="7"/>
           <rect x="14" y="14" width="7" height="7"/>
           <rect x="3" y="14" width="7" height="7"/>`,
    equipment: `<path d="M14 18V6a2 2 0 00-2-2H4a2 2 0 00-2 2v11a1 1 0 001 1h2"/>
                <path d="M15 18H9"/>
                <path d="M19 18h2a1 1 0 001-1v-3.65a1 1 0 00-.22-.624l-3.48-4.35A1 1 0 0017.52 8H14"/>
                <circle cx="17" cy="18" r="2"/>
                <circle cx="7" cy="18" r="2"/>`,
    control: `<path d="M12 20h9"/>
              <path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
              <path d="M15 5l3 3"/>`
  };
  return icons[icon] || '';
}

onMounted(() => {
  if (sectionRef.value) {
    gsap.fromTo(
      sectionRef.value.querySelectorAll('.advantage-card'),
      { opacity: 0, x: -40 },
      {
        opacity: 1,
        x: 0,
        duration: 0.6,
        stagger: 0.15,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: sectionRef.value,
          start: 'top 70%',
        }
      }
    );
  }
});
</script>

<template>
  <section id="about" ref="sectionRef" class="about-section">
    <div class="section-container">
      <div class="about-layout">
        <div class="about-content">
          <span class="section-badge">О терминале</span>
          <h2 class="section-title">
            Ежедневно более 100 компаний выбирают<br/>
            <span class="highlight">MULTIMODAL TRANS TERMINAL</span>
          </h2>
          <p class="section-description">
            Мы предоставляем полный комплекс услуг по хранению, обработке и таможенному оформлению грузов.
            Современная инфраструктура и профессиональная команда гарантируют надёжность и эффективность работы.
          </p>

          <div class="cta-group">
            <button class="cta-primary" onclick="document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })">
              Получить консультацию
            </button>
            <a href="tel:+998991433388" class="cta-secondary">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/>
              </svg>
              Позвонить
            </a>
          </div>
        </div>

        <div class="advantages-grid">
          <div
            v-for="(advantage, index) in advantages"
            :key="index"
            class="advantage-card"
          >
            <div class="advantage-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" v-html="getIconSvg(advantage.icon)" />
            </div>
            <h3 class="advantage-title">{{ advantage.title }}</h3>
            <p class="advantage-description">{{ advantage.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Decorative elements -->
    <div class="bg-decoration">
      <div class="decoration-circle circle-1"></div>
      <div class="decoration-circle circle-2"></div>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.about-section {
  position: relative;
  padding: 120px 0;
  background: #FFFFFF;
  overflow: hidden;
}

.section-container {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  z-index: 1;
}

.about-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  align-items: center;
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
  font-size: 36px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 24px 0;
  line-height: 1.3;
}

.section-title .highlight {
  color: #0077B6;
}

.section-description {
  font-family: 'DM Sans', sans-serif;
  font-size: 17px;
  color: #64748B;
  line-height: 1.7;
  margin: 0 0 32px 0;
}

.cta-group {
  display: flex;
  gap: 16px;
}

.cta-primary {
  padding: 14px 28px;
  background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-family: 'DM Sans', sans-serif;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 25px rgba(0, 119, 182, 0.3);
}

.cta-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(0, 119, 182, 0.4);
}

.cta-secondary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  background: white;
  color: #0077B6;
  border: 2px solid #0077B6;
  border-radius: 12px;
  font-family: 'DM Sans', sans-serif;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s ease;
}

.cta-secondary:hover {
  background: rgba(0, 119, 182, 0.05);
}

.advantages-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.advantage-card {
  padding: 28px;
  background: #F8FAFC;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  transition: all 0.3s ease;
}

.advantage-card:hover {
  background: white;
  border-color: #0077B6;
  box-shadow: 0 10px 40px rgba(0, 119, 182, 0.1);
  transform: translateY(-4px);
}

.advantage-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
  border-radius: 12px;
  margin-bottom: 16px;
}

.advantage-icon svg {
  color: white;
}

.advantage-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 17px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 8px 0;
}

.advantage-description {
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  color: #64748B;
  line-height: 1.6;
  margin: 0;
}

.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.decoration-circle {
  position: absolute;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(0, 119, 182, 0.05) 0%, rgba(0, 180, 216, 0.05) 100%);
}

.circle-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
}

.circle-2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
}

@media (max-width: 1024px) {
  .about-layout {
    grid-template-columns: 1fr;
    gap: 48px;
  }

  .section-title {
    font-size: 30px;
  }
}

@media (max-width: 600px) {
  .about-section {
    padding: 80px 0;
  }

  .section-title {
    font-size: 26px;
  }

  .advantages-grid {
    grid-template-columns: 1fr;
  }

  .cta-group {
    flex-direction: column;
  }

  .cta-primary,
  .cta-secondary {
    justify-content: center;
  }
}
</style>
