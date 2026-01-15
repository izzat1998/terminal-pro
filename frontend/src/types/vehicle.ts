/**
 * Vehicle-related type definitions
 * Extracted from Vehicles.vue for reusability
 */

export interface Photo {
  id: string;
  file_url: string;
  thumbnail_url?: string;
  image_url?: string;
  original_filename: string;
  file_category: number;
  category_name: string;
  mime_type: string;
  size: number;
  size_mb: number;
  uploaded_by: number | null;
  is_public: boolean;
  is_active: boolean;
  width: number;
  height: number;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: number;
  name: string;
  phone: string;
  company_slug: string;
}

export interface Manager {
  id: number;
  name: string;
  phone: string;
}

export interface Vehicle {
  id: number;
  status: string;
  status_display: string;
  license_plate: string;
  entry_photos: Photo[];
  entry_time: string | null;
  manager: Manager | null;
  customer: Customer | null;
  vehicle_type: string;
  vehicle_type_display: string;
  visitor_type: string | null;
  visitor_type_display: string | null;
  transport_type: string | null;
  transport_type_display: string | null;
  entry_load_status: string | null;
  entry_load_status_display: string | null;
  cargo_type: string | null;
  cargo_type_display: string | null;
  container_size: string | null;
  container_size_display: string | null;
  container_load_status: string | null;
  container_load_status_display: string | null;
  destination: number | null;
  exit_photos: Photo[];
  exit_time: string | null;
  exit_load_status: string | null;
  exit_load_status_display: string | null;
  is_on_terminal: boolean;
  dwell_time_hours: number | null;
  created_at: string;
  updated_at: string;
}

/** Transformed vehicle record for table display */
export interface VehicleRecord {
  key: string;
  id: number;
  status: string;
  status_display: string;
  license_plate: string;
  entry_photos: Photo[];
  entry_time: string;
  customer_id: number | null;
  customer_name: string;
  customer_phone: string;
  customer_company_slug: string;
  manager_name: string;
  manager_phone: string;
  vehicle_type: string;
  vehicle_type_display: string;
  visitor_type: string;
  visitor_type_display: string;
  transport_type: string;
  transport_type_display: string;
  entry_load_status: string;
  entry_load_status_display: string;
  cargo_type: string;
  cargo_type_display: string;
  container_size: string;
  container_size_display: string;
  container_load_status: string;
  container_load_status_display: string;
  destination: number | null;
  exit_photos: Photo[];
  exit_time: string;
  exit_load_status: string;
  exit_load_status_display: string;
  is_on_terminal: boolean;
  dwell_time_hours: string;
}

/** API response for gate statistics */
export interface GateStatistics {
  current: {
    total_on_terminal: number;
    by_vehicle_type: Record<string, { count: number; label: string }>;
  };
  time_metrics: {
    avg_dwell_hours: number;
    longest_current_stay: {
      license_plate: string;
      hours: number;
      vehicle_type: string;
    } | null;
  };
  overstayers: {
    count: number;
  };
  last_30_days: {
    total_entries: number;
    total_exits: number;
  };
}

/** Simplified stats for display */
export interface GateStats {
  total: number;
  light: number;
  cargo: number;
  overstayers: number;
  avgDwellHours: number;
  entriesLast30Days: number;
  exitsLast30Days: number;
  longestStay: {
    plate: string;
    hours: number;
  };
}

/** Destination for cargo vehicles */
export interface Destination {
  id: number;
  name: string;
  code: string;
  zone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Choice option from API */
export interface ChoiceOption {
  value: string;
  label: string;
}

/** All vehicle choices from API */
export interface VehicleChoices {
  vehicle_types: ChoiceOption[];
  visitor_types: ChoiceOption[];
  transport_types: ChoiceOption[];
  load_statuses: ChoiceOption[];
  cargo_types: ChoiceOption[];
  container_sizes: ChoiceOption[];
}

/** Customer option for select dropdowns */
export interface CustomerOption {
  id: number;
  first_name: string;
  phone_number: string;
}
