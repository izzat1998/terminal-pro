/**
 * Format a date string to DD.MM.YYYY HH:mm format
 * Returns '—' for invalid dates
 */
export function formatDateTime(dateString: string): string {
  const date = new Date(dateString);

  // Validate the date is valid
  if (isNaN(date.getTime())) {
    return '—';
  }

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${day}.${month}.${year} ${hours}:${minutes}`;
}

/**
 * Format a date string to DD.MM.YYYY format
 * Returns '—' for invalid dates
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);

  // Validate the date is valid
  if (isNaN(date.getTime())) {
    return '—';
  }

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();

  return `${day}.${month}.${year}`;
}
