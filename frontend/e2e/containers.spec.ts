import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForModal, waitForSuccessMessage, waitForErrorMessage, fillAntSelect, selectAntRadio } from './helpers/auth';

/**
 * Container Entry Modal E2E Tests
 *
 * Tests all form field combinations for creating and editing container entries
 */

test.describe('Container Entry Modal', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/containers');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Create Container Modal', () => {
    test('should open create modal', async ({ page }) => {
      // Click create button (actual text: "Создать контейнер")
      await page.click('button:has-text("Создать контейнер")');
      await waitForModal(page);

      // Verify modal is visible
      await expect(page.locator('.ant-modal-content')).toBeVisible();
    });

    test('should validate required fields', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Создать")');
      await waitForModal(page);

      // Try to submit empty form
      await page.click('.ant-modal-footer button.ant-btn-primary');

      // Should show validation errors
      await expect(page.locator('.ant-form-item-explain-error')).toBeVisible();
    });

    test('should create container with all required fields', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Создать")');
      await waitForModal(page);

      // Fill required fields
      await page.fill('input[name="container_number"], input[placeholder*="MSKU"]', 'MSKU1234567');

      // Select ISO type
      await fillAntSelect(page, '.ant-select:has(input[id*="iso"])', '22G1');

      // Select status
      await selectAntRadio(page, '[class*="status"], .ant-radio-group', 'Порожний');

      // Select transport type
      await selectAntRadio(page, '[class*="transport"], .ant-radio-group', 'Авто');

      // Fill transport number
      await page.fill('input[name="transport_number"], input[placeholder*="транспорт"]', '01A123BC');

      // Select company (if required)
      const companySelect = page.locator('.ant-select:has(input[id*="company"])');
      if (await companySelect.isVisible()) {
        await companySelect.click();
        await page.click('.ant-select-item-option:first-child');
      }

      // Submit
      await page.click('.ant-modal-footer button.ant-btn-primary');

      // Should show success message
      await waitForSuccessMessage(page);
    });

    test('should validate container number format', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Создать")');
      await waitForModal(page);

      // Fill invalid container number
      await page.fill('input[name="container_number"], input[placeholder*="MSKU"]', 'INVALID');

      // Trigger validation (blur or submit)
      await page.click('.ant-modal-title');

      // Should show format error
      await expect(page.locator('.ant-form-item-explain-error')).toContainText(/формат|4 буквы|7 цифр/i);
    });

    test('should create LADEN container with cargo info', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Создать")');
      await waitForModal(page);

      // Fill required fields
      await page.fill('input[name="container_number"], input[placeholder*="MSKU"]', 'HDMU7654321');
      await fillAntSelect(page, '.ant-select:has(input[id*="iso"])', '42G1');
      await selectAntRadio(page, '[class*="status"], .ant-radio-group', 'Гружёный');
      await selectAntRadio(page, '[class*="transport"], .ant-radio-group', 'Авто');
      await page.fill('input[name="transport_number"], input[placeholder*="транспорт"]', '01B456CD');

      // Fill optional cargo fields
      const cargoNameInput = page.locator('input[name="cargo_name"], input[placeholder*="груз"]');
      if (await cargoNameInput.isVisible()) {
        await cargoNameInput.fill('Электроника');
      }

      const cargoWeightInput = page.locator('input[name="cargo_weight"], input[placeholder*="вес"]');
      if (await cargoWeightInput.isVisible()) {
        await cargoWeightInput.fill('15000');
      }

      // Submit
      await page.click('.ant-modal-footer button.ant-btn-primary');
      await waitForSuccessMessage(page);
    });
  });

  test.describe('Edit Container Modal', () => {
    test('should open edit modal with pre-filled data', async ({ page }) => {
      // Click edit on first row
      await page.click('table tbody tr:first-child button:has-text("Редактировать"), table tbody tr:first-child .ant-btn:has([class*="edit"])');
      await waitForModal(page);

      // Verify fields are pre-filled
      const containerNumberInput = page.locator('input[name="container_number"], input[placeholder*="MSKU"]');
      await expect(containerNumberInput).not.toBeEmpty();
    });

    test('should update container via PATCH', async ({ page }) => {
      // Click edit on first row
      await page.click('table tbody tr:first-child button:has-text("Редактировать"), table tbody tr:first-child .ant-btn:has([class*="edit"])');
      await waitForModal(page);

      // Change a field (e.g., location)
      const locationInput = page.locator('input[name="location"], input[placeholder*="место"]');
      if (await locationInput.isVisible()) {
        await locationInput.fill('Zone A-Updated');
      }

      // Submit
      await page.click('.ant-modal-footer button.ant-btn-primary');
      await waitForSuccessMessage(page);
    });
  });

  test.describe('Delete Container', () => {
    test('should show confirmation before delete', async ({ page }) => {
      // Click delete on first row
      await page.click('table tbody tr:first-child button:has-text("Удалить"), table tbody tr:first-child .ant-btn-dangerous');

      // Should show confirmation modal
      await expect(page.locator('.ant-modal-confirm, .ant-popconfirm')).toBeVisible();
    });
  });
});
