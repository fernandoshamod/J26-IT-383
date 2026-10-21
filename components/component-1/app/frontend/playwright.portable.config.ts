import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: 'portable-acceptance.spec.ts',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: 'list',
  use: {
    baseURL: `http://127.0.0.1:${process.env.PP1_FRONTEND_PORT || '5173'}`,
    browserName: 'chromium',
    channel: 'chrome',
    headless: true,
    trace: 'retain-on-failure',
  },
  outputDir: '../runtime-state/playwright-portable-002',
});
