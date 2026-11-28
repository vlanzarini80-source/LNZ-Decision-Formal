import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {initialBudget,reserve} from './budget.ts';
import {initialResearch,advanceResearch} from './research-state.ts';
let count=0,receipts=0;
const seen=new Set<string>();
for(const line of readFileSync(process.argv[2],'utf8').trim().split('\n')){
 const [a,b,c]=line.split(',');
 assert(!seen.has(a+','+b));seen.add(a+','+b);
 if(a==='receipt'){
 const s=advanceResearch(initialResearch(1,0),{kind:'candidate',proof:'candidate'},1);
 const next=advanceResearch(s,{kind:'receipt',status:b as 'ACCEPTED'|'REJECTED'|'UNAVAILABLE',diagnostic:''},2);
 assert.equal(next.reason,c);assert.equal(next.certified,false);receipts++;continue;
 }
 const limit=Number(a),used=Number(b);
 assert(Number.isInteger(limit)&&limit>=0&&limit<=256&&Number.isInteger(used)&&used>=0&&used<=limit);
 for(const kind of ['provider','verifier','lemma'] as const){
 const s=initialBudget({provider:limit,verifier:limit,lemma:limit},100);s.used[kind]=used;
 if(c==='EXHAUSTED')assert.throws(()=>reserve(s,kind,'id',1),/EXHAUSTED/);
 else{const next=reserve(s,kind,'id',1);assert.equal(next.used[kind],Number(c));assert.deepEqual(next.limits,s.limits);for(const k of ['provider','verifier','lemma'] as const)if(k!==kind)assert.equal(next.used[k],s.used[k]);}
 count++;
 }
}
assert.equal(count,99459);assert.equal(receipts,3);
console.log('FORMAL_CONFORMANCE_PASS',count,receipts);
