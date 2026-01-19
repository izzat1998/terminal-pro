/**
 * Date formatting utilities for the Telegram Mini App
 */

/**
 * Format a date string for display in Uzbek locale
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
