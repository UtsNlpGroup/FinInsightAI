import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// When running inside Docker the Vite dev server proxies to the backend
// container via its internal service name.  Outside Docker (plain npm run dev)
// the backend is reachable at localhost:8001.
const API_TARGET = process.env.API_TARGET ?? 'http://localhost:8001'

export default defineConfig({
  base: '/FinInsightAI/',
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: true,   // bind to 0.0.0.0 so Docker can expose it
    port: 5173,
    proxy: {
      // All /api/* calls are forwarded to the FastAPI backend.
      // The browser never sees a cross-origin request.
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})
