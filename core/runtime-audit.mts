import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {SQLiteBudgetStore} from './sqlite-budget.ts';
import {initialBudget} from './budget.ts';
import {runPortable} from './runtime.ts';
import type {RuntimeAdapters} from './runtime-contracts.ts';
const dir=mkdtempSync(join(tmpdir(),'lnz-runtime-'));
const db=new SQLiteBudgetStore(join(dir,'runtime.db'));
try{
 db.create('r',initialBudget({provider:3,verifier:2,lemma:0},Date.now()+60000));
 let n=0;const events:unknown[]=[];
 const adapters:RuntimeAdapters={provider:{id:'synthetic',async expand(){return [{id:'direct',goals:[]}]},async propose(statement,d){n++;assert.equal(d.length,n-1);return {statement,proof:'candidate'+n}}},verifier:{id:'synthetic',async verify(r){return {...r,status:n===1?'REJECTED':'ACCEPTED',diagnostic:'synthetic'}}},store:{async append(e){events.push(e)}}};
 const result=await runPortable('r','synthetic target',adapters,db);
 assert.equal(result.status,'RUNNER_ACCEPTANCE_UNATTESTED');assert.equal(result.certified,false);
 assert.deepEqual((await db.load('r')).used,{provider:3,verifier:2,lemma:0});
 assert.equal(db.events('r').length,10);assert.equal(events.length,6);
 await assert.rejects(runPortable('r','synthetic target',adapters,db),/FRESH_RUN_REQUIRED/);
 console.log('Runtime audit passed; 5 durable reservations, synthetic adapters, in-memory orchestration events');
}finally{db.close();rmSync(dir,{recursive:true,force:true})}
