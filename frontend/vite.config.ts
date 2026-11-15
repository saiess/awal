import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'serve' ? '/' : '/static/ui/',
  build: { outDir: '../app/static/ui', emptyOutDir: true, manifest: true, sourcemap: false },
  server: {
    host: '127.0.0.1', port: 3000, strictPort: true,
    // Preserve Host so the existing same-origin write protection also works in development.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
      '/static': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
}));
