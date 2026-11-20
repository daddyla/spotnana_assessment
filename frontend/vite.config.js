import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, proxy API calls to the backend so the app only ever uses relative
// URLs ("/api/..."). In Docker, nginx does the same job — no CORS either way.
//
// The target follows the same BACKEND_PORT that docker-compose uses (read from the
// repo-root .env), so `vite dev` and `docker-compose up` never disagree about where
// the backend lives. VITE_API_TARGET overrides everything.
export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, '..', ''); // '' prefix = load all keys, not just VITE_*
  const port = process.env.BACKEND_PORT || rootEnv.BACKEND_PORT || '8000';
  const apiTarget = process.env.VITE_API_TARGET || `http://localhost:${port}`;

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': apiTarget,
        '/health': apiTarget,
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/setupTests.js',
    },
  };
});
