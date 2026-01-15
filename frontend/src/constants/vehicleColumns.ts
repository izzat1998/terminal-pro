/**
 * Vehicle table column definitions
 * Extracted from Vehicles.vue for maintainability
 */

import type { VehicleRecord } from '../types/vehicle';

/** Column definition with proper typing */
export interface VehicleColumnDef {
  title: string;
  key: string;
  dataIndex?: string;
  align?: 'left' | 'center' | 'right';
  width?: number;
  fixed?: 'left' | 'right';
  sorter?: (a: VehicleRecord, b: VehicleRecord) => number;
  defaultSortOrder?: 'ascend' | 'descend';
  filters?: { text: string; value: string }[];
  onFilter?: (value: string, record: VehicleRecord) => boolean;
}

/** Vehicle table columns configuration */
export const VEHICLE_COLUMNS: VehicleColumnDef[] = [
  {
    title: '№',
    key: 'number',
    align: 'center',
    width: 60,
    fixed: 'left',
  },
  {
    title: 'Гос. номер',
    dataIndex: 'license_plate',
    key: 'license_plate',
    align: 'center',
    width: 120,
    fixed: 'left',
    sorter: (a, b) => a.license_plate.localeCompare(b.license_plate),
  },
  {
    title: 'Статус',
    key: 'status',
    align: 'center',
    width: 120,
    filters: [
      { text: 'Ожидает', value: 'WAITING' },
      { text: 'На терминале', value: 'ON_TERMINAL' },
      { text: 'Выехал', value: 'EXITED' },
      { text: 'Отменён', value: 'CANCELLED' },
    ],
    onFilter: (value, record) => record.status === value,
  },
  {
    title: 'Клиент',
    key: 'customer',
    align: 'center',
    width: 150,
    sorter: (a, b) => a.customer_name.localeCompare(b.customer_name),
  },
  {
    title: 'Менеджер',
    key: 'manager',
    align: 'center',
    width: 150,
  },
  {
    title: 'Тип ТС',
    dataIndex: 'vehicle_type_display',
    key: 'vehicle_type',
    align: 'center',
    width: 140,
    filters: [
      { text: 'Легковой', value: 'LIGHT' },
      { text: 'Грузовой', value: 'CARGO' },
    ],
    onFilter: (value, record) => record.vehicle_type === value,
  },
  {
    title: 'Фото въезда',
    key: 'entry_photos',
    align: 'center',
    width: 180,
  },
  {
    title: 'Время въезда',
    dataIndex: 'entry_time',
    key: 'entry_time',
    align: 'center',
    width: 160,
    sorter: (a, b) => a.entry_time.localeCompare(b.entry_time),
    defaultSortOrder: 'descend',
  },
  {
    title: 'Тип посетителя',
    dataIndex: 'visitor_type_display',
    key: 'visitor_type',
    align: 'center',
    width: 130,
  },
  {
    title: 'Тип транспорта',
    dataIndex: 'transport_type_display',
    key: 'transport_type',
    align: 'center',
    width: 130,
  },
  {
    title: 'Статус загрузки въезд',
    dataIndex: 'entry_load_status_display',
    key: 'entry_load_status',
    align: 'center',
    width: 170,
  },
  {
    title: 'Тип груза',
    dataIndex: 'cargo_type_display',
    key: 'cargo_type',
    align: 'center',
    width: 120,
  },
  {
    title: 'Размер контейнера',
    dataIndex: 'container_size_display',
    key: 'container_size',
    align: 'center',
    width: 150,
  },
  {
    title: 'Фото выезда',
    key: 'exit_photos',
    align: 'center',
    width: 180,
  },
  {
    title: 'Время выезда',
    dataIndex: 'exit_time',
    key: 'exit_time',
    align: 'center',
    width: 160,
    sorter: (a, b) => a.exit_time.localeCompare(b.exit_time),
  },
  {
    title: 'Статус загрузки выезд',
    dataIndex: 'exit_load_status_display',
    key: 'exit_load_status',
    align: 'center',
    width: 170,
  },
  {
    title: 'Время пребывания (ч)',
    dataIndex: 'dwell_time_hours',
    key: 'dwell_time_hours',
    align: 'center',
    width: 160,
    sorter: (a, b) => {
      const aVal = a.dwell_time_hours === '—' ? 0 : parseFloat(a.dwell_time_hours);
      const bVal = b.dwell_time_hours === '—' ? 0 : parseFloat(b.dwell_time_hours);
      return aVal - bVal;
    },
  },
  {
    title: 'Действия',
    key: 'actions',
    align: 'center',
    width: 120,
    fixed: 'right',
  },
];

/** Status filter options */
export const STATUS_FILTERS = [
  { text: 'Ожидает', value: 'WAITING' },
  { text: 'На терминале', value: 'ON_TERMINAL' },
  { text: 'Выехал', value: 'EXITED' },
  { text: 'Отменён', value: 'CANCELLED' },
] as const;

/** Vehicle type filter options */
export const VEHICLE_TYPE_FILTERS = [
  { text: 'Легковой', value: 'LIGHT' },
  { text: 'Грузовой', value: 'CARGO' },
] as const;
