/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path' // Node.js path module for resolving aliases

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Allows using '@/' as an alias for the 'src' directory in imports
      '@': path.resolve(__dirname, './src'), 
    },
  },
  server: {
    port: 3000, // Port for the Vite development server
    proxy: {
      // Proxy API requests starting with '/api' to the backend server during development
      // This avoids CORS issues when backend and frontend run on different ports.
      '/api': {
        target: 'http://127.0.0.1:8000', // Backend's address and port
        changeOrigin: true, // Recommended for virtual hosted sites
        // secure: false, // Uncomment if your backend is HTTP and you encounter proxy errors
        // rewrite: (path) => path.replace(/^\/api/, '/api/v1') // Example if backend has /api/v1 prefix
      },
    },
  },
  test: { // Vitest configuration
    globals: true, // Allows using Vitest's global APIs (describe, it, expect) without imports
    environment: 'jsdom', // Simulates a browser environment for tests
    setupFiles: './src/setupTests.js', // Path to your test setup file
    css: true, // Enables processing CSS files during component tests
    coverage: { // Optional: configure code coverage
      provider: 'v8', // or 'istanbul'
      reporter: ['text', 'json', 'html'],
    },
  },
})