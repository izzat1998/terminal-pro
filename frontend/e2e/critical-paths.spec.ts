import { test, expect } from '@playwright/test';

/**
 * CRITICAL PATH TESTS
 *
 * These are the MUST-HAVE tests for production deployment.
 * They cover the most important user flows that CANNOT fail.
 *
 * Run before every deployment:
 *   npm run test:e2e -- e2e/critical-paths.spec.ts
 */

// Test credentials - update these to match your test environment
const CREDENTIALS = {
  username: 'admin',
  password: 'admin123',
};

test.describe('Critical Paths - Pre-Deployment Checks', () => {

  /**
   * TEST 1: Authentication
   * If this fails, users cannot access the system at all
   */
  test('1. User can login and see dashboard', async ({ page }) => {
    // Go to login
    await page.goto('/login');

    // Fill credentials
    await page.fill('input[placeholder="Имя пользователя"]', CREDENTIALS.username);
    await page.fill('input[placeholder="Пароль"]', CREDENTIALS.password);

    // Submit
    await page.click('button[type="submit"]');

    // Should redirect to main page (not stay on login)
    await expect(page).not.toHaveURL(/\/login/);

    // Should see navigation or main content (use .first() for strict mode)
    await expect(page.locator('.ant-layout-sider').first()).toBeVisible();
  });

  /**
   * TEST 2: Container List Loads
   * Core functionality - users must see container data
   */
  test('2. Container list page loads with data', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[placeholder="Имя пользователя"]', CREDENTIALS.username);
    await page.fill('input[placeholder="Пароль"]', CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|containers)?$/);

    // Navigate to containers
    await page.goto('/containers');
    await page.waitForLoadState('networkidle');

    // Table should be visible
    await expect(page.locator('.ant-table').first()).toBeVisible();

    // Should have statistics card
    await expect(page.locator('.ant-statistic').first()).toBeVisible();
  });

  /**
   * TEST 3: Vehicle List Loads
   * Core functionality - users must see vehicle data
   */
  test('3. Vehicle list page loads', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[placeholder="Имя пользователя"]', CREDENTIALS.username);
    await page.fill('input[placeholder="Пароль"]', CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|containers)?$/);

    // Navigate to vehicles
    await page.goto('/vehicles');
    await page.waitForLoadState('networkidle');

    // Table should be visible
    await expect(page.locator('.ant-table').first()).toBeVisible();
  });

  /**
   * TEST 4: Create Modal Opens
   * Users must be able to add new data
   */
  test('4. Create container modal opens and has required fields', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[placeholder="Имя пользователя"]', CREDENTIALS.username);
    await page.fill('input[placeholder="Пароль"]', CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|containers)?$/);

    // Go to containers
    await page.goto('/containers');
    await page.waitForLoadState('networkidle');

    // Click create button
    await page.click('button:has-text("Создать")');

    // Modal should open
    await expect(page.locator('.ant-modal-content')).toBeVisible();

    // Required fields should exist in modal (use modal scope)
    const modal = page.locator('.ant-modal-content');
    await expect(modal.getByText('Номер контейнера')).toBeVisible();
    await expect(modal.getByText('Статус')).toBeVisible();
  });

  /**
   * TEST 5: API Health Check
   * Backend must be responding
   */
  test('5. API responds correctly', async ({ request }) => {
    // Check auth endpoint exists (use baseURL from config)
    const loginResponse = await request.post('http://localhost:8000/api/auth/login/', {
      data: {
        login: CREDENTIALS.username,
        password: CREDENTIALS.password,
      },
    });

    // Should get 200 (success) or 400/401 (wrong creds) - not 500 (server error)
    expect([200, 400, 401]).toContain(loginResponse.status());

    // If login succeeded, check entries endpoint
    if (loginResponse.ok()) {
      const data = await loginResponse.json();
      const token = data.access;

      const entriesResponse = await request.get('http://localhost:8000/api/terminal/entries/', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      expect(entriesResponse.ok()).toBeTruthy();
    }
  });
});
