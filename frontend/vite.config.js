import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiProxyConfig = {
  target: 'http://localhost:8000',
  bypass: (req) => {
    if (req.headers.accept && req.headers.accept.includes('text/html')) {
      return '/index.html';
    }
  },
};

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': apiProxyConfig,
      '/agents': apiProxyConfig,
      '/events': apiProxyConfig,
      '/ledger': apiProxyConfig,
      '/alerts': apiProxyConfig,
      '/attacks': apiProxyConfig,
      '/anomalies': apiProxyConfig,
      '/graph': apiProxyConfig,
      '/contracts': apiProxyConfig,
      '/enforcement': apiProxyConfig,
      '/trust': apiProxyConfig,
      '/missions': apiProxyConfig,
      '/api': apiProxyConfig,
    },
  },
});
