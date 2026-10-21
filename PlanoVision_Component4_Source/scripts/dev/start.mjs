import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import http from 'node:http';
import net from 'node:net';

export const root=fileURLToPath(new URL('../../',import.meta.url));
export function getPort(value,fallback){
  if(value===undefined)return fallback;
  if(!/^\d+$/.test(value)||Number(value)<1||Number(value)>65535)throw Error('Ports must be integers from 1 to 65535.');
  return Number(value);
}
export function findPython(base=root,platform=process.platform){
  const suffix=platform==='win32'?'Scripts/python.exe':'bin/python';
  const candidates=['.venv','backend/.venv','work/component4_ml_venv'].map(p=>path.join(base,p,suffix));
  return candidates.find(existsSync);
}
function available(port){return new Promise((resolve,reject)=>{const s=net.createServer();s.once('error',()=>reject(Error(`Port ${port} is already in use. Close the old app terminal first. No existing process was stopped.`)));s.listen(port,'127.0.0.1',()=>s.close(resolve));});}
function ping(port){return new Promise(resolve=>{const req=http.get(`http://127.0.0.1:${port}/api/planner/storage`,r=>{let body='';r.on('data',chunk=>body+=chunk);r.on('end',()=>{try{resolve(r.statusCode===200&&JSON.parse(body).version==='planner-records.1');}catch{resolve(false);}});});req.setTimeout(1500,()=>req.destroy());req.on('error',()=>resolve(false));});}

export async function main(mode=process.argv[2]??'all'){
  if(!['all','frontend','backend'].includes(mode))throw Error('Use npm run dev, dev:frontend or dev:backend.');
  const apiPort=getPort(process.env.PLANOVISION_API_PORT,8765),webPort=getPort(process.env.PLANOVISION_WEB_PORT,5173);
  if(apiPort===webPort)throw Error('Frontend and backend need different ports.');
  const children=[];let stopping=false;
  const stop=(code=0)=>{if(stopping)return;stopping=true;for(const c of children)if(c.exitCode===null)c.kill('SIGTERM');process.exitCode=code;};
  const child=(exe,args,cwd)=>{const p=spawn(exe,args,{cwd,stdio:'inherit',env:{...process.env,PYTHONUNBUFFERED:'1',PLANOVISION_API_PORT:String(apiPort),PLANOVISION_WEB_PORT:String(webPort)}});children.push(p);p.once('error',e=>{console.error(e.message);stop(1);});p.once('exit',code=>{if(!stopping)stop(code??1);});return p;};
  process.once('SIGINT',()=>stop(0));process.once('SIGTERM',()=>stop(0));
  try{
    if(mode!=='frontend'){
      const python=findPython();
      if(!python)throw Error('Python environment missing. From this folder run: py -3.12 -m venv .venv, then .venv\\Scripts\\python.exe -m pip install -r backend/requirements.txt');
      await available(apiPort);
      child(python,[path.join(root,'backend/app.py'),'--port',String(apiPort)],root);
      const until=Date.now()+60000;
      while(!stopping&&Date.now()<until){if(await ping(apiPort))break;await new Promise(resolve=>setTimeout(resolve,250));}
      if(stopping)throw Error('Backend exited before becoming ready. Check the Python error above.');
      if(!await ping(apiPort))throw Error('Backend did not become ready within 60 seconds.');
    }
    if(mode!=='backend'){
      const vite=path.join(root,'frontend/node_modules/vite/bin/vite.js');
      if(!existsSync(vite))throw Error('Frontend dependencies missing. Run npm install from the project root.');
      await available(webPort);
      child(process.execPath,[vite,'--host','127.0.0.1','--port',String(webPort),'--strictPort'],path.join(root,'frontend'));
      console.log(`\nFrontend: http://127.0.0.1:${webPort}\nBackend: http://127.0.0.1:${apiPort}\nAPI requests proxy to Python. Ctrl+C stops only processes started by this command.\n`);
    }
  }catch(e){stop(1);throw e;}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{console.error(e.message);process.exitCode=1;});
