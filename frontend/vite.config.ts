import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
  ],
  build: {
    rollupOptions: {
      output: {
        // Almost all of the main entry chunk's size is third-party code
        // (react-dom, Chakra UI + its Ark UI/Zag machine dependencies,
        // axios, react-router, react-query) that changes only on a
        // dependency bump — actual app source is a small fraction of it.
        // Splitting node_modules into its own chunk keeps that large,
        // rarely-changing payload under a stable content hash, so a
        // deploy that only touches app code doesn't force every
        // returning visitor to re-download it.
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        },
      },
    },
  },
});
