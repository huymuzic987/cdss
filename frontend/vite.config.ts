import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const CANVAS_CHUNK_MAX_SIZE = 450 * 1024
const CANVAS_DEPENDENCY_GROUPS = [
  {
    name: 'tldraw',
    test: /node_modules[\\/]tldraw[\\/]/,
    minSize: 20 * 1024,
    maxSize: CANVAS_CHUNK_MAX_SIZE,
    priority: 2,
  },
  {
    name: 'elkjs',
    test: /node_modules[\\/]elkjs[\\/]/,
    minSize: 20 * 1024,
    maxSize: CANVAS_CHUNK_MAX_SIZE,
    priority: 1,
  },
]

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: CANVAS_DEPENDENCY_GROUPS,
        },
      },
    },
  },
  server: {
    proxy: {
      '/trees': 'http://localhost:8000',
      '/evaluate': 'http://localhost:8000',
      '/fhir': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/dashboard': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('html')) {
            return '/index.html'
          }
        },
      },
      '/contribution': {
        target: 'http://localhost:8000',
        bypass(req) {
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
