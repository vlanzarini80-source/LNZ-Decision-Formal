import {randomUUID,createHash} from 'node:crypto';
import type {Verifier} from './runtime-contracts.ts';
import type {TrustedReceiptStore} from './trusted-receipt.ts';
const sha=(s:string)=>createHash('sha256').update(s).digest('hex');
const trusted=new WeakMap<Verifier,Verifier['verify']>();
export function requireTrustedVerifier(v:Verifier):Verifier['verify']{
 const fn=trusted.get(v);if(!fn)throw Error('UNTRUSTED_VERIFIER');return fn;
}
export function trustedAdapter(store:TrustedReceiptStore,context:(statement:string)=>string,transport:(raw:string,signal:AbortSignal)=>Promise<string>):Verifier{
 const adapter:Verifier={id:'lnz-signed-worker-v1',async verify(q,signal){
 if(sha(q.statement)!==q.statementHash||sha(q.proof)!==q.proofHash||!q.proof.startsWith('by\n'))throw Error('REQUEST_BINDING');
 const prefix=context(q.statement);
 const requestId=randomUUID();
 const raw=JSON.stringify({...q,requestId,protocol:'LNZ-WORKER-1',timeoutSeconds:120});
 const binding={requestId,statementHash:q.statementHash,proofHash:q.proofHash,contextHash:sha(prefix),sourceHash:sha(prefix+q.proof.slice(3)+'\n#print axioms lnz_candidate\n')};
 const response=await transport(raw,signal);
 return store.ingest(response,binding);
 }};
 const frozen=Object.freeze(adapter);trusted.set(frozen,frozen.verify.bind(frozen));return frozen;
}
