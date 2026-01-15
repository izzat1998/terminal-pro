/**
 * Vehicle Excel export service
 * Handles exporting vehicle data to Excel format
 */

import * as XLSX from 'xlsx';
import dayjs from 'dayjs';
import { http } from '../utils/httpClient';
import { formatDateTime } from '../utils/dateFormat';
import type { Vehicle } from '../types/vehicle';

/** Filter parameters for export */
export interface ExportFilters {
  vehicleType?: string;
  status?: string;
  searchText?: string;
  dateRange?: [dayjs.Dayjs, dayjs.Dayjs] | null;
}

/** Excel row data structure */
interface ExcelRow {
  '№': number;
  'Гос. номер': string;
  'Статус': string;
  'Клиент': string;
  'Телефон клиента': string;
  'Тип ТС': string;
  'Время въезда': string;
  'Тип транспорта': string;
  'Статус загрузки въезд': string;
  'Тип груза': string;
  'Время выезда': string;
  'Статус загрузки выезд': string;
  'Время пребывания (ч)': string;
}

/**
 * Export vehicles to Excel file
 *
 * @param filters - Optional filters to apply to export
 * @returns Number of exported records
 * @throws Error if export fails
 *
 * @example
 * ```ts
 * try {
 *   const count = await exportVehiclesToExcel({
 *     vehicleType: 'CARGO',
 *     status: 'ON_TERMINAL'
 *   });
 *   message.success(`Exported ${count} records`);
 * } catch (error) {
 *   message.error('Export failed');
 * }
 * ```
 */
export async function exportVehiclesToExcel(filters: ExportFilters = {}): Promise<number> {
  // Build query params
  const params = new URLSearchParams();
  params.append('page_size', '10000'); // Get all records

  if (filters.vehicleType && filters.vehicleType !== 'all') {
    params.append('vehicle_type', filters.vehicleType);
  }
  if (filters.status && filters.status !== 'all') {
    params.append('status', filters.status);
  }
  if (filters.searchText) {
    params.append('license_plate', filters.searchText);
  }
  if (filters.dateRange) {
    params.append('entry_time_after', filters.dateRange[0].format('YYYY-MM-DD'));
    params.append('entry_time_before', filters.dateRange[1].format('YYYY-MM-DD'));
  }

  // Fetch data
  const data = await http.get<{ count: number; results: Vehicle[] }>(
    `/vehicles/entries/?${params.toString()}`
  );

  if (data.results.length === 0) {
    throw new Error('Нет данных для экспорта');
  }

  // Transform data for Excel
  const excelData: ExcelRow[] = data.results.map((v, index) => ({
    '№': index + 1,
    'Гос. номер': v.license_plate,
    'Статус': v.status_display,
    'Клиент': v.customer?.name || '—',
    'Телефон клиента': v.customer?.phone || '—',
    'Тип ТС': v.vehicle_type_display,
    'Время въезда': v.entry_time ? formatDateTime(v.entry_time) : '—',
    'Тип транспорта': v.transport_type_display || '—',
    'Статус загрузки въезд': v.entry_load_status_display || '—',
    'Тип груза': v.cargo_type_display || '—',
    'Время выезда': v.exit_time ? formatDateTime(v.exit_time) : '—',
    'Статус загрузки выезд': v.exit_load_status_display || '—',
    'Время пребывания (ч)': v.dwell_time_hours?.toFixed(2) || '—',
  }));

  // Create workbook and worksheet
  const ws = XLSX.utils.json_to_sheet(excelData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Транспорт');

  // Auto-size columns
  const colWidths = Object.keys(excelData[0] || {}).map(key => ({
    wch: Math.max(key.length, 15),
  }));
  ws['!cols'] = colWidths;

  // Download file
  const fileName = `transport_${dayjs().format('YYYY-MM-DD_HH-mm')}.xlsx`;
  XLSX.writeFile(wb, fileName);

  return excelData.length;
}
