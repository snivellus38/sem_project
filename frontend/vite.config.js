import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const backendPort = process.env.VITE_BACKEND_PORT || '8000'
const backendHttpTarget = `http://127.0.0.1:${backendPort}`
const backendWsTarget = `ws://127.0.0.1:${backendPort}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  optimizeDeps: {
    // Ensure CJS/ESM interop dependencies are pre-bundled for browser compatibility.
    include: [
      '@react-three/drei',
      '@react-three/fiber',
      'three',
      'three-stdlib',
      'zustand',
      'use-sync-external-store/shim/with-selector',
    ],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': backendHttpTarget,
      '/ws': {
        target: backendWsTarget,
        ws: true,
      },
    },
  },
})
