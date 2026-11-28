import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {EvidenceRegistry,payload} from './signed-evidence.ts';
import type {Evidence} from './signed-evidence.ts';
const {privateKey,publicKey}=generateKeyPairSync('ed25519');
const keys=new Map([['worker-test',publicKey.export({type:'spki',format:'pem'}).toString()]]);
const e:Evidence={worker:'worker-test',requestId:'test-1',statementHash:'a'.repeat(64),proofHash:'b'.repeat(64),contextHash:'c'.repeat(64),status:'ACCEPTED',diagnostic:''};
const sig=(x:Evidence)=>sign(null,payload(x),privateKey).toString('hex');
const dir=mkdtempSync(join(tmpdir(),'lnz-sign-')),path=join(dir,'registry.db');
let db=new EvidenceRegistry(path,keys);
try{
 assert.equal(db.ingest({...e,contextHash:'d'.repeat(64)},sig(e),e).status,'BINDING_MISMATCH');
 assert.equal(db.ingest({...e,statementHash:'d'.repeat(64)},sig(e),e).status,'BINDING_MISMATCH');
 assert.equal(db.ingest({...e,proofHash:'d'.repeat(64)},sig(e),e).status,'BINDING_MISMATCH');
 assert.equal(db.ingest({...e,status:'REJECTED'},sig(e),e).status,'INVALID_SIGNATURE');
 const unknown={...e,worker:'unknown'};assert.equal(db.ingest(unknown,sig(unknown),unknown).status,'UNKNOWN_WORKER');
 const result=db.ingest(e,sig(e),e);assert.equal(result.status,'SIGNED_EVIDENCE_UNATTESTED');assert.equal(result.certified,false);
 db.close();db=new EvidenceRegistry(path,keys);
 assert.equal(db.ingest(e,sig(e),e).status,'REPLAY_OR_CONFLICT');
 const conflict={...e,status:'REJECTED' as const};assert.equal(db.ingest(conflict,sig(conflict),e).status,'REPLAY_OR_CONFLICT');
 console.log('SIGNED_EVIDENCE_AUDIT_PASS 7 negative controls; 1 signed unattested receipt');
}finally{db.close();rmSync(dir,{recursive:true,force:true})}
