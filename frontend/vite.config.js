import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://localhost:8000',
      '/agents': 'http://localhost:8000',
      '/events': 'http://localhost:8000',
      '/ledger': 'http://localhost:8000',
      '/alerts': 'http://localhost:8000',
      '/attacks': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
    },
  },
});
