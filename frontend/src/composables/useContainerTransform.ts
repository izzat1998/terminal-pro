/**
 * Composable for transforming container entry API responses to frontend records.
 * Extracts duplicate data transformation logic from ContainerTable.vue.
 *
 * Usage:
 *   import { useContainerTransform } from '@/composables/useContainerTransform'
 *   const { transformEntries } = useContainerTransform()
 *   dataSource.value = transformEntries(apiData)
 */

import type {
  TerminalEntry,
  CraneOperation,
  FileAttachment,
} from '../services/terminalService'
import { formatDateLocale, formatDateTimeLocale } from '../utils/dateFormat'

/**
 * Frontend record type used by ContainerTable.vue for display
 */
export interface ContainerRecord {
  key: string
  containerId: number
  container: string
  isoType: string
  containerStatus: string
  status: string
  transportType: string
  entryTrainNumber: string
  transportNumber: string
  exitDate: string
  exitTransportType: string
  exitTrainNumber: string
  exitTransportNumber: string
  destinationStation: string
  location: string
  additionalCraneOperationDate: string
  craneOperations: CraneOperation[]
  note: string
  cargoWeight: number | undefined
  cargoName: string
  clientName: string
  companyId: number | undefined
  companyName: string
  companySlug: string
  containerOwner: string
  containerOwnerId: number | undefined
  entryTime: string
  dwellTimeDays: number
  files: number
  filesData: FileAttachment[]
  created: string
  updated: string
  // Storage cost fields (populated by bulk fetch)
  storageCostUsd?: string
  storageCostUzs?: string
  storageBillableDays?: number
  storageCostLoading?: boolean
  // Additional charges fields (populated by bulk fetch)
  additionalChargesUsd?: string
  additionalChargesUzs?: string
  additionalChargesCount?: number
  additionalChargesLoading?: boolean
}

export function useContainerTransform() {
  /**
   * Transform a single API entry to frontend record format
   */
  const transformEntry = (entry: TerminalEntry): ContainerRecord => ({
    key: entry.id.toString(),
    containerId: entry.id,
    container: entry.container.container_number,
    isoType: entry.container.iso_type,
    containerStatus: entry.status,
    status: entry.status,
    transportType: entry.transport_type,
    entryTrainNumber: entry.entry_train_number || '',
    transportNumber: entry.transport_number || '',
    exitDate: entry.exit_date ? formatDateLocale(entry.exit_date) : '',
    exitTransportType: entry.exit_transport_type || '',
    exitTrainNumber: entry.exit_train_number || '',
    exitTransportNumber: entry.exit_transport_number || '',
    destinationStation: entry.destination_station || '',
    location: entry.location || '',
    additionalCraneOperationDate: entry.additional_crane_operation_date
      ? formatDateLocale(entry.additional_crane_operation_date)
      : '',
    craneOperations: entry.crane_operations || [],
    note: entry.note || '',
    cargoWeight: entry.cargo_weight ?? undefined,
    cargoName: entry.cargo_name || '',
    clientName: entry.client_name || '',
    companyId: entry.company?.id,
    companyName: entry.company?.name || '',
    companySlug: entry.company?.slug || '',
    containerOwner: entry.container_owner?.name || '',
    containerOwnerId: entry.container_owner?.id,
    entryTime: formatDateLocale(entry.entry_time),
    dwellTimeDays: entry.dwell_time_days || 0,
    files: entry.file_count,
    filesData: entry.files || [],
    created: formatDateTimeLocale(entry.created_at),
    updated: formatDateTimeLocale(entry.updated_at),
  })

  /**
   * Transform an array of API entries to frontend records
   */
  const transformEntries = (entries: TerminalEntry[]): ContainerRecord[] =>
    entries.map(transformEntry)

  return {
    transformEntry,
    transformEntries,
  }
}
