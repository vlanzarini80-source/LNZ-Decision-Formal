import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFileSync,mkdtempSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {researchLemmas} from '../core/lemma-research.ts';
import type {LemmaProvider} from '../core/lemma-research.ts';
import {trustedAdapter} from '../core/trusted-adapter.ts';
import {TrustedReceiptStore} from '../core/trusted-receipt.ts';
import {SQLiteBudgetStore} from '../core/sqlite-budget.ts';
import {initialBudget} from '../core/budget.ts';
const dir=mkdtempSync(join(tmpdir(),'lnz-lemma-'));
const receipts=join(dir,'receipts.db');
const registry=new TrustedReceiptStore(receipts,readFileSync('worker-public.pem','utf8'),process.env.LNZ_WORKER_COMMIT!,process.env.LNZ_EXPECTED_VERSION!);
const budget=new SQLiteBudgetStore(join(dir,'budget.db'));
const db=new DatabaseSync(join(dir,'events.db'));
db.exec('PRAGMA synchronous=FULL; CREATE TABLE events(run TEXT,seq INTEGER,data TEXT,PRIMARY KEY(run,seq))');
const evidence={async append(e:any){db.prepare('INSERT INTO events VALUES(?,?,?)').run(e.runId,e.sequence,JSON.stringify(e))}};
const root='(a b : Nat) : a + b = b + a';
const lemma='(n : Nat) : n + 0 = n';
let calls=0;
const adapter=trustedAdapter(registry,s=>'import Lean\nset_option autoImplicit false\ntheorem lnz_candidate '+s+' := by\n',async raw=>{
 calls++;
 const p=spawnSync('python3',['signed-worker/signed_dynamic_execution.py'],{input:raw,encoding:'utf8',env:{...process.env,PYTHONPATH:process.cwd()+'/worker'},timeout:150000});
 assert.equal(p.status,0,p.stderr);return p.stdout.trim();
});
const provider:LemmaProvider={id:'scripted-control-not-ai',async next(i){
 assert.equal(i.root,root);
 if(i.attempts.length===0)return {kind:'lemma',statement:lemma,proof:'by\n  assumption'};
 if(i.attempts.length===1){assert.equal(i.attempts[0].status,'REJECTED');assert.equal(i.accepted.length,0);return {kind:'lemma',statement:lemma,proof:'by\n  simp'};}
 assert.equal(i.accepted.length,1);assert.equal(i.rootOnly,true);
 return {kind:'root',statement:root,proof:'by\n  omega'};
}};
const start=(id:string,p=3,v=3,l=2)=>budget.create(id,initialBudget({provider:p,verifier:v,lemma:l},Date.now()+300000));
try{
 start('real');
 const r=await researchLemmas('real',root,provider,adapter,budget,evidence);
 assert.equal(r.status,'ROOT_ACCEPTED_UNATTESTED');assert.equal(r.certified,false);
 assert.deepEqual(r.attempts.map(a=>a.status),['REJECTED','ACCEPTED','ACCEPTED']);
 assert.equal(r.accepted.length,1);assert.equal(calls,3);
 assert.deepEqual((await budget.load('real')).used,{provider:3,verifier:3,lemma:2});
 start('zero',0,0,0);
 assert.equal((await researchLemmas('zero',root,provider,adapter,budget,evidence)).status,'BUDGET_EXHAUSTED');
 start('mismatch');
 const bad:LemmaProvider={id:'mismatch-control',async next(){return {kind:'root',statement:lemma,proof:'by\n  simp'}}};
 assert.equal((await researchLemmas('mismatch',root,bad,adapter,budget,evidence)).status,'ROOT_MISMATCH');
 assert.equal(calls,3);
 start('fake');
 await assert.rejects(researchLemmas('fake',root,provider,{id:adapter.id,async verify(){throw Error('must not call')}},budget,evidence),/UNTRUSTED_VERIFIER/);
 assert.equal((await budget.load('fake')).revision,0);
 console.log('LEMMA_RESEARCH_REAL_LEAN_PASS scripted controls only');
}finally{
 const rd=new DatabaseSync(receipts);
 writeFileSync('lemma-research-evidence.json',JSON.stringify({events:db.prepare('SELECT * FROM events ORDER BY run,seq').all(),receipts:rd.prepare('SELECT * FROM trusted_receipts').all(),budget:budget.events('real'),calls},null,2));
 rd.close();db.close();registry.close();budget.close();
}
