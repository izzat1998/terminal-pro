/**
 * Dayjs configuration with Asia/Tashkent timezone.
 * Import from '@/config/dayjs' instead of 'dayjs' for timezone-aware operations.
 */

import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/ru';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(localizedFormat);
dayjs.extend(customParseFormat);
dayjs.extend(relativeTime);
dayjs.locale('ru');

export const APP_TIMEZONE = 'Asia/Tashkent';
dayjs.tz.setDefault(APP_TIMEZONE);

export default dayjs;

/** Parse a date string to dayjs in Asia/Tashkent timezone */
export function parseDate(dateString: string | null | undefined): dayjs.Dayjs | null {
  if (!dateString) return null;
  const parsed = dayjs(dateString);
  return parsed.isValid() ? parsed.tz(APP_TIMEZONE) : null;
}

/** Get current time in Asia/Tashkent timezone */
export function now(): dayjs.Dayjs {
  return dayjs().tz(APP_TIMEZONE);
}

/** Format to DD.MM.YYYY HH:mm. Returns '—' for invalid dates. */
export function formatDateTime(dateString: string | null | undefined): string {
  const date = parseDate(dateString);
  return date ? date.format('DD.MM.YYYY HH:mm') : '—';
}

/** Format to DD.MM.YYYY. Returns '—' for invalid dates. */
export function formatDate(dateString: string | null | undefined): string {
  const date = parseDate(dateString);
  return date ? date.format('DD.MM.YYYY') : '—';
}

/** Format to D/M for chart labels */
export function formatDateLabel(dateString: string | null | undefined): string {
  const date = parseDate(dateString);
  return date ? date.format('D/M') : '';
}

/** Format as relative time (e.g., "5 мин назад") */
export function formatRelativeTime(dateString: string | null | undefined): string {
  const date = parseDate(dateString);
  if (!date) return '—';

  const nowTime = now();
  const diffMinutes = nowTime.diff(date, 'minute');
  const diffHours = nowTime.diff(date, 'hour');
  const diffDays = nowTime.diff(date, 'day');

  if (diffMinutes < 1) return 'только что';
  if (diffMinutes < 60) return `${diffMinutes} мин назад`;
  if (diffHours < 24) return `${diffHours} ч назад`;
  if (diffDays === 1) return 'вчера';
  if (diffDays < 7) return `${diffDays} дн назад`;

  return date.format('DD.MM.YYYY');
}
