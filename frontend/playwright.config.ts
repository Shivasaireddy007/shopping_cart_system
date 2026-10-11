import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests against a running stack (Docker Compose in CI, or local dev servers).
 *   E2E_BASE_URL=http://localhost:8080 npx playwright test
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:8080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      // PLAYWRIGHT_CHANNEL=chrome uses an installed Chrome instead of Playwright's download.
      use: { ...devices['Desktop Chrome'], channel: process.env.PLAYWRIGHT_CHANNEL },
    },
  ],
})
