import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useCrudTable } from '../useCrudTable';
import { http } from '../../utils/httpClient';
import type { PaginatedResponse } from '../../types/api';
import { message } from 'ant-design-vue';

// Mock modules
vi.mock('../../utils/httpClient');
vi.mock('ant-design-vue', () => ({
  message: {
    error: vi.fn(),
  },
}));

describe('useCrudTable', () => {
  interface MockApiItem {
    id: number;
    name: string;
    email: string;
  }

  interface MockTableRecord {
    key: string;
    id: number;
    name: string;
    email: string;
  }

  const mockApiItems: MockApiItem[] = [
    { id: 1, name: 'User 1', email: 'user1@example.com' },
    { id: 2, name: 'User 2', email: 'user2@example.com' },
  ];

  const transformItem = (item: MockApiItem): MockTableRecord => ({
    key: item.id.toString(),
    id: item.id,
    name: item.name,
    email: item.email,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchData', () => {
    it('should fetch and transform paginated data', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 2,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem);

      // Act
      await table.fetchData();

      // Assert
      expect(table.dataSource.value).toHaveLength(2);
      expect(table.dataSource.value[0]?.key).toBe('1');
      expect(table.dataSource.value[0]?.name).toBe('User 1');
      expect(table.pagination.value.total).toBe(2);
      expect(table.loading.value).toBe(false);
    });

    it('should handle non-paginated array response', async () => {
      // Arrange
      vi.mocked(http.get).mockResolvedValue(mockApiItems);

      const table = useCrudTable('/api/users/', transformItem);

      // Act
      await table.fetchData();

      // Assert
      expect(table.dataSource.value).toHaveLength(2);
      expect(table.pagination.value.total).toBe(2);
    });

    it('should include search parameter when search is enabled and has value', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 1,
        next: null,
        previous: null,
        results: [mockApiItems[0]!],
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem, {
        searchEnabled: true,
      });

      table.searchText.value = 'User 1';

      // Act
      await table.fetchData();

      // Assert
      expect(http.get).toHaveBeenCalledWith(
        expect.stringContaining('search=User+1')
      );
    });

    it('should use custom search parameter name', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 1,
        next: null,
        previous: null,
        results: [mockApiItems[0]!],
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem, {
        searchEnabled: true,
        searchParamName: 'q',
      });

      table.searchText.value = 'test';

      // Act
      await table.fetchData();

      // Assert
      expect(http.get).toHaveBeenCalledWith(
        expect.stringContaining('q=test')
      );
    });

    it('should not include search parameter when search text is empty', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 2,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem, {
        searchEnabled: true,
      });

      table.searchText.value = '   '; // Whitespace only

      // Act
      await table.fetchData();

      // Assert
      expect(http.get).toHaveBeenCalledWith(
        expect.not.stringContaining('search=')
      );
    });

    it('should handle fetch error', async () => {
      // Arrange
      vi.mocked(http.get).mockRejectedValue(new Error('Network error'));

      const table = useCrudTable('/api/users/', transformItem);

      // Act
      await table.fetchData();

      // Assert
      expect(message.error).toHaveBeenCalledWith('Network error');
      expect(table.loading.value).toBe(false);
    });

    it('should use custom error message on failure', async () => {
      // Arrange
      vi.mocked(http.get).mockRejectedValue(new Error('Network error'));

      const table = useCrudTable('/api/users/', transformItem, {
        errorMessage: 'Custom error message',
      });

      // Act
      await table.fetchData();

      // Assert
      expect(message.error).toHaveBeenCalledWith('Network error');
    });

    it('should set loading state during fetch', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 2,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      vi.mocked(http.get).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockResponse), 100))
      );

      const table = useCrudTable('/api/users/', transformItem);

      // Act
      const fetchPromise = table.fetchData();
      expect(table.loading.value).toBe(true);

      await fetchPromise;

      // Assert
      expect(table.loading.value).toBe(false);
    });
  });

  describe('pagination', () => {
    it('should use default page size', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 2,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem);

      // Act
      await table.fetchData();

      // Assert
      expect(table.pagination.value.pageSize).toBe(25);
    });

    it('should use custom default page size', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 2,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem, {
        defaultPageSize: 50,
      });

      // Act
      await table.fetchData();

      // Assert
      expect(table.pagination.value.pageSize).toBe(50);
    });

    it('should handle page change', async () => {
      // Arrange
      const page1Response: PaginatedResponse<MockApiItem> = {
        count: 50,
        next: 'page2',
        previous: null,
        results: mockApiItems,
      };

      const page2Response: PaginatedResponse<MockApiItem> = {
        count: 50,
        next: null,
        previous: 'page1',
        results: [{ id: 3, name: 'User 3', email: 'user3@example.com' }],
      };

      vi.mocked(http.get)
        .mockResolvedValueOnce(page1Response)
        .mockResolvedValueOnce(page2Response);

      const table = useCrudTable('/api/users/', transformItem);

      await table.fetchData();

      // Act
      table.handleTableChange({ current: 2, pageSize: 25 });
      await vi.waitFor(() => expect(http.get).toHaveBeenCalledTimes(2));

      // Assert
      expect(http.get).toHaveBeenLastCalledWith(
        expect.stringContaining('page=2')
      );
    });

    it('should handle page size change', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 100,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      vi.mocked(http.get)
        .mockResolvedValueOnce(mockResponse)
        .mockResolvedValueOnce(mockResponse);

      const table = useCrudTable('/api/users/', transformItem);

      await table.fetchData();

      // Act
      table.handleTableChange({ current: 1, pageSize: 50 });
      await vi.waitFor(() => expect(http.get).toHaveBeenCalledTimes(2));

      // Assert
      expect(http.get).toHaveBeenLastCalledWith(
        expect.stringContaining('page_size=50')
      );
    });
  });

  describe('handleSearch', () => {
    it('should reset to page 1 when searching', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 1,
        next: null,
        previous: null,
        results: [mockApiItems[0]!],
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem, {
        searchEnabled: true,
      });

      // Set to page 2 first
      table.pagination.value.current = 2;
      table.searchText.value = 'User 1';

      // Act
      await table.handleSearch();

      // Assert
      expect(http.get).toHaveBeenCalledWith(
        expect.stringContaining('page=1')
      );
      expect(table.pagination.value.current).toBe(1);
    });
  });

  describe('refresh', () => {
    it('should refresh current page', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 50,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem);

      // Set to page 2
      table.pagination.value.current = 2;

      // Act
      await table.refresh();

      // Assert
      expect(http.get).toHaveBeenCalledWith(
        expect.stringContaining('page=2')
      );
    });
  });

  describe('refreshAfterDelete', () => {
    it('should stay on current page when not last item', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 2,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem);

      await table.fetchData();
      table.pagination.value.current = 2;

      // Act
      await table.refreshAfterDelete();

      // Assert
      expect(http.get).toHaveBeenLastCalledWith(
        expect.stringContaining('page=2')
      );
    });

    it('should go to previous page when deleting last item on page', async () => {
      // Arrange
      const mockResponse1: PaginatedResponse<MockApiItem> = {
        count: 26,
        next: null,
        previous: null,
        results: mockApiItems,
      };

      const mockResponse2: PaginatedResponse<MockApiItem> = {
        count: 25,
        next: null,
        previous: null,
        results: [mockApiItems[0]!],
      };

      vi.mocked(http.get)
        .mockResolvedValueOnce(mockResponse1)
        .mockResolvedValueOnce(mockResponse2);

      const table = useCrudTable('/api/users/', transformItem);

      await table.fetchData();

      // Simulate being on page 2 with only 1 item
      table.pagination.value.current = 2;
      table.dataSource.value = [transformItem(mockApiItems[0]!)];

      // Act
      await table.refreshAfterDelete();

      // Assert
      expect(http.get).toHaveBeenLastCalledWith(
        expect.stringContaining('page=1')
      );
    });

    it('should not go to previous page when on page 1', async () => {
      // Arrange
      const mockResponse: PaginatedResponse<MockApiItem> = {
        count: 1,
        next: null,
        previous: null,
        results: [mockApiItems[0]!],
      };

      vi.mocked(http.get).mockResolvedValue(mockResponse);

      const table = useCrudTable('/api/users/', transformItem);

      await table.fetchData();
      table.dataSource.value = [transformItem(mockApiItems[0]!)];

      // Act
      await table.refreshAfterDelete();

      // Assert
      expect(http.get).toHaveBeenLastCalledWith(
        expect.stringContaining('page=1')
      );
    });
  });

  describe('pagination configuration', () => {
    it('should use custom page size options', () => {
      // Arrange
      const customOptions = ['5', '10', '20'];

      const table = useCrudTable('/api/users/', transformItem, {
        pageSizeOptions: customOptions,
      });

      // Assert
      expect(table.pagination.value.pageSizeOptions).toEqual(customOptions);
    });

    it('should enable size changer', () => {
      // Arrange
      const table = useCrudTable('/api/users/', transformItem);

      // Assert
      expect(table.pagination.value.showSizeChanger).toBe(true);
    });
  });
});
