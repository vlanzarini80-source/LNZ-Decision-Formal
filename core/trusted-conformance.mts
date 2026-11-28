import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decideEvidence} from './trusted-policy.ts';
const seen=new Set<number>();
for(const line of readFileSync(process.argv[2],'utf8').trim().split('\n')){
 const [id,expected]=line.split(',');const n=Number(id);
 assert(Number.isInteger(n)&&n>=0&&n<256&&!seen.has(n));seen.add(n);
 const b=(i:number)=>Boolean(n & (1<<i));
 assert.equal(decideEvidence({signature:b(0),context:b(1),worker:b(2),fresh:b(3),compiled:b(4),axioms:b(5),attested:b(6),sufficient:b(7)}),expected,'case '+n);
}
assert.equal(seen.size,256);
console.log('TRUSTED_POLICY_CONFORMANCE_PASS',seen.size);
