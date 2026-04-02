import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/src/lib/echarts.js')) {
            return 'echarts-runtime'
          }

          if (!id.includes('node_modules')) {
            return null
          }

          if (id.includes('element-plus') || id.includes('@element-plus')) {
            return 'element-plus'
          }

          if (id.includes('echarts')) {
            return 'echarts-core'
          }

          if (id.includes('zrender')) {
            return 'zrender'
          }

          if (id.includes('@vueup/vue-quill') || id.includes('quill')) {
            return 'editor'
          }

          if (id.includes('vue-router')) {
            return 'router'
          }

          if (id.includes('pinia')) {
            return 'store'
          }

          if (id.includes('axios')) {
            return 'http'
          }

          if (id.includes('vue')) {
            return 'vue-core'
          }

          return 'vendor'
        }
      }
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
