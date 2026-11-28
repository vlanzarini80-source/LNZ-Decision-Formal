import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawn} from 'node:child_process';
import {SQLiteBudgetStore} from './sqlite-budget.ts';
import {initialBudget,claim,complete} from './budget.ts';
if(process.argv[2]==='child'){
 const s=new SQLiteBudgetStore(process.argv[3]);
 try{await claim(s,'run','provider',process.argv[4],1);console.log('CLAIMED')}catch(e){console.log(String(e));process.exitCode=2}finally{s.close()}
}else{
 const dir=mkdtempSync(join(tmpdir(),'lnz-sqlite-')),path=join(dir,'audit.db');
 try{
 let s=new SQLiteBudgetStore(path);s.create('run',initialBudget({provider:2,verifier:1,lemma:1},100));s.close();
 const results=await Promise.all(Array.from({length:8},(_,i)=>new Promise<{code:number|null;out:string}>((resolve,reject)=>{const p=spawn(process.execPath,['--experimental-strip-types',process.argv[1],'child',path,'p'+i]);let out='';p.stdout.on('data',d=>out+=d);p.on('error',reject);p.on('close',code=>resolve({code,out}))})));
 assert.equal(results.filter(x=>x.code===0&&x.out.includes('CLAIMED')).length,1);
 assert.equal(results.filter(x=>x.code===2&&/CONFLICT|INTERRUPTED_OR_BUSY/.test(x.out)).length,7);
 s=new SQLiteBudgetStore(path);let state=await s.load('run');assert.equal(state.used.provider,1);assert.equal(s.events('run').length,1);
 await assert.rejects(claim(s,'run','verifier','v',2),/INTERRUPTED_OR_BUSY/);
 const id=state.pending!.id;await complete(s,'run',id,{status:'SYNTHETIC'});s.close();
 s=new SQLiteBudgetStore(path);state=await s.load('run');assert.equal(state.pending,null);assert.equal(s.events('run').length,2);
 await assert.rejects(claim(s,'run','provider',id,3),/UNIQUE/);
 assert.deepEqual(await s.load('run'),state);assert.equal(s.events('run').length,2);
 await claim(s,'run','provider','new',4);await complete(s,'run','new',{status:'SYNTHETIC'});
 await assert.rejects(claim(s,'run','provider','third',5),/EXHAUSTED/);
 s.close();console.log('11 assertions passed; SQLite disk and 8 child processes');
 }finally{rmSync(dir,{recursive:true,force:true})}
}
