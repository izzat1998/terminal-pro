import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3002,
  },
  optimizeDeps: {
    exclude: [
      'playwright',
      'playwright-core',
      'chromium-bidi',
      // Exclude Playwright adapter files from optimization
      './src/adapters/FrontendAdapter',
      './src/adapters/TelegramAdapter',
    ],
  },
  build: {
    rollupOptions: {
      external: [
        'playwright',
        'playwright-core',
        'chromium-bidi',
        // Exclude all internal playwright dependencies
        /chromium-bidi/,
      ],
    },
  },
  // Ignore errors from playwright dependencies during dev
  esbuild: {
    logOverride: {
      'unsupported-require-call': 'silent',
    },
  },
})
