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

/**
 * Format a date string to localized Russian format using toLocaleDateString
 * Returns empty string for null/undefined/invalid dates
 */
export function formatDateLocale(dateString: string | null | undefined): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleDateString('ru-RU');
}

/**
 * Format a datetime string to localized Russian format (DD.MM.YYYY, HH:MM)
 * Returns empty string for null/undefined/invalid dates
 */
export function formatDateTimeLocale(dateString: string | null | undefined): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format a date string for chart labels (D/M format)
 * Used for compact axis labels in charts
 */
export function formatDateLabel(dateString: string): string {
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return '';
  return `${date.getDate()}/${date.getMonth() + 1}`;
}

/**
 * Format a date as relative time (e.g., "5 мин назад", "2 часа назад")
 * Used for displaying how long ago something happened
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return '—';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMinutes < 1) {
    return 'только что';
  }
  if (diffMinutes < 60) {
    return `${diffMinutes} мин назад`;
  }
  if (diffHours < 24) {
    return `${diffHours} ч назад`;
  }
  if (diffDays === 1) {
    return 'вчера';
  }
  if (diffDays < 7) {
    return `${diffDays} дн назад`;
  }

  // Fall back to regular date format
  return formatDate(dateString);
}
