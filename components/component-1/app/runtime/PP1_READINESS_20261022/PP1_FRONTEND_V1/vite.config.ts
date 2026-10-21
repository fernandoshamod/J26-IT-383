import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const proxy = { '/api': { target: 'http://127.0.0.1:8765', changeOrigin: true, rewrite: (p: string) => p.replace(/^\/api/, '') }, '/companion': { target: 'http://127.0.0.1:8768', changeOrigin: true, rewrite: (p: string) => p.replace(/^\/companion/, '') }, '/scene': { target: 'http://127.0.0.1:8769', changeOrigin: true } };
export default defineConfig({ plugins: [react()], server: { port: 5173, strictPort: true, proxy }, preview: {port:5173,strictPort:true,proxy} });
