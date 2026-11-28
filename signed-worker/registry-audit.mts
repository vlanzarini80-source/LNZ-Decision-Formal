import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {TrustedReceiptStore} from '../core/trusted-receipt.ts';
const sha=(s:string)=>createHash('sha256').update(s).digest('hex');
const dir=mkdtempSync(join(tmpdir(),'lnz-trusted-')),path=join(dir,'registry.db');
const pem=readFileSync('worker-public.pem','utf8');
const statement='(α : Type) (xs ys : List α) : (xs ++ ys).reverse = ys.reverse ++ xs.reverse';
const prefix='import Lean\nset_option autoImplicit false\ntheorem lnz_candidate '+statement+' := by\n';
const version=process.env.LNZ_EXPECTED_VERSION!;
let db=new TrustedReceiptStore(path,pem,'543677c0b72e9653704eb5affdbd7d06410c5ba2',version);
try{
 for(const [tactic,status] of [['rfl','REJECTED'],['simp','ACCEPTED']] as const){
 const raw=readFileSync('signed-'+tactic+'.json','utf8'),x=JSON.parse(raw),e=JSON.parse(x.payload);
 const b={requestId:e.requestId,statementHash:sha(statement),proofHash:sha('by\n  '+tactic),contextHash:sha(prefix),sourceHash:sha(prefix+'  '+tactic+'\n#print axioms lnz_candidate\n')};
 assert.throws(()=>db.ingest(raw,{...b,contextHash:'0'.repeat(64)}),/BINDING/);
 assert.throws(()=>db.ingest(JSON.stringify({...x,payload:x.payload+' '}),b),/SIGNATURE/);
 const result=db.ingest(raw,b);assert.equal(result.status,status);assert.equal(result.certified,false);
 db.close();db=new TrustedReceiptStore(path,pem,'543677c0b72e9653704eb5affdbd7d06410c5ba2',version);
 assert.throws(()=>db.ingest(raw,b),/REPLAY_OR_CONFLICT/);
 }
 console.log('TRUSTED_REGISTRY_REAL_LEAN_PASS 2 receipts 6 negative controls');
}finally{db.close();rmSync(dir,{recursive:true,force:true})}
