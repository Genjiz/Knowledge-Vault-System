import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const backendPort = process.env.KV_BACKEND_PORT || '5000'
const frontendPort = Number(process.env.KV_FRONTEND_PORT) || 3000
const backendTarget = `http://localhost:${backendPort}`

export default defineConfig({
  plugins: [tailwindcss(), react()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: Boolean(process.env.KV_FRONTEND_PORT),
    proxy: {
      '/api': { target: backendTarget, changeOrigin: true },
      '/uploads': { target: backendTarget, changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.test.{ts,tsx}'],
    css: true,
  },
})
