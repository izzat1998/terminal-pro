/**
 * Placement Service - API client for 3D terminal placement operations
 */

import { http } from '../utils/httpClient';
import type {
  ApiResponse,
  ApiListResponse,
  ContainerPositionRecord,
  PlacementLayout,
  Position,
  SuggestionResponse,
  UnplacedContainer,
  ZoneCode,
} from '../types/placement';

const BASE_URL = '/terminal/placement';

// Backend error code to user-friendly message mapping
const ERROR_MESSAGE_MAP: Record<string, string> = {
  // Placement validation errors
  POSITION_OCCUPIED: 'Эта позиция уже занята',
  NO_SUPPORT: 'Нет контейнера ниже для поддержки',
  SIZE_INCOMPATIBILITY: 'Размеры контейнеров несовместимы (40ft нельзя ставить на 20ft)',
  WEIGHT_DISTRIBUTION_VIOLATION: 'Гружёный контейнер нельзя ставить на порожний',

  // Container state errors
  ALREADY_PLACED: 'Контейнер уже размещён на терминале',
  CONTAINER_ENTRY_NOT_FOUND: 'Контейнер не найден',

  // Position errors
  POSITION_NOT_FOUND: 'Позиция не найдена',
  INVALID_ZONE: 'Недопустимая зона',
  INVALID_ROW: 'Недопустимый ряд',
  INVALID_BAY: 'Недопустимый отсек',
  INVALID_TIER: 'Недопустимый ярус',

  // General errors
  NO_AVAILABLE_POSITIONS: 'Нет свободных позиций на терминале',
};

/**
 * Parse backend error response and return user-friendly message
 */
export function parsePlacementError(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { data?: { error?: { code?: string; message?: string } } } };
    const errorData = axiosError.response?.data?.error;

    if (errorData?.code && ERROR_MESSAGE_MAP[errorData.code]) {
      return ERROR_MESSAGE_MAP[errorData.code]!;
    }

    if (errorData?.message) {
      return errorData.message;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Произошла неизвестная ошибка';
}

/**
 * Get complete terminal layout for 3D visualization.
 * Returns all zones, dimensions, positioned containers, and statistics.
 */
export async function getLayout(): Promise<PlacementLayout> {
  const response = await http.get<ApiResponse<PlacementLayout>>(`${BASE_URL}/layout/`);
  return response.data;
}

/**
 * Auto-suggest optimal position for a container.
 * @param containerEntryId - Container entry ID to place
 * @param zonePreference - Optional preferred zone
 */
export async function suggestPosition(
  containerEntryId: number,
  zonePreference?: ZoneCode
): Promise<SuggestionResponse> {
  const response = await http.post<ApiResponse<SuggestionResponse>>(
    `${BASE_URL}/suggest/`,
    {
      container_entry_id: containerEntryId,
      zone_preference: zonePreference,
    }
  );
  return response.data;
}

/**
 * Assign container to a specific position.
 * @param containerEntryId - Container entry ID to place
 * @param position - Target position coordinates
 */
export async function assignPosition(
  containerEntryId: number,
  position: Omit<Position, 'coordinate'>
): Promise<ContainerPositionRecord> {
  const response = await http.post<ApiResponse<ContainerPositionRecord>>(
    `${BASE_URL}/assign/`,
    {
      container_entry_id: containerEntryId,
      position,
    }
  );
  return response.data;
}

/**
 * Move container to a new position.
 * @param positionId - Current position ID
 * @param newPosition - New position coordinates
 */
export async function moveContainer(
  positionId: number,
  newPosition: Omit<Position, 'coordinate'>
): Promise<ContainerPositionRecord> {
  const response = await http.patch<ApiResponse<ContainerPositionRecord>>(
    `${BASE_URL}/${positionId}/move/`,
    { new_position: newPosition }
  );
  return response.data;
}

/**
 * Remove container from its position.
 * @param positionId - Position ID to remove
 */
export async function removePosition(positionId: number): Promise<void> {
  await http.delete(`${BASE_URL}/${positionId}/remove/`);
}

/**
 * Get available positions with optional filters.
 * @param zone - Filter by zone (optional)
 * @param tier - Filter by tier (optional)
 * @param limit - Max positions to return (default 50)
 */
export async function getAvailablePositions(
  zone?: ZoneCode,
  tier?: number,
  limit: number = 50
): Promise<Position[]> {
  const params = new URLSearchParams();
  if (zone) params.append('zone', zone);
  if (tier) params.append('tier', tier.toString());
  params.append('limit', limit.toString());

  const response = await http.get<ApiListResponse<Position>>(
    `${BASE_URL}/available/?${params.toString()}`
  );
  return response.data;
}

/**
 * Get containers without assigned positions.
 * These need to be placed via the assign endpoint.
 */
export async function getUnplacedContainers(): Promise<UnplacedContainer[]> {
  const response = await http.get<ApiListResponse<UnplacedContainer>>(
    `${BASE_URL}/unplaced/`
  );
  return response.data;
}

// Export all functions as a service object
export const placementService = {
  getLayout,
  suggestPosition,
  assignPosition,
  moveContainer,
  removePosition,
  getAvailablePositions,
  getUnplacedContainers,
};
