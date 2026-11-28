import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {leanAdapter} from './lean-adapter.ts';
const sha=(s:string)=>createHash('sha256').update(s).digest('hex');
const v=leanAdapter('http://127.0.0.1:8080/verify',process.env.LNZ_LEAN_WORKER_TOKEN!);
const statement='(α : Type) (xs ys : List α) : (xs ++ ys).reverse = ys.reverse ++ xs.reverse';
for(const [proof,expected] of [['by\n  rfl','REJECTED'],['by\n  simp','ACCEPTED']]){
 const r=await v.verify({statement,statementHash:sha(statement),proof,proofHash:sha(proof)},AbortSignal.timeout(150000));
 console.log(JSON.stringify(r));assert.equal(r.status,expected);
 if(expected==='REJECTED')assert.match(r.diagnostic,/error:/);
 else assert.match(r.diagnostic,/'lnz_candidate' (depends on axioms|does not depend on any axioms)/);
}
console.log('REAL_LEAN_ADAPTER_SCRIPTED_CONTROLS_PASS');
