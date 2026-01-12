// Using localStorage for token persistence
// Note: localStorage is vulnerable to XSS attacks, ensure proper sanitization
export function setCookie(name: string, value: string) {
  try {
    localStorage.setItem(name, value);
  } catch (error) {
    console.error('Failed to save to localStorage:', error);
  }
}

export function getCookie(name: string): string | null {
  try {
    return localStorage.getItem(name);
  } catch (error) {
    console.error('Failed to read from localStorage:', error);
    return null;
  }
}

export function deleteCookie(name: string) {
  try {
    localStorage.removeItem(name);
  } catch (error) {
    console.error('Failed to remove from localStorage:', error);
  }
}
