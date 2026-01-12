/**
 * Shared API types for the Telegram Mini App
 * Consolidates interfaces that were previously duplicated across multiple files
 */

// ============ Plate Recognition ============

export interface RecognitionResult {
  plate_number: string;
  confidence: number;
  success: boolean;
  error_message?: string;
}

// ============ Choices/Options ============

export interface ChoiceOption {
  value: string;
  label: string;
}

export interface ChoicesResponse {
  vehicle_types: ChoiceOption[];
  visitor_types: ChoiceOption[];
  transport_types: ChoiceOption[];
  load_statuses: ChoiceOption[];
  cargo_types: ChoiceOption[];
  container_sizes: ChoiceOption[];
}

// ============ Destination ============

export interface Destination {
  id: number;
  name: string;
  code: string;
  zone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DestinationsResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Destination[];
}

// ============ Photo/File ============

export interface PhotoFile {
  id: string;
  file_url: string;
  original_filename: string;
  file_category: number;
  category_name: string;
  mime_type: string;
  size: number;
  size_mb: string;
  uploaded_by: number;
  uploaded_by_username: string;
  is_public: boolean;
  is_active: boolean;
  width: number;
  height: number;
  created_at: string;
  updated_at: string;
}

// ============ Customer ============

export interface Customer {
  id: number;
  name: string;
  phone: string;
}

// ============ Vehicle Entry ============

export type VehicleStatus = 'WAITING' | 'ON_TERMINAL' | 'EXITED';
export type VehicleType = 'LIGHT' | 'CARGO';
export type VisitorType = 'EMPLOYEE' | 'CUSTOMER' | 'GUEST';
export type TransportType = 'PLATFORM' | 'FURA' | 'PRICEP' | 'MINI_FURA' | 'ZIL' | 'GAZEL' | 'LABO';
export type LoadStatus = 'LOADED' | 'EMPTY';
export type CargoType = 'CONTAINER' | 'FOOD' | 'METAL' | 'WOOD' | 'CHEMICAL' | 'EQUIPMENT' | 'OTHER';
export type ContainerSize = '1x20F' | '2x20F' | '40F';

export interface VehicleEntry {
  id: number;
  status: VehicleStatus;
  status_display: string;
  license_plate: string;
  entry_photos: PhotoFile[];
  entry_time: string | null;
  manager: number | null;
  customer: Customer | null;
  vehicle_type: VehicleType;
  vehicle_type_display: string;
  visitor_type?: VisitorType | null;
  visitor_type_display?: string | null;
  transport_type?: TransportType | null;
  transport_type_display?: string | null;
  entry_load_status?: LoadStatus | null;
  entry_load_status_display?: string | null;
  cargo_type?: CargoType | null;
  cargo_type_display?: string | null;
  container_size?: ContainerSize | null;
  container_size_display?: string | null;
  container_load_status?: LoadStatus | null;
  container_load_status_display?: string | null;
  destination?: number | null;
  exit_photos: PhotoFile[];
  exit_time?: string | null;
  exit_load_status?: LoadStatus | null;
  exit_load_status_display?: string | null;
  is_on_terminal: boolean;
  dwell_time_hours: number | null;
  created_at: string;
  updated_at: string;
}

export interface VehicleEntriesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: VehicleEntry[];
}

export interface VehicleEntryPayload {
  license_plate: string;
  entry_photo_files: string[];
  entry_time: string;
  vehicle_type?: VehicleType;
  visitor_type?: VisitorType;
  transport_type?: TransportType;
  entry_load_status?: LoadStatus;
  cargo_type?: CargoType;
  container_size?: ContainerSize;
  container_load_status?: LoadStatus;
  destination?: number;
}

// ============ Statistics ============

export interface VehicleTypeCount {
  vehicle_type: VehicleType;
  vehicle_type_display: string;
  count: number;
}

export interface TransportTypeCount {
  transport_type: TransportType;
  transport_type_display: string;
  count: number;
}

export interface LoadStatusCount {
  entry_load_status: LoadStatus;
  entry_load_status_display: string;
  count: number;
}

export interface OverstayerInfo {
  id: number;
  license_plate: string;
  entry_time: string;
  dwell_time_hours: number;
}

export interface DailyEntryCount {
  date: string;
  count: number;
}

export interface CurrentStats {
  total_on_terminal: number;
  by_vehicle_type: VehicleTypeCount[];
  by_transport_type: TransportTypeCount[];
  by_load_status: LoadStatusCount[];
  avg_dwell_time_hours: number;
  avg_dwell_time_by_vehicle_type: { vehicle_type: VehicleType; avg_hours: number }[];
  longest_stay_hours: number;
  overstayers: OverstayerInfo[];
}

export interface Last30DaysStats {
  total_entries: number;
  total_exits: number;
  daily_entries: DailyEntryCount[];
}

export interface TerminalStatistics {
  current: CurrentStats;
  last_30_days: Last30DaysStats;
}
