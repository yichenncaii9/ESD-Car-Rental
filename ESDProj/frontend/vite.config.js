import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  optimizeDeps: {
    include: ['@fawmi/vue-google-maps', 'fast-deep-equal']
  },
  server: {
    port: 8080,
    host: true
  }
})
