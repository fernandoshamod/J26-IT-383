import { test, expect } from '@playwright/test';

test('SQLite event workspace creates, updates, lists and deletes a real local record', async ({ page }) => {
  const eventName = `Portable acceptance event ${Date.now()}`;
  await page.goto('/');
  await expect(page.getByText('Backend connected', { exact: true })).toBeVisible();
  await page.locator('nav').getByRole('button', { name: 'My events', exact: true }).click();
  await page.getByRole('button', { name: 'Create event', exact: true }).click();
  await page.getByLabel('Event name').fill(eventName);
  await page.getByLabel('Venue name').fill('Disposable test hall');
  await page.getByRole('button', { name: 'Save local SQLite draft', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('saved in the local SQLite database');
  const created = await page.evaluate(() => fetch('/companion/event-projects').then(r => r.json()));
  expect(created.storage).toBe('local_sqlite');
  expect(created.projects.some((p: { name: string }) => p.name === eventName)).toBeTruthy();
  const id = created.projects.find((p: { name: string }) => p.name === eventName).id;
  await page.locator('.event-form-panel').getByRole('button', { name: 'My events' }).click();
  await page.getByRole('button', { name: `Open event ${eventName}` }).click();
  await page.getByRole('button', { name: 'Edit details' }).click();
  await page.getByLabel('Venue name').fill('Updated disposable hall');
  await page.getByRole('button', { name: 'Save local SQLite draft', exact: true }).click();
  expect((await page.evaluate((eventId) => fetch(`/companion/event-projects/${eventId}`).then(r => r.json()), id)).project.venue).toBe('Updated disposable hall');
  await page.locator('nav').getByRole('button', { name: 'My events', exact: true }).click();
  await page.getByRole('button', { name: `Archive event ${eventName}` }).click();
  const archived = page.locator('details.archived-events');
  await archived.locator('summary').click();
  await archived.getByRole('button', { name: 'Delete' }).click();
  expect((await page.evaluate(() => fetch('/companion/event-projects').then(r => r.json())).then((x: any) => x.projects)).some((p: any) => p.id === id)).toBeFalsy();
});

test('Scene compiler UI invokes the controlled compiler and renders actual alternatives', async ({ page }) => {
  await page.goto('/');
  await page.locator('nav').getByRole('button', { name: 'Scene compiler', exact: true }).click();
  await expect(page.getByTestId('scene-compiler')).toBeVisible();
  await page.getByLabel('Controlled scene state').selectOption('partially_furnished');
  const responsePromise = page.waitForResponse(r => r.url().includes('/scene/compile-and-optimize') && r.request().method() === 'POST');
  await page.getByTestId('compile-scene-run').click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  await expect(page.getByTestId('scene-result')).toBeVisible({ timeout: 120_000 });
  await expect(page.getByTestId('scene-result')).toContainText('Independent demand/allocation oracle: true');
  await expect.poll(() => page.getByRole('img', { name: 'Actual compiler bridge returned scene geometry' }).locator('polygon').count()).toBeGreaterThan(100);
  await expect(page.getByRole('button', { name: /Alternative 2/ })).toBeVisible();
});

test('Twin Editor without a fresh source stays pending and does not fabricate a registration', async ({ page }) => {
  await page.goto('/');
  await page.locator('nav').getByRole('button', { name: 'Twin editor', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Visual Twin review editor', exact: true })).toBeVisible();
  await expect(page.getByText(/Upload and analyze an image first/)).toBeVisible();
  await expect(page.getByRole('button', { name: /Validate|Register/i })).toHaveCount(0);
});
