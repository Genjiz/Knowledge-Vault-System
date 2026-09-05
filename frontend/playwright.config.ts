import { defineConfig } from '@playwright/test'

const port = process.env.PLAYWRIGHT_PORT || '4173'
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:' + port
const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  reporter: 'list',
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command:
          'node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port ' + port + ' --strictPort',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
  use: {
    baseURL,
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
    launchOptions: executablePath ? { executablePath } : undefined,
  },
})
