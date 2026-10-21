import {spawnSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../',import.meta.url));
const required=['vite/bin/vite.js','typescript/bin/tsc','react/package.json','react-dom/package.json','vitest/vitest.mjs'];
if(required.every(p=>existsSync(new URL('../../frontend/node_modules/'+p,import.meta.url)))){
  console.log('Frontend dependencies already installed. Run npm run dev after Python setup.');
}else{
  const npm=process.env.npm_execpath;
  if(!npm){console.error('Run npm install from the project root, or npm ci inside frontend.');process.exit(1);}
  const result=spawnSync(process.execPath,[npm,'ci','--prefix','frontend','--no-audit','--no-fund'],{cwd:root,stdio:'inherit'});
  process.exit(result.status??1);
}
