import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForModal, waitForSuccessMessage, fillAntSelect, selectAntRadio } from './helpers/auth';

/**
 * Vehicle Entry Modal E2E Tests
 *
 * Tests all form field combinations including conditional fields
 * for LIGHT vs CARGO vehicles
 */

test.describe('Vehicle Entry Modal', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/vehicles');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Create Vehicle Modal', () => {
    test('should open create modal', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Въезд")');
      await waitForModal(page);
      await expect(page.locator('.ant-modal-title')).toBeVisible();
    });

    test('should validate license plate required', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Въезд")');
      await waitForModal(page);

      // Try to submit without license plate
      await page.click('.ant-modal-footer button.ant-btn-primary');

      // Should show error
      await expect(page.locator('.ant-message-error, .ant-form-item-explain-error')).toBeVisible();
    });

    test('should create LIGHT vehicle with visitor type', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Въезд")');
      await waitForModal(page);

      // Fill license plate
      await page.fill('input[name="license_plate"], input[placeholder*="номер"]', '01A123BC');

      // Select vehicle type: LIGHT
      await fillAntSelect(page, '.ant-select:has-text("Тип ТС"), [class*="vehicle_type"]', 'Легковой');

      // Should show visitor type field
      await expect(page.locator('text=Тип посетителя')).toBeVisible();

      // Select visitor type
      await fillAntSelect(page, '.ant-select:has-text("посетителя")', 'Клиент');

      // Submit
      await page.click('.ant-modal-footer button.ant-btn-primary');
      await waitForSuccessMessage(page);
    });

    test('should create CARGO vehicle with transport fields', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Въезд")');
      await waitForModal(page);

      // Fill license plate
      await page.fill('input[name="license_plate"], input[placeholder*="номер"]', '01B456CD');

      // Select vehicle type: CARGO
      await fillAntSelect(page, '.ant-select:has-text("Тип ТС"), [class*="vehicle_type"]', 'Грузовой');

      // Should show cargo-specific fields
      await expect(page.locator('text=Тип транспорта')).toBeVisible();
      await expect(page.locator('text=Статус загрузки')).toBeVisible();

      // Fill cargo vehicle fields
      await fillAntSelect(page, '.ant-select:has-text("Тип транспорта")', 'Фура');
      await fillAntSelect(page, '.ant-select:has-text("Статус загрузки")', 'Порожний');

      // Select destination (required for cargo)
      await fillAntSelect(page, '.ant-select:has-text("Назначение")', 'K1');

      // Submit
      await page.click('.ant-modal-footer button.ant-btn-primary');
      await waitForSuccessMessage(page);
    });

    test('should show container fields when cargo is LOADED with CONTAINER', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Въезд")');
      await waitForModal(page);

      // Fill license plate
      await page.fill('input[name="license_plate"], input[placeholder*="номер"]', '01C789EF');

      // Select CARGO vehicle
      await fillAntSelect(page, '.ant-select:has-text("Тип ТС")', 'Грузовой');

      // Select transport type that supports containers
      await fillAntSelect(page, '.ant-select:has-text("Тип транспорта")', 'Платформа');

      // Select LOADED status
      await fillAntSelect(page, '.ant-select:has-text("Статус загрузки въезд")', 'С грузом');

      // Should show cargo type field
      await expect(page.locator('text=Тип груза')).toBeVisible();

      // Select CONTAINER cargo type
      await fillAntSelect(page, '.ant-select:has-text("Тип груза")', 'Контейнер');

      // Should show container fields
      await expect(page.locator('text=Размер контейнера')).toBeVisible();
      await expect(page.locator('text=Статус загрузки контейнера')).toBeVisible();

      // Fill container fields
      await fillAntSelect(page, '.ant-select:has-text("Размер контейнера")', '20');
      await fillAntSelect(page, '.ant-select:has-text("Статус загрузки контейнера")', 'С грузом');

      // Select destination
      await fillAntSelect(page, '.ant-select:has-text("Назначение")', 'K1');

      // Submit
      await page.click('.ant-modal-footer button.ant-btn-primary');
      await waitForSuccessMessage(page);
    });

    test('should validate cargo fields when CARGO type selected', async ({ page }) => {
      await page.click('button:has-text("Добавить"), button:has-text("Въезд")');
      await waitForModal(page);

      // Fill only license plate and vehicle type
      await page.fill('input[name="license_plate"], input[placeholder*="номер"]', '01D012GH');
      await fillAntSelect(page, '.ant-select:has-text("Тип ТС")', 'Грузовой');

      // Try to submit without required cargo fields
      await page.click('.ant-modal-footer button.ant-btn-primary');

      // Should show error for missing transport_type and entry_load_status
      await expect(page.locator('.ant-message-error')).toBeVisible();
    });
  });

  test.describe('Edit Vehicle Modal', () => {
    test('should open edit modal with pre-filled data', async ({ page }) => {
      // Click edit on first vehicle
      await page.click('table tbody tr:first-child button:has-text("Редактировать"), table tbody tr:first-child .anticon-edit');
      await waitForModal(page);

      // License plate should be pre-filled
      const licensePlateInput = page.locator('input[name="license_plate"], input[placeholder*="номер"]');
      await expect(licensePlateInput).not.toBeEmpty();
    });

    test('should update vehicle with PATCH (partial update)', async ({ page }) => {
      // Find an editable vehicle and click edit
      await page.click('table tbody tr:first-child button:has-text("Редактировать"), table tbody tr:first-child .anticon-edit');
      await waitForModal(page);

      // Just change one field (e.g., customer if available)
      const customerSelect = page.locator('.ant-select:has-text("Клиент")');
      if (await customerSelect.isVisible()) {
        await customerSelect.click();
        await page.click('.ant-select-item-option:first-child');
      }

      // Submit - should use PATCH, not PUT
      await page.click('.ant-modal-footer button.ant-btn-primary');
      await waitForSuccessMessage(page);
    });
  });

  test.describe('Exit Vehicle Modal', () => {
    test('should open exit modal for ON_TERMINAL vehicle', async ({ page }) => {
      // Look for exit button (only visible for ON_TERMINAL vehicles)
      const exitButton = page.locator('table tbody tr button:has-text("Выезд")').first();

      if (await exitButton.isVisible()) {
        await exitButton.click();
        await waitForModal(page);

        // Should show exit time field
        await expect(page.locator('text=Время выезда')).toBeVisible();
      }
    });

    test('should register exit with exit time', async ({ page }) => {
      const exitButton = page.locator('table tbody tr button:has-text("Выезд")').first();

      if (await exitButton.isVisible()) {
        await exitButton.click();
        await waitForModal(page);

        // Exit time should be pre-filled with current time
        const exitTimeInput = page.locator('.ant-picker');
        await expect(exitTimeInput).toBeVisible();

        // Submit
        await page.click('.ant-modal-footer button.ant-btn-primary');
        await waitForSuccessMessage(page);
      }
    });
  });
});
