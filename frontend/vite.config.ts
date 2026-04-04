import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

function manualChunks(id: string) {
  if (!id.includes('node_modules')) {
    return undefined;
  }

  if (id.includes('zrender')) {
    return 'vendor-zrender';
  }

  if (id.includes('echarts-for-react')) {
    return 'vendor-echarts-react';
  }

  if (id.includes('echarts')) {
    return 'vendor-echarts';
  }

  if (id.includes('react-router') || id.includes('@remix-run')) {
    return 'vendor-router';
  }

  if (id.includes('@tanstack/react-query') || id.includes('axios')) {
    return 'vendor-data';
  }

  if (id.includes('framer-motion')) {
    return 'vendor-motion';
  }

  if (id.includes('react') || id.includes('scheduler')) {
    return 'vendor-react';
  }

  return 'vendor-misc';
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18080',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
});
