import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  server: {
    // Proxy API requests to the FastAPI backend during development.
    // When the browser requests /api/chat, Vite forwards it to localhost:8000/api/chat.
    // This avoids CORS issues and lets us use relative URLs ("/api/...") everywhere.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
