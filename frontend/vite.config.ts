import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig({
  // VITE_* vars live in the repo root .env/.env.example, not frontend/.env -
  // one file for both the dev server (loaded here) and the production build
  // (docker-compose.prod.yml's build args, sourced from the same root .env
  // via Compose's own interpolation. See .env.example).
  envDir: '..',
  plugins: [
    react(),
  ],
  resolve: {
    // Must match the "@"/"@app" paths in tsconfig.app.json and the
    // resolve.alias in vitest.config.ts, or dev-server/build-time
    // resolution of "@/..." and "@app/..." imports diverges from what
    // typecheck/tests see.
    alias: {
      '@': path.resolve(dirname, 'src/mystic_auth'),
      '@app': path.resolve(dirname, 'src/app'),
    },
  },
  // No custom build.rollupOptions.output.manualChunks here: a prior
  // version forced every node_modules import into one "vendor" chunk for
  // better long-term caching (rarely-changing third-party code under a
  // stable hash, separate from app code that changes every deploy). That
  // broke production: app/src files like api/axiosInstance.ts both import
  // from and get imported by that vendor chunk, and Rollup placed shared
  // CJS-interop helpers into axiosInstance's own chunk, creating a real
  // circular chunk dependency. ESM's live-binding semantics for circular
  // imports meant vendor.js called a binding from axiosInstance.js's chunk
  // before that chunk's module body had run far enough to define it,
  // throwing "TypeError: t is not a function" at the very top of the
  // vendor bundle: the whole app failed to mount, a blank page with no
  // build-time warning. Reverting to Rollup's own automatic chunking
  // (its default module-graph analysis doesn't create this circular
  // dependency) trades away that caching optimization for a build that
  // actually works. Re-introduce chunking later only with real production
  // verification (not just curl on the built files) that nothing crashes.
});
