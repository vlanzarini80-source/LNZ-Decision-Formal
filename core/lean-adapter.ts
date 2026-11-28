import {randomUUID,createHash} from 'node:crypto';
import type {Verifier} from './runtime-contracts.ts';
const sha=(s:string)=>createHash('sha256').update(s).digest('hex');
export function leanAdapter(endpoint:string,token:string,timeoutSeconds=120):Verifier{
 const url=new URL(endpoint);
 if(url.protocol!=='https:'&&!(url.protocol==='http:'&&url.hostname==='127.0.0.1'))throw Error('INVALID_ENDPOINT');
 if(url.username||url.password||url.hash||url.search||url.pathname!=='/verify'||token.length<32||!Number.isInteger(timeoutSeconds)||timeoutSeconds<1||timeoutSeconds>120)throw Error('INVALID_CONFIG');
 return {id:'lnz-worker-v1',async verify(q,signal){
 if(sha(q.statement)!==q.statementHash||sha(q.proof)!==q.proofHash)throw Error('REQUEST_HASH_MISMATCH');
 const requestId=randomUUID(),protocol='LNZ-WORKER-1';
 const r=await fetch(url,{method:'POST',redirect:'error',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({...q,requestId,protocol,timeoutSeconds}),signal:AbortSignal.any([signal,AbortSignal.timeout((timeoutSeconds+20)*1000)])});
 if(!r.ok)throw Error('WORKER_HTTP_'+r.status);
 const raw=await r.text();if(raw.length>64000)throw Error('RECEIPT_LIMIT');
 const x=JSON.parse(raw);
 if(x.protocol!==protocol||x.requestId!==requestId||x.statementHash!==q.statementHash||x.proofHash!==q.proofHash||!['ACCEPTED','REJECTED','UNAVAILABLE'].includes(x.status)||typeof x.diagnostic!=='string'||x.diagnostic.length>8000)throw Error('INVALID_RECEIPT');
 return {statementHash:x.statementHash,proofHash:x.proofHash,status:x.status,diagnostic:x.diagnostic};
 }};
}
