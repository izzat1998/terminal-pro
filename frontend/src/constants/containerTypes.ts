/**
 * Container ISO type constants
 * Centralized definition to avoid duplication across components
 */

/** Standard container ISO types used throughout the application */
export const ISO_TYPES = [
  '22G1', // 20ft standard
  '42G1', // 40ft standard
  '45G1', // 45ft high cube
  'L5G1', // 45ft standard
  '22R1', // 20ft reefer
  '42R1', // 40ft reefer
  '45R1', // 45ft reefer high cube
  'L5R1', // 45ft reefer
  '22U1', // 20ft open top
  '42U1', // 40ft open top
  '45U1', // 45ft open top
  '22P1', // 20ft flat rack
  '42P1', // 40ft flat rack
  '45P1', // 45ft flat rack
  '22T1', // 20ft tank
  '42T1', // 40ft tank
] as const;

/** Type for ISO type values */
export type IsoType = (typeof ISO_TYPES)[number];

/** Container status options */
export const CONTAINER_STATUSES = ['Порожний', 'Гружёный'] as const;
export type ContainerStatus = (typeof CONTAINER_STATUSES)[number];

/** Transport type options */
export const TRANSPORT_TYPES = ['Авто', 'Вагон'] as const;
export type TransportType = (typeof TRANSPORT_TYPES)[number];

/** Default text for containers without a company */
export const NO_COMPANY_LABEL = 'Без компании';
