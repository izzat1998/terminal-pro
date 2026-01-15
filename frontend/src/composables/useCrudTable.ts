import { ref } from 'vue';
import { message } from 'ant-design-vue';
import { http } from '../utils/httpClient';
import type { PaginatedResponse } from '../types/api';

interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
  showSizeChanger: boolean;
  pageSizeOptions: string[];
}

interface TablePaginationEvent {
  current: number;
  pageSize: number;
}

interface UseCrudTableOptions {
  defaultPageSize?: number;
  pageSizeOptions?: string[];
  errorMessage?: string;
  /** Enable search functionality */
  searchEnabled?: boolean;
  /** Query param name for search (default: 'search') */
  searchParamName?: string;
}

/**
 * Composable for managing paginated table data with CRUD operations.
 *
 * @template T - The API response item type
 * @template R - The table record type (with key field)
 *
 * @param endpoint - API endpoint (e.g., '/auth/managers/')
 * @param transform - Function to transform API items to table records
 * @param options - Optional configuration
 */
export function useCrudTable<T, R extends { key: string }>(
  endpoint: string,
  transform: (item: T) => R,
  options: UseCrudTableOptions = {}
) {
  const {
    defaultPageSize = 25,
    pageSizeOptions = ['10', '25', '50', '100'],
    errorMessage = 'Не удалось загрузить данные. Проверьте подключение к сети или попробуйте позже.',
    searchEnabled = false,
    searchParamName = 'search',
  } = options;

  const dataSource = ref<R[]>([]);
  const loading = ref(false);
  const searchText = ref('');
  const pagination = ref<PaginationState>({
    current: 1,
    pageSize: defaultPageSize,
    total: 0,
    showSizeChanger: true,
    pageSizeOptions,
  });

  const fetchData = async (page?: number, pageSize?: number) => {
    try {
      loading.value = true;

      const currentPage = page ?? pagination.value.current;
      const currentPageSize = pageSize ?? pagination.value.pageSize;

      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('page_size', currentPageSize.toString());

      // Add search param if enabled and has value
      if (searchEnabled && searchText.value.trim()) {
        params.append(searchParamName, searchText.value.trim());
      }

      const data = await http.get<PaginatedResponse<T> | T[]>(`${endpoint}?${params.toString()}`);

      // Handle both paginated and non-paginated responses
      if (Array.isArray(data)) {
        dataSource.value = data.map(transform) as R[];
        pagination.value.total = data.length;
      } else if (data && 'results' in data) {
        dataSource.value = data.results.map(transform) as R[];
        pagination.value.total = data.count;
      }

      pagination.value.current = currentPage;
      pagination.value.pageSize = currentPageSize;
    } catch (error) {
      message.error(error instanceof Error ? error.message : errorMessage);
    } finally {
      loading.value = false;
    }
  };

  const handleTableChange = (pag: TablePaginationEvent) => {
    fetchData(pag.current, pag.pageSize);
  };

  const refresh = () => {
    fetchData(pagination.value.current, pagination.value.pageSize);
  };

  /**
   * Handle search - resets to page 1 and fetches data
   */
  const handleSearch = () => {
    fetchData(1, pagination.value.pageSize);
  };

  /**
   * Refresh after deleting an item.
   * Handles the edge case of deleting the last item on a page.
   */
  const refreshAfterDelete = () => {
    const isLastItemOnPage = dataSource.value.length === 1 && pagination.value.current > 1;
    const newPage = isLastItemOnPage ? pagination.value.current - 1 : pagination.value.current;
    fetchData(newPage, pagination.value.pageSize);
  };

  return {
    dataSource,
    loading,
    pagination,
    searchText,
    fetchData,
    handleTableChange,
    handleSearch,
    refresh,
    refreshAfterDelete,
  };
}
