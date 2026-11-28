import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createPublicKey,createHash,verify} from 'node:crypto';
const sha=(s:string|Buffer)=>createHash('sha256').update(s).digest('hex');
const key=createPublicKey(readFileSync('worker-public.pem'));
assert.equal(key.asymmetricKeyType,'ed25519');
for(const [tactic,status,rc] of [['rfl','REJECTED',1],['simp','ACCEPTED',0]] as const){
 const r=JSON.parse(readFileSync('signed-'+tactic+'.json','utf8'));
 const sig=Buffer.from(r.signature,'hex');
 assert(verify(null,Buffer.from(r.payload),key,sig));
 const e=JSON.parse(r.payload);
 assert.equal(e.worker,sha(key.export({type:'spki',format:'der'})));
 assert.equal(e.workerCommit,'543677c0b72e9653704eb5affdbd7d06410c5ba2');
 assert.match(e.leanVersion,/version 4\.24\.0/);
 assert.equal(e.logHash,sha(e.log));assert.equal(e.status,status);assert.equal(e.exitCode,rc);assert.equal(e.certified,false);
 const statement='(α : Type) (xs ys : List α) : (xs ++ ys).reverse = ys.reverse ++ xs.reverse';
 const prefix='import Lean\nset_option autoImplicit false\ntheorem lnz_candidate '+statement+' := by\n';
 assert.equal(e.statementHash,sha(statement));assert.equal(e.proofHash,sha('by\n  '+tactic));
 assert.equal(e.contextHash,sha(prefix));assert.equal(e.sourceHash,sha(prefix+'  '+tactic+'\n#print axioms lnz_candidate\n'));
 if(status==='ACCEPTED')assert.deepEqual(e.axioms,['propext']);
 else assert.match(e.log,/error:/);
 assert(!verify(null,Buffer.from(r.payload+' '),key,sig));
 console.log('SIGNED_REAL_LEAN',status,e.exitCode,e.axioms,e.sourceHash,e.logHash);
}
console.log('SIGNED_REAL_LEAN_AUDIT_PASS');
