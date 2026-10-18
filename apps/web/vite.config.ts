import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api/c3': { target: 'http://127.0.0.1:8033', changeOrigin: true, rewrite: (path) => path.replace(/^\/api\/c3/, '') } },
  },
});
