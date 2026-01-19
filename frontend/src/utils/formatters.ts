/**
 * Shared formatting utilities for currency and numeric values.
 * Provides consistent formatting across the application.
 */

/**
 * Format a numeric value as currency.
 * Supports USD and UZS (Uzbek Sum) currencies.
 *
 * @param value - The numeric value to format (number or string)
 * @param currency - The currency code ('USD' or 'UZS'), defaults to 'USD'
 * @returns Formatted currency string
 *
 * @example
 * formatCurrency(1234.56, 'USD') // '$1 234,56'
 * formatCurrency('5000000', 'UZS') // '5 000 000 сум'
 */
export function formatCurrency(
  value: number | string | undefined,
  currency: 'USD' | 'UZS' = 'USD'
): string {
  if (value === undefined || value === null || value === '') {
    return '—';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;

  if (isNaN(num)) {
    return '—';
  }

  if (currency === 'USD') {
    return `$${num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} сум`;
}

/**
 * Format currency with compact notation (K, M suffixes).
 * Useful for dashboard KPI displays where space is limited.
 *
 * @param value - The numeric value or string to format
 * @returns Formatted compact currency string (e.g., '$1.5M', '$500K')
 *
 * @example
 * formatCurrencyCompact('1500000') // '$1.5M'
 * formatCurrencyCompact('50000') // '$50.0K'
 * formatCurrencyCompact('500') // '$500'
 */
export function formatCurrencyCompact(value: string | number | undefined): string {
  if (value === undefined || value === null || value === '') {
    return '$0';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;

  if (isNaN(num)) {
    return '$0';
  }

  if (num >= 1000000) {
    return `$${(num / 1000000).toFixed(1)}M`;
  }

  if (num >= 1000) {
    return `$${(num / 1000).toFixed(1)}K`;
  }

  return `$${num.toFixed(0)}`;
}

/**
 * Format UZS (Uzbek Sum) currency value.
 * Convenience function for formatting UZS specifically.
 *
 * @param value - The numeric value or string to format
 * @returns Formatted UZS currency string
 *
 * @example
 * formatUzs('5000000') // '5 000 000 сум'
 */
export function formatUzs(value: string | number | undefined): string {
  return formatCurrency(value, 'UZS');
}
