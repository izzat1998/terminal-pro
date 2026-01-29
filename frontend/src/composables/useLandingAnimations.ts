/**
 * Landing page animations composable using GSAP
 */

// Types for the composable
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export interface AnimationConfig {
  duration?: number;
  ease?: string;
  delay?: number;
  stagger?: number;
}

export function useLandingAnimations() {
  /**
   * Animate elements on scroll using stagger
   */
  function staggerIn(
    elements: HTMLElement[] | string,
    config: AnimationConfig = {}
  ): void {
    const {
      duration = 0.6,
      ease = 'power2.out',
      delay = 0,
      stagger = 0.1,
    } = config;

    const targets = typeof elements === 'string' ? document.querySelectorAll(elements) : elements;

    gsap.fromTo(
      targets,
      { opacity: 0, y: 40 },
      {
        opacity: 1,
        y: 0,
        duration,
        ease,
        delay,
        stagger,
        scrollTrigger: {
          trigger: targets,
          start: 'top 85%',
          toggleActions: 'play none none reverse',
        },
      }
    );
  }

  /**
   * Animate section title and subtitle
   */
  function animateSectionTitle(
    titleRef: HTMLElement | string,
    subtitleRef?: HTMLElement | string
  ): void {
    const title = typeof titleRef === 'string' ? document.querySelector(titleRef) : titleRef;
    if (!title) return;

    gsap.fromTo(
      title,
      { opacity: 0, y: 30 },
      {
        opacity: 1,
        y: 0,
        duration: 0.8,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: title,
          start: 'top 80%',
        },
      }
    );

    if (subtitleRef) {
      const subtitle = typeof subtitleRef === 'string' ? document.querySelector(subtitleRef) : subtitleRef;
      if (subtitle) {
        gsap.fromTo(
          subtitle,
          { opacity: 0, y: 20 },
          {
            opacity: 1,
            y: 0,
            duration: 0.6,
            ease: 'power2.out',
            delay: 0.2,
            scrollTrigger: {
              trigger: subtitle,
              start: 'top 80%',
            },
          }
        );
      }
    }
  }

  /**
   * Animate feature cards with staggered entrance
   */
  function animateFeatureCards(containerSelector: string): void {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const cards = container.querySelectorAll('.feature-card');

    gsap.fromTo(
      cards,
      { opacity: 0, y: 50, scale: 0.95 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.6,
        ease: 'back.out(1.2)',
        stagger: 0.15,
        scrollTrigger: {
          trigger: container,
          start: 'top 75%',
        },
      }
    );
  }

  /**
   * Create floating animation for hero elements
   */
  function floatAnimation(element: HTMLElement, config: { duration?: number; y?: number } = {}): gsap.core.Tween {
    const { duration = 3, y = 15 } = config;

    return gsap.to(element, {
      y: -y,
      duration,
      ease: 'sine.inOut',
      repeat: -1,
      yoyo: true,
    });
  }

  /**
   * Animate CTA button with pulse effect
   */
  function pulseButton(button: HTMLElement): void {
    gsap.to(button, {
      boxShadow: '0 0 0 0 rgba(233, 69, 96, 0.4)',
      duration: 1.5,
      ease: 'power1.inOut',
      repeat: -1,
      yoyo: true,
    });
  }

  /**
   * Parallax effect for background elements
   */
  function parallaxEffect(element: HTMLElement, speed: number = 0.5): void {
    gsap.to(element, {
      y: `+=${speed * 100}`,
      ease: 'none',
      scrollTrigger: {
        trigger: element,
        start: 'top bottom',
        end: 'bottom top',
        scrub: true,
      },
    });
  }

  /**
   * Animate numbers counting up
   */
  function countUp(
    element: HTMLElement,
    targetValue: number,
    config: { duration?: number; prefix?: string; suffix?: string } = {}
  ): void {
    const { duration = 2, prefix = '', suffix = '' } = config;

    const counter = { value: 0 };

    gsap.to(counter, {
      value: targetValue,
      duration,
      ease: 'power2.out',
      onUpdate: () => {
        element.textContent = `${prefix}${Math.round(counter.value).toLocaleString()}${suffix}`;
      },
      scrollTrigger: {
        trigger: element,
        start: 'top 80%',
        toggleActions: 'play none none reverse',
      },
    });
  }

  /**
   * Reveal section with scale and fade
   */
  function revealSection(section: HTMLElement, config: AnimationConfig = {}): void {
    const { duration = 0.8, ease = 'power2.out' } = config;

    gsap.fromTo(
      section,
      { opacity: 0, scale: 0.97 },
      {
        opacity: 1,
        scale: 1,
        duration,
        ease,
        scrollTrigger: {
          trigger: section,
          start: 'top 70%',
        },
      }
    );
  }

  return {
    staggerIn,
    animateSectionTitle,
    animateFeatureCards,
    floatAnimation,
    pulseButton,
    parallaxEffect,
    countUp,
    revealSection,
  };
}
