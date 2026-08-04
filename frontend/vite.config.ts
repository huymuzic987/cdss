import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/trees': 'http://localhost:8000',
      '/evaluate': 'http://localhost:8000',
      '/fhir': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/dashboard': {
        target: 'http://localhost:8000',
        bypass: (req) => {
          if (req.headers.accept?.includes('html')) {
            return '/index.html'
          }
        },
      },

    },
    allowedHosts: [
      "cdss.click",
    ],
  },
})
