import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {SQLiteBudgetStore} from './sqlite-budget.ts';
import {initialBudget} from './budget.ts';
import {runPortable} from './runtime.ts';
import {leanAdapter} from './lean-adapter.ts';
const statement='(α : Type) (xs ys : List α) : (xs ++ ys).reverse = ys.reverse ++ xs.reverse';
const db=new SQLiteBudgetStore('runtime-audit.db');
const evidence=new DatabaseSync('runtime-evidence.db');
evidence.exec('PRAGMA synchronous=FULL; CREATE TABLE events(run_id TEXT,sequence INTEGER,body TEXT,PRIMARY KEY(run_id,sequence))');
let attempts=0;
try{
 db.create('scripted-control',initialBudget({provider:3,verifier:2,lemma:0},Date.now()+300000));
 const result=await runPortable('scripted-control',statement,{
 provider:{id:'SCRIPTED_CONTROL_NOT_AI',async expand(){return [{id:'direct',goals:[]}]},async propose(s,d){attempts++;if(attempts===2)assert.match(d[0],/error:.*rfl.*failed/);return {statement:s,proof:attempts===1?'by\n  rfl':'by\n  simp'}}},
 verifier:leanAdapter('http://127.0.0.1:8080/verify',process.env.LNZ_LEAN_WORKER_TOKEN!),
 store:{async append(e){evidence.prepare('INSERT INTO events VALUES(?,?,?)').run(e.runId,e.sequence,JSON.stringify(e))}}
 },db);
 assert.equal(result.status,'RUNNER_ACCEPTANCE_UNATTESTED');assert.equal(result.certified,false);
 assert.equal(attempts,2);assert.deepEqual((await db.load('scripted-control')).used,{provider:3,verifier:2,lemma:0});
 const rows=db.events('scripted-control');assert.equal(rows.length,10);
 const raw=JSON.stringify(rows);assert.match(raw,/sorryAx/);assert.match(raw,/propext/);
 console.log(JSON.stringify({result,attempts,events:rows,orchestration:evidence.prepare('SELECT * FROM events ORDER BY sequence').all()}));
 console.log('REAL_LEAN_RUNTIME_SCRIPTED_CONTROL_PASS');
}finally{db.close();evidence.close()}
