import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    // `npm run dev` talks to a local backend: uvicorn app.main:app --port 8000
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: { target: 'es2022', assetsInlineLimit: 0 },
});
