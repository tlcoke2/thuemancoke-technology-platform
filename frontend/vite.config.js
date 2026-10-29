import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const configured = env.VITE_SOFTWARE_API_URL;
  if (mode === 'staging' && !configured) throw new Error('Staging requires VITE_SOFTWARE_API_URL');
  const api = new URL(configured || 'https://api.thuemancokelimited.com');
  if (api.protocol !== 'https:' || api.username || api.password || api.search || api.hash || api.pathname !== '/') {
    throw new Error('Software API must be an HTTPS origin without credentials or path');
  }
  if (mode === 'staging' && api.hostname === 'api.thuemancokelimited.com') {
    throw new Error('Staging must not use production software intake');
  }
  return {
  // Isolate the existing contact form as well as software/CRM pages in staging.
  define: mode === 'staging' ? { 'import.meta.env.VITE_API_URL': JSON.stringify(api.origin) } : {},
  plugins: [react(), {
    name: 'software-api-config',
    generateBundle() {
      this.emitFile({ type: 'asset', fileName: 'software-config.js',
        source: `window.TCL_SOFTWARE_API = ${JSON.stringify(api.origin)};\n` });
    },
  }],
  base: "./",
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  };
});
