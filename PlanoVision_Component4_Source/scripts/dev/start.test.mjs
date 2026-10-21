import {test} from 'node:test';
import assert from 'node:assert/strict';
import {findPython,getPort} from './start.mjs';
test('default and explicit ports',()=>{assert.equal(getPort(undefined,8765),8765);assert.equal(getPort('5173',8765),5173);});
test('invalid ports fail before starting any processes',()=>{for(const p of ['','0','65536','-1','NaN','5173;echo bad','1.5'])assert.throws(()=>getPort(p,8765));});
test('a nonexistent workspace does not silently use an unrelated global Python',()=>{assert.equal(findPython('Z:/nonexistent-planovision-test-directory','win32'),undefined);});
