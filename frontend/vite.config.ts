import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In development the API runs on :8000; the browser talks to it through this proxy.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // Node can't build requests from relative URLs, so tests use an absolute API address.
    env: { VITE_API_URL: 'http://localhost' },
  },
})
