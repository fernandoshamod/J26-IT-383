import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const backendPort = Number(process.env.PP1_BACKEND_PORT || 8765);
const companionPort = Number(process.env.PP1_COMPANION_PORT || 8768);
const scenePort = Number(process.env.PP1_SCENE_PORT || 8769);
const frontendPort = Number(process.env.PP1_FRONTEND_PORT || 5173);
const proxy = { '/api': { target: `http://127.0.0.1:${backendPort}`, changeOrigin: true, rewrite: (p: string) => p.replace(/^\/api/, '') }, '/companion': { target: `http://127.0.0.1:${companionPort}`, changeOrigin: true, rewrite: (p: string) => p.replace(/^\/companion/, '') }, '/scene': { target: `http://127.0.0.1:${scenePort}`, changeOrigin: true } };
export default defineConfig({ plugins: [react()], server: { port: frontendPort, strictPort: true, proxy }, preview: {port:frontendPort,strictPort:true,proxy} });
