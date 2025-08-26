import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8004',
      '/ws': {
        target: 'ws://localhost:8004',
        ws: true
      },
      '/ws/canvas': {
        target: 'ws://localhost:8004',
        ws: true
      }
    }
  }
})
