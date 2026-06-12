import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        manualChunks(id: string): string | undefined {
          if (id.includes('@mui/icons-material')) return 'vendor-mui-icons';
          if (id.includes('@mui/material') || id.includes('@emotion')) return 'vendor-mui';
          if (id.includes('recharts') || id.includes('d3-')) return 'vendor-charts';
          if (id.includes('node_modules/react') || id.includes('react-router')) return 'vendor-react';
          return undefined;
        },
      },
    },
  },
})
