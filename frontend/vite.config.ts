import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        // 如果后端需要通过 Clash 代理访问外部 API，取消下面的注释
        // configure: (proxy, options) => {
        //   proxy.on('proxyReq', (proxyReq, req, res) => {
        //     proxyReq.setHeader('X-Forwarded-For', req.socket.remoteAddress)
        //   })
        // }
      },
      '/ws': {
        target: 'ws://localhost:5000',
        ws: true,
      },
    },
  },
})
