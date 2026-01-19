/**
 * useYardPreferences - Toggle state management for 3D yard view
 *
 * Manages UI preferences for the 3D terminal view:
 * - Stats bar visibility (hidden by default for operators)
 * - Company cards visibility (hidden by default)
 *
 * All preferences are persisted to localStorage for consistency across sessions.
 */

import { ref, watch } from 'vue';

// Storage keys
const STORAGE_KEYS = {
  SHOW_STATS: 'yard_show_stats',
  SHOW_COMPANIES: 'yard_show_companies',
} as const;

// Get stored value or default
function getStoredBoolean(key: string, defaultValue: boolean): boolean {
  const stored = localStorage.getItem(key);
  if (stored === null) return defaultValue;
  return stored === 'true';
}

// Singleton state - shared across all component instances
// This ensures all components using this composable see the same state
const showStatsBar = ref(getStoredBoolean(STORAGE_KEYS.SHOW_STATS, false));
const showCompanyCards = ref(getStoredBoolean(STORAGE_KEYS.SHOW_COMPANIES, false));

// Persist changes to localStorage
watch(showStatsBar, (value) => {
  localStorage.setItem(STORAGE_KEYS.SHOW_STATS, String(value));
});

watch(showCompanyCards, (value) => {
  localStorage.setItem(STORAGE_KEYS.SHOW_COMPANIES, String(value));
});

/**
 * Composable for managing yard view preferences.
 *
 * Default state: Both stats bar and company cards are hidden (Operator Mode).
 * This maximizes 3D canvas space for daily terminal operations.
 *
 * Toggle states:
 * - Stats OFF + Companies OFF = Operator Mode (default, max canvas)
 * - Stats ON + Companies OFF = Quick Overview
 * - Stats ON + Companies ON = Presentation Mode (CEO demos)
 */
export function useYardPreferences() {
  function toggleStatsBar(): void {
    showStatsBar.value = !showStatsBar.value;
  }

  function toggleCompanyCards(): void {
    showCompanyCards.value = !showCompanyCards.value;
  }

  // Reset to defaults (operator mode)
  function resetToDefaults(): void {
    showStatsBar.value = false;
    showCompanyCards.value = false;
  }

  return {
    showStatsBar,
    showCompanyCards,
    toggleStatsBar,
    toggleCompanyCards,
    resetToDefaults,
  };
}
