import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  webServer: {
    command: "node scripts/serve-static-subpath.mjs",
    url: "http://127.0.0.1:4183/theatre/cuemaster/",
    reuseExistingServer: false
  },
  use: {
    baseURL: "http://127.0.0.1:4183/theatre/cuemaster/",
    trace: "on-first-retry"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
