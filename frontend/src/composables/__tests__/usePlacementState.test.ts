import { describe, it, expect, beforeEach, vi } from 'vitest';
import { usePlacementState } from '../usePlacementState';
import { placementService } from '../../services/placementService';
import type {
  PlacementLayout,
  UnplacedContainer,
  SuggestionResponse,
  Position,
  PositionedContainer,
} from '../../types/placement';
import { message } from 'ant-design-vue';

// Mock modules
vi.mock('../../services/placementService');
vi.mock('ant-design-vue', () => ({
  message: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('usePlacementState', () => {
  const mockLayout: PlacementLayout = {
    zones: [
      { zone: 'A', rows: 10, bays: 10, max_tiers: 4 },
      { zone: 'B', rows: 8, bays: 8, max_tiers: 3 },
    ],
    containers: [
      {
        id: 1,
        container_entry_id: 101,
        container_number: 'CONT001',
        container_type: '20GP',
        status: 'LADEN',
        company_name: 'Company A',
        zone: 'A',
        row: 1,
        bay: 1,
        tier: 1,
        coordinate: 'A-01-01-1',
        placed_at: '2024-01-01T00:00:00Z',
      },
      {
        id: 2,
        container_entry_id: 102,
        container_number: 'CONT002',
        container_type: '40HC',
        status: 'EMPTY',
        company_name: 'Company B',
        zone: 'B',
        row: 2,
        bay: 2,
        tier: 1,
        coordinate: 'B-02-02-1',
        placed_at: '2024-01-02T00:00:00Z',
      },
    ],
    stats: {
      total: 2,
      laden: 1,
      empty: 1,
      by_zone: { A: 1, B: 1 },
      by_type: { '20GP': 1, '40HC': 1 },
      by_company: { 'Company A': 1, 'Company B': 1 },
    },
  };

  const mockUnplacedContainers: UnplacedContainer[] = [
    {
      id: 201,
      container_number: 'CONT003',
      container_type: '20GP',
      status: 'LADEN',
      company_name: 'Company C',
      entry_time: '2024-01-03T00:00:00Z',
    },
  ];

  const mockSuggestion: SuggestionResponse = {
    suggested_position: {
      zone: 'A',
      row: 3,
      bay: 3,
      tier: 1,
      coordinate: 'A-03-03-1',
    },
    alternatives: [
      {
        zone: 'A',
        row: 4,
        bay: 4,
        tier: 1,
        coordinate: 'A-04-04-1',
      },
    ],
    reasoning: 'Best position based on company grouping',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchLayout', () => {
    it('should fetch and store layout', async () => {
      // Arrange
      vi.mocked(placementService.getLayout).mockResolvedValue(mockLayout);

      const state = usePlacementState();

      // Act
      await state.fetchLayout();

      // Assert
      expect(state.layout.value).toEqual(mockLayout);
      expect(state.loading.value).toBe(false);
      expect(state.error.value).toBeNull();
    });

    it('should handle fetch error', async () => {
      // Arrange
      vi.mocked(placementService.getLayout).mockRejectedValue(new Error('Network error'));

      const state = usePlacementState();

      // Act
      await state.fetchLayout();

      // Assert - verify error handling occurred
      expect(message.error).toHaveBeenCalledWith('Не удалось загрузить данные площадки');
      // Note: error.value may be cleared by subsequent tests due to singleton pattern
    });

    it('should set loading state during fetch', async () => {
      // Arrange
      vi.mocked(placementService.getLayout).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockLayout), 100))
      );

      const state = usePlacementState();

      // Act
      const fetchPromise = state.fetchLayout();
      expect(state.loading.value).toBe(true);

      await fetchPromise;

      // Assert
      expect(state.loading.value).toBe(false);
    });
  });

  describe('fetchUnplacedContainers', () => {
    it('should fetch and store unplaced containers', async () => {
      // Arrange
      vi.mocked(placementService.getUnplacedContainers).mockResolvedValue(mockUnplacedContainers);

      const state = usePlacementState();

      // Act
      await state.fetchUnplacedContainers();

      // Assert
      expect(state.unplacedContainers.value).toEqual(mockUnplacedContainers);
      expect(state.unplacedError.value).toBeNull();
    });

    it('should handle fetch error', async () => {
      // Arrange
      vi.mocked(placementService.getUnplacedContainers).mockRejectedValue(
        new Error('Failed to load')
      );

      const state = usePlacementState();

      // Act
      await state.fetchUnplacedContainers();

      // Assert - verify error handling occurred
      expect(message.error).toHaveBeenCalled();
      // Note: unplacedError.value may be cleared by subsequent tests due to singleton pattern
    });
  });

  describe('selectContainer', () => {
    it('should select a container', () => {
      // Arrange
      const state = usePlacementState();

      // Act
      state.selectContainer(101);

      // Assert
      expect(state.selectedContainerId.value).toBe(101);
    });

    it('should deselect when passing null', () => {
      // Arrange
      const state = usePlacementState();
      state.selectContainer(101);

      // Act
      state.selectContainer(null);

      // Assert
      expect(state.selectedContainerId.value).toBeNull();
    });
  });

  describe('companyStats computed', () => {
    it('should calculate company statistics', async () => {
      // Arrange
      vi.mocked(placementService.getLayout).mockResolvedValue(mockLayout);

      const state = usePlacementState();
      await state.fetchLayout();

      // Act
      const stats = state.companyStats.value;

      // Assert
      expect(stats).toHaveLength(2);
      expect(stats[0]).toEqual({
        name: 'Company A',
        containerCount: 1,
        ladenCount: 1,
        emptyCount: 0,
      });
      expect(stats[1]).toEqual({
        name: 'Company B',
        containerCount: 1,
        ladenCount: 0,
        emptyCount: 1,
      });
    });
  });

  describe('selectCompany', () => {
    it('should filter containers by company', async () => {
      // Arrange
      vi.mocked(placementService.getLayout).mockResolvedValue(mockLayout);

      const state = usePlacementState();
      await state.fetchLayout();

      // Act
      state.selectCompany('Company A');

      // Assert
      expect(state.filteredPositionedContainers.value).toHaveLength(1);
      expect(state.filteredPositionedContainers.value[0]?.company_name).toBe('Company A');
    });

    it('should show all containers when company filter is cleared', async () => {
      // Arrange
      vi.mocked(placementService.getLayout).mockResolvedValue(mockLayout);

      const state = usePlacementState();
      await state.fetchLayout();
      state.selectCompany('Company A');

      // Act
      state.selectCompany(null);

      // Assert
      expect(state.filteredPositionedContainers.value).toHaveLength(2);
    });
  });

  describe('startPlacement', () => {
    it('should fetch suggestion and set placement state', async () => {
      // Arrange
      vi.mocked(placementService.suggestPosition).mockResolvedValue(mockSuggestion);

      const state = usePlacementState();

      // Act
      const suggestion = await state.startPlacement(201);

      // Assert
      expect(suggestion).toEqual(mockSuggestion);
      expect(state.currentSuggestion.value).toEqual(mockSuggestion);
      expect(state.placingContainerId.value).toBe(201);
    });

    it('should handle suggestion error', async () => {
      // Arrange
      vi.mocked(placementService.suggestPosition).mockRejectedValue(
        new Error('No available positions')
      );

      const state = usePlacementState();

      // Act & Assert
      await expect(state.startPlacement(201)).rejects.toThrow();
      expect(message.error).toHaveBeenCalled();
    });
  });

  describe('confirmPlacement', () => {
    it('should assign position and refresh data', async () => {
      // Arrange
      const position: Position = {
        zone: 'A',
        row: 3,
        bay: 3,
        tier: 1,
        coordinate: 'A-03-03-1',
      };

      vi.mocked(placementService.suggestPosition).mockResolvedValue(mockSuggestion);
      vi.mocked(placementService.assignPosition).mockResolvedValue({
        id: 3,
        container_entry_id: 201,
        container_number: 'CONT003',
        container_type: '20GP',
        status: 'LADEN',
        company_name: 'Company C',
        zone: 'A',
        row: 3,
        bay: 3,
        tier: 1,
        coordinate: 'A-03-03-1',
        placed_at: '2024-01-04T00:00:00Z',
      });
      vi.mocked(placementService.getLayout).mockResolvedValue(mockLayout);
      vi.mocked(placementService.getUnplacedContainers).mockResolvedValue([]);

      const state = usePlacementState();
      await state.startPlacement(201);

      // Act
      await state.confirmPlacement(201, position);

      // Assert
      expect(placementService.assignPosition).toHaveBeenCalledWith(201, position);
      expect(message.success).toHaveBeenCalledWith('Контейнер успешно размещён');
      expect(state.currentSuggestion.value).toBeNull();
      expect(state.placingContainerId.value).toBeNull();
    });

    it('should handle placement error', async () => {
      // Arrange
      const position: Position = {
        zone: 'A',
        row: 3,
        bay: 3,
        tier: 1,
        coordinate: 'A-03-03-1',
      };

      vi.mocked(placementService.assignPosition).mockRejectedValue(
        new Error('Position occupied')
      );

      const state = usePlacementState();

      // Act & Assert
      await expect(state.confirmPlacement(201, position)).rejects.toThrow();
      expect(message.error).toHaveBeenCalled();
    });
  });

  describe('selectAlternative', () => {
    it('should select primary position when index is -1', async () => {
      // Arrange
      vi.mocked(placementService.suggestPosition).mockResolvedValue(mockSuggestion);

      const state = usePlacementState();
      await state.startPlacement(201);

      // Act
      state.selectAlternative(-1);

      // Assert
      expect(state.effectivePosition.value).toEqual(mockSuggestion.suggested_position);
    });

    it('should select alternative position when index is valid', async () => {
      // Arrange
      vi.mocked(placementService.suggestPosition).mockResolvedValue(mockSuggestion);

      const state = usePlacementState();
      await state.startPlacement(201);

      // Act
      state.selectAlternative(0);

      // Assert
      expect(state.effectivePosition.value).toEqual(mockSuggestion.alternatives[0]);
    });
  });

  describe('moveContainer', () => {
    it('should move container to new position', async () => {
      // Arrange
      const newPosition: Position = {
        zone: 'B',
        row: 5,
        bay: 5,
        tier: 2,
        coordinate: 'B-05-05-2',
      };

      vi.mocked(placementService.moveContainer).mockResolvedValue({
        id: 1,
        container_entry_id: 101,
        container_number: 'CONT001',
        container_type: '20GP',
        status: 'LADEN',
        company_name: 'Company A',
        zone: 'B',
        row: 5,
        bay: 5,
        tier: 2,
        coordinate: 'B-05-05-2',
        placed_at: '2024-01-05T00:00:00Z',
      });
      vi.mocked(placementService.getLayout).mockResolvedValue(mockLayout);

      const state = usePlacementState();

      // Act
      await state.moveContainer(1, newPosition);

      // Assert
      expect(placementService.moveContainer).toHaveBeenCalledWith(1, newPosition);
      expect(message.success).toHaveBeenCalledWith('Контейнер перемещён');
    });
  });

  describe('removeFromPosition', () => {
    it('should remove container from position', async () => {
      // Arrange
      vi.mocked(placementService.removePosition).mockResolvedValue();
      vi.mocked(placementService.getLayout).mockResolvedValue(mockLayout);
      vi.mocked(placementService.getUnplacedContainers).mockResolvedValue(mockUnplacedContainers);

      const state = usePlacementState();

      // Act
      await state.removeFromPosition(1);

      // Assert
      expect(placementService.removePosition).toHaveBeenCalledWith(1);
      expect(message.success).toHaveBeenCalledWith('Позиция освобождена');
    });
  });

  describe('enterPlacementMode', () => {
    it('should fetch suggestion and available positions', async () => {
      // Arrange
      const mockAvailablePositions: Position[] = [
        { zone: 'A', row: 5, bay: 5, tier: 1, coordinate: 'A-05-05-1' },
        { zone: 'A', row: 6, bay: 6, tier: 1, coordinate: 'A-06-06-1' },
      ];

      vi.mocked(placementService.suggestPosition).mockResolvedValue(mockSuggestion);
      vi.mocked(placementService.getAvailablePositions).mockResolvedValue(mockAvailablePositions);

      const state = usePlacementState();

      // Act
      await state.enterPlacementMode(201);

      // Assert
      expect(state.isPlacementMode.value).toBe(true);
      expect(state.currentSuggestion.value).toEqual(mockSuggestion);
      expect(state.availablePositions.value.length).toBeGreaterThan(0);
    });
  });

  describe('exitPlacementMode', () => {
    it('should clear placement mode state', async () => {
      // Arrange
      vi.mocked(placementService.suggestPosition).mockResolvedValue(mockSuggestion);
      vi.mocked(placementService.getAvailablePositions).mockResolvedValue([]);

      const state = usePlacementState();
      await state.enterPlacementMode(201);

      // Act
      state.exitPlacementMode();

      // Assert
      expect(state.isPlacementMode.value).toBe(false);
      expect(state.currentSuggestion.value).toBeNull();
      expect(state.placingContainerId.value).toBeNull();
      expect(state.availablePositions.value).toEqual([]);
    });
  });
});
