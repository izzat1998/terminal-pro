import { http } from '../utils/httpClient'

export interface EventPerformer {
  id: number
  full_name: string
  user_type: string
}

export interface ContainerEvent {
  id: number
  event_type: string
  event_type_display: string
  event_time: string
  performed_by: EventPerformer | null
  source: string
  source_display: string
  details: Record<string, unknown>
  created_at: string
}

export interface ContainerTimeline {
  container_number: string
  container_entry_id: number
  events: ContainerEvent[]
}

interface ApiResponse {
  success: boolean
  data: ContainerTimeline
}

export async function getContainerEvents(entryId: number): Promise<ContainerTimeline> {
  const response = await http.get<ApiResponse>(`/terminal/entries/${entryId}/events/`)
  return response.data
}
