import { describe, it, expect } from 'vitest'
import { formatDateTime, formatDate, formatRelativeTime, formatDateLocale, formatDateTimeLocale } from './dateFormat'

describe('dateFormat utilities', () => {
  describe('formatDateTime', () => {
    it('formats ISO date string to DD.MM.YYYY HH:mm', () => {
      const result = formatDateTime('2025-01-15T14:30:00')
      expect(result).toMatch(/^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$/)
    })

    it('pads single digit values with zeros', () => {
      const result = formatDateTime('2025-01-05T09:05:00')
      expect(result).toContain('05')
    })

    it('converts UTC times to Asia/Tashkent (+05:00)', () => {
      // UTC 09:30 should become 14:30 in Tashkent
      const result = formatDateTime('2025-01-15T09:30:00Z')
      expect(result).toBe('15.01.2025 14:30')
    })

    it('returns — for invalid dates', () => {
      expect(formatDateTime('invalid')).toBe('—')
      expect(formatDateTime('')).toBe('—')
    })
  })

  describe('formatDate', () => {
    it('formats ISO date string to DD.MM.YYYY', () => {
      const result = formatDate('2025-01-15T14:30:00')
      expect(result).toMatch(/^\d{2}\.\d{2}\.\d{4}$/)
    })

    it('converts UTC dates to Asia/Tashkent timezone', () => {
      // UTC 23:30 on Jan 15 should become Jan 16 in Tashkent (UTC+5)
      const result = formatDate('2025-01-15T23:30:00Z')
      expect(result).toBe('16.01.2025')
    })
  })

  describe('formatDateLocale', () => {
    it('returns empty string for null/undefined', () => {
      expect(formatDateLocale(null)).toBe('')
      expect(formatDateLocale(undefined)).toBe('')
    })

    it('formats valid date string', () => {
      const result = formatDateLocale('2025-01-15T14:30:00Z')
      expect(result).toMatch(/^\d{2}\.\d{2}\.\d{4}$/)
    })
  })

  describe('formatDateTimeLocale', () => {
    it('returns empty string for null/undefined', () => {
      expect(formatDateTimeLocale(null)).toBe('')
      expect(formatDateTimeLocale(undefined)).toBe('')
    })

    it('formats valid datetime string with comma separator', () => {
      const result = formatDateTimeLocale('2025-01-15T09:30:00Z')
      expect(result).toBe('15.01.2025, 14:30')
    })
  })

  describe('formatRelativeTime', () => {
    it('returns — for invalid dates', () => {
      expect(formatRelativeTime('invalid')).toBe('—')
    })
  })
})
