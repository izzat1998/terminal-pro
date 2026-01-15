/**
 * Composable for shared placement state management.
 * Handles bi-directional sync between table and 3D view.
 */

import { ref, computed } from 'vue';
import { message } from 'ant-design-vue';
import { placementService, parsePlacementError } from '../services/placementService';
import { NO_COMPANY_LABEL } from '../constants/containerTypes';
import type {
  PlacementLayout,
  UnplacedContainer,
  SuggestionResponse,
  Position,
  ZoneCode,
  CompanyStats,
} from '../types/placement';

function getErrorMessage(e: unknown, fallback: string): string {
  // Try to parse placement-specific error first
  const parsed = parsePlacementError(e);
  if (parsed !== 'Произошла неизвестная ошибка') {
    return parsed;
  }
  return e instanceof Error ? e.message : fallback;
}

// Shared state (singleton pattern)
const layout = ref<PlacementLayout | null>(null);
const unplacedContainers = ref<UnplacedContainer[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const unplacedError = ref<string | null>(null);

// Selection state for bi-directional sync
const selectedContainerId = ref<number | null>(null);
const hoveredContainerId = ref<number | null>(null);

// Current suggestion (when placing a container)
const currentSuggestion = ref<SuggestionResponse | null>(null);
const placingContainerId = ref<number | null>(null);

// Company filtering state
const selectedCompanyName = ref<string | null>(null);

export function usePlacementState() {
  // Computed: containers currently on terminal with positions
  const positionedContainers = computed(() => layout.value?.containers ?? []);

  // Computed: total statistics
  const stats = computed(() => layout.value?.stats ?? null);

  // Computed: selected container data
  const selectedContainer = computed(() => {
    if (!selectedContainerId.value) return null;
    return positionedContainers.value.find(c => c.id === selectedContainerId.value) ?? null;
  });

  // Computed: company statistics derived from positioned containers
  const companyStats = computed<CompanyStats[]>(() => {
    const statsMap = new Map<string, CompanyStats>();

    for (const container of positionedContainers.value) {
      const name = container.company_name || NO_COMPANY_LABEL;
      if (!statsMap.has(name)) {
        statsMap.set(name, { name, containerCount: 0, ladenCount: 0, emptyCount: 0 });
      }
      const stats = statsMap.get(name)!;
      stats.containerCount++;
      if (container.status === 'LADEN') {
        stats.ladenCount++;
      } else {
        stats.emptyCount++;
      }
    }

    // Sort by container count descending
    return Array.from(statsMap.values()).sort((a, b) => b.containerCount - a.containerCount);
  });

  // Computed: filtered containers by selected company (for table view)
  const filteredPositionedContainers = computed(() => {
    if (!selectedCompanyName.value) return positionedContainers.value;
    return positionedContainers.value.filter(
      c => (c.company_name || NO_COMPANY_LABEL) === selectedCompanyName.value
    );
  });

  // Computed: filtered unplaced containers by selected company
  const filteredUnplacedContainers = computed(() => {
    if (!selectedCompanyName.value) return unplacedContainers.value;
    return unplacedContainers.value.filter(
      c => (c.company_name || NO_COMPANY_LABEL) === selectedCompanyName.value
    );
  });

  /**
   * Select company for filtering
   */
  function selectCompany(name: string | null): void {
    selectedCompanyName.value = name;
  }

  /**
   * Fetch complete terminal layout from API
   */
  async function fetchLayout(): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      layout.value = await placementService.getLayout();
    } catch (e) {
      error.value = getErrorMessage(e, 'Failed to load terminal layout');
      message.error('Не удалось загрузить данные площадки');
    } finally {
      loading.value = false;
    }
  }

  /**
   * Fetch containers without positions
   */
  async function fetchUnplacedContainers(): Promise<void> {
    unplacedError.value = null;
    try {
      unplacedContainers.value = await placementService.getUnplacedContainers();
    } catch (e) {
      const errorMsg = getErrorMessage(e, 'Не удалось загрузить неразмещённые контейнеры');
      unplacedError.value = errorMsg;
      message.error(errorMsg);
    }
  }

  /**
   * Refresh all placement data
   */
  async function refreshAll(): Promise<void> {
    await Promise.all([fetchLayout(), fetchUnplacedContainers()]);
  }

  /**
   * Select a container (from table or 3D view)
   */
  function selectContainer(containerId: number | null): void {
    selectedContainerId.value = containerId;
  }

  /**
   * Set hovered container (for highlighting)
   */
  function setHoveredContainer(containerId: number | null): void {
    hoveredContainerId.value = containerId;
  }

  /**
   * Start placement workflow for a container
   */
  async function startPlacement(containerEntryId: number, zonePreference?: ZoneCode): Promise<SuggestionResponse> {
    loading.value = true;
    placingContainerId.value = containerEntryId;

    try {
      const suggestion = await placementService.suggestPosition(containerEntryId, zonePreference);
      currentSuggestion.value = suggestion;
      return suggestion;
    } catch (e) {
      message.error(getErrorMessage(e, 'Не удалось получить рекомендацию'));
      throw e;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Confirm placement at suggested or custom position
   */
  async function confirmPlacement(containerEntryId: number, position: Position): Promise<void> {
    loading.value = true;

    try {
      await placementService.assignPosition(containerEntryId, position);
      message.success('Контейнер успешно размещён');

      // Clear placement state
      currentSuggestion.value = null;
      placingContainerId.value = null;

      // Refresh data
      await refreshAll();
    } catch (e) {
      message.error(getErrorMessage(e, 'Не удалось разместить контейнер'));
      throw e;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Cancel current placement workflow
   */
  function cancelPlacement(): void {
    currentSuggestion.value = null;
    placingContainerId.value = null;
  }

  /**
   * Move container to new position
   */
  async function moveContainer(positionId: number, newPosition: Position): Promise<void> {
    loading.value = true;

    try {
      await placementService.moveContainer(positionId, newPosition);
      message.success('Контейнер перемещён');
      await fetchLayout();
    } catch (e) {
      message.error(getErrorMessage(e, 'Не удалось переместить контейнер'));
      throw e;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Remove container from position
   */
  async function removeFromPosition(positionId: number): Promise<void> {
    loading.value = true;

    try {
      await placementService.removePosition(positionId);
      message.success('Позиция освобождена');
      await refreshAll();
    } catch (e) {
      message.error(getErrorMessage(e, 'Не удалось освободить позицию'));
      throw e;
    } finally {
      loading.value = false;
    }
  }

  return {
    // State
    layout,
    unplacedContainers,
    unplacedError,
    loading,
    error,
    selectedContainerId,
    hoveredContainerId,
    currentSuggestion,
    placingContainerId,
    selectedCompanyName,

    // Computed
    positionedContainers,
    stats,
    selectedContainer,
    companyStats,
    filteredPositionedContainers,
    filteredUnplacedContainers,

    // Actions
    fetchLayout,
    fetchUnplacedContainers,
    refreshAll,
    selectContainer,
    setHoveredContainer,
    selectCompany,
    startPlacement,
    confirmPlacement,
    cancelPlacement,
    moveContainer,
    removeFromPosition,
  };
}
