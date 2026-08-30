import { test, expect } from '@playwright/test';

const EMAIL = `e2e-${Date.now()}@example.com`;
const PASSWORD = 'e2ePassword123!';
const ORG = 'E2E Test Airline';

test('full flight planning flow: register, create, calculate, dispatch, generate PDF', async ({ page }) => {
  // 1. Register
  await page.goto('http://localhost:5173/register');
  const emailInput = page.locator('input[type="email"]');
  const textInputs = page.locator('input[type="text"], input:not([type])');
  const passwordInput = page.locator('input[type="password"]').first();
  await emailInput.fill(EMAIL);
  await textInputs.nth(0).fill('E2E Pilot');
  await passwordInput.fill(PASSWORD);
  await textInputs.nth(1).fill(ORG);
  await page.getByRole('button', { name: /create account/i }).click();
  await expect(page).toHaveURL(/localhost:5173\/?$/);

  // 2. Dashboard
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  // 3. New flight plan
  await page.getByRole('link', { name: /new flight plan/i }).first().click();
  await expect(page.getByRole('heading', { name: 'New Flight Plan' })).toBeVisible();

  // Fill departure + arrival
  await page.locator('#od-airport-dep').fill('VABB');
  await page.locator('#od-airport-arr').fill('VIDP');

  // Set passengers + cargo
  await page.locator('#od-pax').fill('150');
  await page.locator('#od-cargo').fill('1200');

  // Set cruise altitude
  await page.locator('#od-cruise-alt').fill('35000');

  // Set the route
  await page.locator('#od-route-text').fill('VABB DCT BOM A466 GADIN A466 DEL DCT VIDP');

  // 4. Create the draft
  await page.getByRole('button', { name: /create draft/i }).click();
  await expect(page.getByText(/flight plan created/i)).toBeVisible({ timeout: 10000 });

  // 5. Calculate
  await page.getByRole('button', { name: /calculate/i }).click();
  await expect(page.getByText('Calculated', { exact: true })).toBeVisible({ timeout: 15000 });
  // Verify the status chip changed to CALCULATED
  await expect(page.getByText('CALCULATED', { exact: true })).toBeVisible();

  // Live summary should show distance > 0 and block fuel > 0
  await expect(page.getByText(/Distance/i).first()).toBeVisible();
  await expect(page.getByText(/Block fuel/i).first()).toBeVisible();

  // 6. Generate documents
  await page.getByRole('button', { name: /generate documents/i }).click();
  await expect(page.getByText(/documents generated/i)).toBeVisible({ timeout: 30000 });

  // 7. Open detail
  await page.getByRole('button', { name: /open detail/i }).click();
  await expect(page.getByRole('heading', { name: /VABB|VIDP/ })).toBeVisible();

  // Tabs
  for (const tab of ['Route', 'NavLog', 'Fuel', 'Weights', 'Warnings', 'Documents']) {
    await page.getByRole('button', { name: tab }).first().click();
  }

  // Documents tab should show 4 documents
  await page.getByRole('button', { name: 'Documents' }).first().click();
  await expect(page.getByText('OFP').first()).toBeVisible();
  await expect(page.getByText('NAV_LOG').first()).toBeVisible();

  // 8. Dispatch
  page.once('dialog', (d) => d.accept());
  await page.getByRole('button', { name: /dispatch/i }).click();
  await expect(page.getByText('Dispatched', { exact: true })).toBeVisible({ timeout: 10000 });

  // After dispatch, button shows "Dispatched ✓"
  await expect(page.getByRole('button', { name: 'Dispatched ✓' })).toBeVisible();
});
