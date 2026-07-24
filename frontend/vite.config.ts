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
      '/dashboard': 'http://localhost:8000',
    },
  },
})
