/**
 * Yard Service - API client for 3D yard slot data
 */

import { http } from '../utils/httpClient'

/** Container entry data nested within a yard slot */
export interface YardSlotContainerEntry {
  id: number
  container_number: string
  iso_type: string
  status: 'LADEN' | 'EMPTY'
  is_hazmat: boolean
  imo_class: string | null
  priority: string
  company_name: string | null
  dwell_time_days: number
  entry_time: string
  cargo_name: string
}

/** Yard slot with physical + logical position and optional occupant */
export interface YardSlot {
  id: number
  zone: string
  row: number
  bay: number
  tier: number
  sub_slot: string
  dxf_x: number | null
  dxf_y: number | null
  rotation: number
  container_size: string
  container_entry: YardSlotContainerEntry | null
}

interface YardSlotsResponse {
  success: boolean
  data: YardSlot[]
}

/**
 * Fetch all yard slots with occupant data
 */
export async function getYardSlots(params?: {
  zone?: string
  occupied?: boolean
  container_size?: string
}): Promise<YardSlot[]> {
  const query = new URLSearchParams()
  if (params?.zone) query.append('zone', params.zone)
  if (params?.occupied !== undefined) query.append('occupied', String(params.occupied))
  if (params?.container_size) query.append('container_size', params.container_size)

  const qs = query.toString()
  const url = `/terminal/yard/slots/${qs ? `?${qs}` : ''}`
  const response = await http.get<YardSlotsResponse>(url)
  return response.data
}
