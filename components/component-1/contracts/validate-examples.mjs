import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
// Run from component-1 after app/frontend npm ci; optional external dependency root for audit.
const require=createRequire(path.resolve(process.argv[2] || 'app/frontend/package.json'));
const Ajv2020=require('ajv/dist/2020.js').default;
const ajv=new Ajv2020({allErrors:true,strict:true});
const root=path.dirname(fileURLToPath(import.meta.url));
for (const name of ['group-layout-handoff','group-error']) {
 const schema=JSON.parse(readFileSync(path.join(root,'schemas',`${name}.schema.json`),'utf8'));
 const example=JSON.parse(readFileSync(path.join(root,'examples',`${name}.json`),'utf8'));
 const valid=ajv.compile(schema);
 if (!valid(example)) throw Error(JSON.stringify(valid.errors));
 const bad=structuredClone(example); bad.implementation_status='implemented';
 if(valid(bad))throw Error('Proposal status must not accept implemented claims');
 const extra=structuredClone(example);extra.unknown='unversioned field';
 if(valid(extra))throw Error('Unknown fields must be rejected');
 console.log(`${name}: valid example accepted; invalid implementation status and unknown field rejected`);
}
