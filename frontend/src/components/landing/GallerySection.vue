<script setup lang="ts">
import { ref, onMounted } from 'vue';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface GalleryImage {
  src: string;
  alt: string;
  category: string;
}

// Using placeholder images - in production these would be actual terminal photos
const galleryImages: GalleryImage[] = [
  { src: 'https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?w=600', alt: 'Контейнерный терминал', category: 'Терминал' },
  { src: 'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=600', alt: 'Погрузочные работы', category: 'Операции' },
  { src: 'https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=600', alt: 'Складские помещения', category: 'Склад' },
  { src: 'https://images.unsplash.com/photo-1553413077-190dd305871c?w=600', alt: 'Грузовой транспорт', category: 'Транспорт' },
  { src: 'https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?w=600', alt: 'Контейнеры на площадке', category: 'Терминал' },
  { src: 'https://images.unsplash.com/photo-1587293852726-70cdb56c2866?w=600', alt: 'Кран на терминале', category: 'Оборудование' },
];

const activeCategory = ref('Все');
const categories = ['Все', 'Терминал', 'Операции', 'Склад', 'Транспорт', 'Оборудование'];
const lightboxOpen = ref(false);
const lightboxImage = ref<GalleryImage | null>(null);
const sectionRef = ref<HTMLElement | null>(null);

const filteredImages = ref(galleryImages);

function filterByCategory(category: string): void {
  activeCategory.value = category;
  if (category === 'Все') {
    filteredImages.value = galleryImages;
  } else {
    filteredImages.value = galleryImages.filter(img => img.category === category);
  }
}

function openLightbox(image: GalleryImage): void {
  lightboxImage.value = image;
  lightboxOpen.value = true;
  document.body.style.overflow = 'hidden';
}

function closeLightbox(): void {
  lightboxOpen.value = false;
  lightboxImage.value = null;
  document.body.style.overflow = '';
}

onMounted(() => {
  if (sectionRef.value) {
    gsap.fromTo(
      sectionRef.value.querySelectorAll('.gallery-item'),
      { opacity: 0, scale: 0.9 },
      {
        opacity: 1,
        scale: 1,
        duration: 0.6,
        stagger: 0.1,
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
  <section id="gallery" ref="sectionRef" class="gallery-section">
    <div class="section-container">
      <div class="section-header">
        <span class="section-badge">Галерея</span>
        <h2 class="section-title">Фото-экскурсия по терминалу</h2>
        <p class="section-subtitle">
          Познакомьтесь с нашей инфраструктурой и возможностями терминала
        </p>
      </div>

      <div class="category-filter">
        <button
          v-for="category in categories"
          :key="category"
          class="filter-btn"
          :class="{ active: activeCategory === category }"
          @click="filterByCategory(category)"
        >
          {{ category }}
        </button>
      </div>

      <div class="gallery-grid">
        <div
          v-for="(image, index) in filteredImages"
          :key="index"
          class="gallery-item"
          @click="openLightbox(image)"
        >
          <img :src="image.src" :alt="image.alt" loading="lazy" />
          <div class="item-overlay">
            <span class="item-category">{{ image.category }}</span>
            <span class="item-title">{{ image.alt }}</span>
            <div class="zoom-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="11" y1="8" x2="11" y2="14"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Lightbox -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="lightboxOpen" class="lightbox" @click.self="closeLightbox">
          <button class="lightbox-close" @click="closeLightbox">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <div class="lightbox-content">
            <img v-if="lightboxImage" :src="lightboxImage.src" :alt="lightboxImage.alt" />
            <div v-if="lightboxImage" class="lightbox-caption">
              <span class="caption-category">{{ lightboxImage.category }}</span>
              <span class="caption-title">{{ lightboxImage.alt }}</span>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.gallery-section {
  padding: 120px 0;
  background: #F8FAFC;
}

.section-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.section-header {
  text-align: center;
  margin-bottom: 48px;
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

.category-filter {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 40px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 10px 20px;
  background: white;
  border: 1px solid #E5E7EB;
  border-radius: 50px;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 500;
  color: #64748B;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-btn:hover {
  border-color: #0077B6;
  color: #0077B6;
}

.filter-btn.active {
  background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
  border-color: transparent;
  color: white;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.gallery-item {
  position: relative;
  aspect-ratio: 4/3;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
}

.gallery-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.gallery-item:hover img {
  transform: scale(1.1);
}

.item-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 40%, rgba(0, 0, 0, 0.7) 100%);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 20px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.gallery-item:hover .item-overlay {
  opacity: 1;
}

.item-category {
  font-family: 'DM Sans', sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #00B4D8;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 4px;
}

.item-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: white;
}

.zoom-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.8);
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  transition: all 0.3s ease;
}

.zoom-icon svg {
  color: #0077B6;
}

.gallery-item:hover .zoom-icon {
  transform: translate(-50%, -50%) scale(1);
}

/* Lightbox */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 40px;
}

.lightbox-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 8px;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.lightbox-close:hover {
  opacity: 1;
}

.lightbox-content {
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.lightbox-content img {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 8px;
}

.lightbox-caption {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 20px;
}

.caption-category {
  font-family: 'DM Sans', sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #00B4D8;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 4px;
}

.caption-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .gallery-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .section-title {
    font-size: 32px;
  }
}

@media (max-width: 600px) {
  .gallery-section {
    padding: 80px 0;
  }

  .gallery-grid {
    grid-template-columns: 1fr;
  }

  .section-title {
    font-size: 28px;
  }

  .filter-btn {
    padding: 8px 16px;
    font-size: 13px;
  }
}
</style>
