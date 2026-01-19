// ============================================================================
// Adapter Utility Functions
// ============================================================================
// Shared utilities for all adapters including variable interpolation and
// nested value access.
// ============================================================================

/**
 * Get nested value from object using dot notation path.
 * Example: getNestedValue({container1: {data: {id: 42}}}, 'container1.data.id') => 42
 */
export function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const keys = path.split('.');
  let current: unknown = obj;

  for (const key of keys) {
    if (current === null || current === undefined) {
      return undefined;
    }
    if (typeof current === 'object') {
      current = (current as Record<string, unknown>)[key];
    } else {
      return undefined;
    }
  }

  return current;
}

/**
 * Interpolate variables in a string.
 * Pattern: {{ variableName }} or {{ container1.data.id }}
 */
export function interpolate(template: string, data: Record<string, unknown>): string {
  return template.replace(/\{\{\s*([^}]+)\s*\}\}/g, (_, path) => {
    const value = getNestedValue(data, path.trim());
    if (value === undefined) {
      console.warn(`Variable not found: ${path}`);
      return `{{${path}}}`;
    }
    return String(value);
  });
}

/**
 * Interpolate variables in an object recursively.
 */
export function interpolateObject(
  obj: Record<string, unknown>,
  data: Record<string, unknown>
): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(obj)) {
    if (typeof value === 'string') {
      result[key] = interpolate(value, data);
    } else if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      result[key] = interpolateObject(value as Record<string, unknown>, data);
    } else if (Array.isArray(value)) {
      result[key] = value.map((item) => {
        if (typeof item === 'string') {
          return interpolate(item, data);
        }
        if (item !== null && typeof item === 'object') {
          return interpolateObject(item as Record<string, unknown>, data);
        }
        return item;
      });
    } else {
      result[key] = value;
    }
  }

  return result;
}

/**
 * Simple delay utility.
 */
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
