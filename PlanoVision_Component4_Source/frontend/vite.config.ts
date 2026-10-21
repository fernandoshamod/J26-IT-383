import {defineConfig} from 'vitest/config';
import {loadEnv} from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({mode})=>{
  const apiPort=loadEnv(mode,'.','PLANOVISION_').PLANOVISION_API_PORT??'8765';
  if(!/^\d+$/.test(apiPort)||Number(apiPort)<1||Number(apiPort)>65535)throw Error('Invalid PLANOVISION_API_PORT.');
  return {plugins:[react()],server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:'+apiPort,changeOrigin:true}}},test:{environment:'jsdom',setupFiles:['./src/test-setup.ts']}};
});
