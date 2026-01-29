/**
 * Keyboard Event Utilities
 *
 * Provides helper functions for keyboard event handling,
 * particularly for distinguishing between typing in inputs vs. global shortcuts.
 */

/**
 * Check if the keyboard event target is an input element
 *
 * Use this to skip global keyboard shortcuts when user is typing in a form field.
 *
 * @param event - The keyboard event to check
 * @returns true if the event target is an input element (input, textarea, or contentEditable)
 *
 * @example
 * function handleKeyDown(event: KeyboardEvent): void {
 *   if (isInputElement(event)) return
 *   if (event.key.toLowerCase() === 'd') toggleDebug()
 * }
 */
export function isInputElement(event: KeyboardEvent): boolean {
  const target = event.target as HTMLElement | null
  if (!target) return false

  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target.isContentEditable
  )
}
