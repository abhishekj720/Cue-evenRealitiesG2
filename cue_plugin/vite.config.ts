import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Bind to all interfaces so the phone (real G2 demo) can load the
    // plugin over the LAN. Port pinned so the evenhub qr output is stable.
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
})
