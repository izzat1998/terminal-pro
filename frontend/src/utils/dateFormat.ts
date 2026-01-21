/**
 * Date formatting utilities for Asia/Tashkent timezone.
 * Re-exports from @/config/dayjs for backward compatibility.
 */

import dayjs, {
  parseDate,
  formatDateTime,
  formatDate,
  formatDateLabel,
  formatRelativeTime,
  APP_TIMEZONE,
} from '@/config/dayjs';

export { dayjs, parseDate, formatDateTime, formatDate, formatDateLabel, formatRelativeTime, APP_TIMEZONE };

/**
 * Format to DD.MM.YYYY. Returns empty string for invalid dates.
 * Use when empty string is preferred over '—' (e.g., form fields).
 */
export function formatDateLocale(dateString: string | null | undefined): string {
  const result = formatDate(dateString);
  return result === '—' ? '' : result;
}

/**
 * Format to DD.MM.YYYY, HH:mm. Returns empty string for invalid dates.
 */
export function formatDateTimeLocale(dateString: string | null | undefined): string {
  if (!dateString) return '';
  const date = parseDate(dateString);
  return date ? date.format('DD.MM.YYYY, HH:mm') : '';
}
