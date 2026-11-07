import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  // README.md, STATUS.md and the handoff all say localhost:5181, and nothing
  // was making that true: with no port set Vite starts at 5173 and walks up
  // until it finds a free one, so the documented URL only answered on a
  // machine that already had eight dev servers running. strictPort so a busy
  // 5181 fails loudly instead of silently landing somewhere else.
  server: { port: 5181, strictPort: true },
})
