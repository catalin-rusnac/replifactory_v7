import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
      alias: {
      '@': '/src'
      }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://192.168.56.113:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
