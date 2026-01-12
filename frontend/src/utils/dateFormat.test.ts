import { describe, it, expect } from 'vitest'
import { formatDateTime, formatDate } from './dateFormat'

describe('dateFormat utilities', () => {
  describe('formatDateTime', () => {
    it('formats ISO date string to DD.MM.YYYY HH:mm', () => {
      // Note: This test assumes local timezone, adjust if needed
      const result = formatDateTime('2025-01-15T14:30:00')
      expect(result).toMatch(/^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$/)
    })

    it('pads single digit values with zeros', () => {
      const result = formatDateTime('2025-01-05T09:05:00')
      expect(result).toContain('05')
    })
  })

  describe('formatDate', () => {
    it('formats ISO date string to DD.MM.YYYY', () => {
      const result = formatDate('2025-01-15T14:30:00')
      expect(result).toMatch(/^\d{2}\.\d{2}\.\d{4}$/)
    })
  })
})
