import { Page } from '@playwright/test';

/**
 * E2E Test Helpers
 *
 * Common utilities for authentication and test setup
 */

export const TEST_CREDENTIALS = {
  admin: {
    username: 'admin',
    password: 'admin123',
  },
};

/**
 * Login as admin user
 */
export async function loginAsAdmin(page: Page) {
  await page.goto('/login');

  // Wait for login form to be visible
  await page.waitForSelector('input[placeholder="Имя пользователя"]', { state: 'visible' });

  // Fill login form
  await page.fill('input[placeholder="Имя пользователя"]', TEST_CREDENTIALS.admin.username);
  await page.fill('input[placeholder="Пароль"]', TEST_CREDENTIALS.admin.password);

  // Submit
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard or main page (with longer timeout)
  await page.waitForURL(/\/(dashboard|containers|vehicles)?$/, { timeout: 15000 });
}

/**
 * Check if user is logged in
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  // Check for logout button or user menu
  const logoutButton = await page.$('text=Выйти');
  return logoutButton !== null;
}

/**
 * Wait for modal to be visible
 */
export async function waitForModal(page: Page) {
  await page.waitForSelector('.ant-modal-content', { state: 'visible' });
}

/**
 * Close modal by clicking cancel or X
 */
export async function closeModal(page: Page) {
  await page.click('.ant-modal-close, button:has-text("Отмена")');
  await page.waitForSelector('.ant-modal-content', { state: 'hidden' });
}

/**
 * Fill Ant Design Select component
 */
export async function fillAntSelect(page: Page, selector: string, value: string) {
  await page.click(selector);
  await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
  await page.click(`.ant-select-item-option:has-text("${value}")`);
}

/**
 * Fill Ant Design Radio Group
 */
export async function selectAntRadio(page: Page, containerSelector: string, value: string) {
  await page.click(`${containerSelector} .ant-radio-button-wrapper:has-text("${value}")`);
}

/**
 * Wait for success message
 */
export async function waitForSuccessMessage(page: Page) {
  await page.waitForSelector('.ant-message-success', { state: 'visible', timeout: 10000 });
}

/**
 * Wait for error message
 */
export async function waitForErrorMessage(page: Page) {
  await page.waitForSelector('.ant-message-error', { state: 'visible', timeout: 10000 });
}
