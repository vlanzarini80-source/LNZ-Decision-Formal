import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {initialResearch,advanceResearch} from './research-state.ts';
import {initialBudget,claim,complete} from './budget.ts';
import {SQLiteBudgetStore} from './sqlite-budget.ts';
if(process.argv[2]==='child'){
 const db=new SQLiteBudgetStore(process.argv[3]);
 await claim(db,'r','provider','interrupted',1);
 process.kill(process.pid,'SIGKILL');
}else{
 const s=initialResearch(2,0);
 const waiting=advanceResearch(s,{kind:'candidate',proof:'candidate'},1);
 const events=[{kind:'candidate',proof:'other'},{kind:'pending'},{kind:'timeout'},...(['ACCEPTED','REJECTED','UNAVAILABLE'] as const).map(status=>({kind:'receipt' as const,status,diagnostic:''}))] as const;
 let checks=0;
 for(const state of [s,waiting])for(const e of events){
 const stopped=advanceResearch(state,e,s.deadline);
 assert.equal(stopped.phase,'STOPPED');assert.equal(stopped.certified,false);
 for(const next of events){assert.deepEqual(advanceResearch(stopped,next,s.deadline+1),stopped);checks++}
 }
 const accepted=advanceResearch(waiting,{kind:'receipt',status:'ACCEPTED',diagnostic:''},2);
 assert.equal(accepted.reason,'RUNNER_ACCEPTANCE_UNATTESTED');assert.equal(accepted.certified,false);
 const dir=mkdtempSync(join(tmpdir(),'lnz-crash-')),path=join(dir,'audit.db');
 try{
 let db=new SQLiteBudgetStore(path);db.create('r',initialBudget({provider:2,verifier:1,lemma:1},100));db.close();
 const child=spawnSync(process.execPath,['--experimental-strip-types',process.argv[1],'child',path]);
 assert.equal(child.signal,'SIGKILL');
 db=new SQLiteBudgetStore(path);
 assert.equal((await db.load('r')).pending?.id,'interrupted');
 assert.equal((await db.load('r')).used.provider,1);
 assert.equal(db.events('r').length,1);
 await assert.rejects(claim(db,'r','provider','retry',2),/INTERRUPTED_OR_BUSY/);
 await assert.rejects(complete(db,'r','wrong',{}),/RESERVATION_MISMATCH/);
 await assert.rejects(claim(db,'r','provider','late',100),/DEADLINE/);
 assert.equal(db.events('r').length,1);db.close();
 console.log('TRANSITION_CRASH_AUDIT_PASS',checks,'terminal comparisons; committed reservation survives SIGKILL');
 }finally{rmSync(dir,{recursive:true,force:true})}
}
