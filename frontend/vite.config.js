import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 端口由桌面启动器注入，未注入时回落到手工开发使用的默认值。
const backendPort = process.env.KV_BACKEND_PORT || '5000'
const frontendPort = Number(process.env.KV_FRONTEND_PORT) || 3000
const backendTarget = `http://localhost:${backendPort}`

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
    // 显式绑定 IPv4 回环：Node 17+ 对 localhost 可能优先解析为 IPv6（::1），
    // 会导致 127.0.0.1 形式的访问与启动器探测失败。
    host: '127.0.0.1',
    port: frontendPort,
    // 端口由启动器分配时必须锁定：一旦静默顺延，启动器打开的仍是它记下的端口。
    strictPort: Boolean(process.env.KV_FRONTEND_PORT),
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true
      },
      '/uploads': {
        target: backendTarget,
        changeOrigin: true
      }
    }
  }
})
