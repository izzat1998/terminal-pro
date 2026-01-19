import { ref, onMounted, onUnmounted, type Ref } from 'vue';

/**
 * Fullscreen state management composable
 *
 * Provides reactive fullscreen state for immersive UI experiences.
 * ESC key exits fullscreen mode.
 *
 * Note: Fullscreen is auto-triggered by placement mode in ContainerPlacement.vue,
 * so manual toggle shortcuts are not needed.
 */

interface UseFullscreenReturn {
  isFullscreen: Ref<boolean>;
  toggleFullscreen: () => void;
  enterFullscreen: () => void;
  exitFullscreen: () => void;
}

export function useFullscreen(): UseFullscreenReturn {
  const isFullscreen = ref(false);

  function toggleFullscreen(): void {
    isFullscreen.value = !isFullscreen.value;
  }

  function enterFullscreen(): void {
    isFullscreen.value = true;
  }

  function exitFullscreen(): void {
    isFullscreen.value = false;
  }

  function handleKeyDown(event: KeyboardEvent): void {
    // Ignore if typing in an input
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
      return;
    }

    // ESC: Exit fullscreen
    if (event.key === 'Escape' && isFullscreen.value) {
      exitFullscreen();
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown);
  });

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown);
  });

  return {
    isFullscreen,
    toggleFullscreen,
    enterFullscreen,
    exitFullscreen,
  };
}
