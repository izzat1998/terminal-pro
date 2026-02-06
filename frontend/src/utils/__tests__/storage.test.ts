import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setStorageItem, getStorageItem, removeStorageItem } from '../storage';

describe('storage utilities', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  describe('setStorageItem', () => {
    it('should store a value in localStorage', () => {
      setStorageItem('test_key', 'test_value');
      expect(localStorage.getItem('test_key')).toBe('test_value');
    });

    it('should overwrite existing value', () => {
      localStorage.setItem('test_key', 'old_value');
      setStorageItem('test_key', 'new_value');
      expect(localStorage.getItem('test_key')).toBe('new_value');
    });

    it('should handle localStorage errors gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });

      // Should not throw
      setStorageItem('test_key', 'test_value');
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to save to localStorage:',
        expect.any(Error)
      );
    });
  });

  describe('getStorageItem', () => {
    it('should retrieve a value from localStorage', () => {
      localStorage.setItem('test_key', 'stored_value');
      expect(getStorageItem('test_key')).toBe('stored_value');
    });

    it('should return null for non-existent key', () => {
      expect(getStorageItem('non_existent')).toBeNull();
    });

    it('should handle localStorage errors gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('SecurityError');
      });

      const result = getStorageItem('test_key');
      expect(result).toBeNull();
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to read from localStorage:',
        expect.any(Error)
      );
    });
  });

  describe('removeStorageItem', () => {
    it('should remove a value from localStorage', () => {
      localStorage.setItem('test_key', 'value');
      removeStorageItem('test_key');
      expect(localStorage.getItem('test_key')).toBeNull();
    });

    it('should not throw when removing non-existent key', () => {
      expect(() => removeStorageItem('non_existent')).not.toThrow();
    });

    it('should handle localStorage errors gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
        throw new Error('SecurityError');
      });

      // Should not throw
      removeStorageItem('test_key');
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to remove from localStorage:',
        expect.any(Error)
      );
    });
  });
});
