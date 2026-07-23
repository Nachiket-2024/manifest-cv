import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  // VITE_* vars live in the repo root .env/.env.example, not frontend/.env —
  // one file for both the dev server (loaded here) and the production build
  // (docker-compose.prod.yml's build args, sourced from the same root .env
  // via Compose's own interpolation — see .env.example).
  envDir: '..',
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
