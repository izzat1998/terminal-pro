/**
 * Local storage utilities for token persistence
 * Note: localStorage is vulnerable to XSS attacks, ensure proper sanitization
 */

export function setStorageItem(name: string, value: string): void {
  try {
    localStorage.setItem(name, value);
  } catch (error) {
    console.error('Failed to save to localStorage:', error);
  }
}

export function getStorageItem(name: string): string | null {
  try {
    return localStorage.getItem(name);
  } catch (error) {
    console.error('Failed to read from localStorage:', error);
    return null;
  }
}

export function removeStorageItem(name: string): void {
  try {
    localStorage.removeItem(name);
  } catch (error) {
    console.error('Failed to remove from localStorage:', error);
  }
}

// Legacy aliases for backward compatibility during migration
// TODO: Remove these aliases after all usages are migrated
export const setCookie = setStorageItem;
export const getCookie = getStorageItem;
export const deleteCookie = removeStorageItem;
