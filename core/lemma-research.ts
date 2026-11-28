import {createHash,randomUUID} from 'node:crypto';
import {claim,complete} from './budget.ts';
import type {DurableBudgetStore,Kind} from './budget.ts';
import type {EvidenceStore,Verifier} from './runtime-contracts.ts';
import {requireTrustedVerifier} from './trusted-adapter.ts';
type Candidate={kind:'lemma'|'root';statement:string;proof:string};
type Attempt=Candidate & {status:string;diagnostic:string};
export interface LemmaProvider {
 readonly id:string;
 next(input:Readonly<{root:string;attempts:readonly Readonly<Attempt>[];accepted:readonly Readonly<Attempt>[];rootOnly:boolean}>,signal:AbortSignal):Promise<Candidate>;
}
const sha=(s:string)=>createHash('sha256').update(s).digest('hex');
// Stage 1: independently checked lemmas only. Root proof is checked in the
// original context; importing verified lemma declarations is a separate stage.
export async function researchLemmas(runId:string,root:string,provider:LemmaProvider,verifier:Verifier,budget:DurableBudgetStore,evidence:EvidenceStore){
 const verify=requireTrustedVerifier(verifier);
 const start=await budget.load(runId);
 if(start.revision!==0||start.pending||!root.trim()||root.length>12000)throw Error('INVALID_START');
 const signal=AbortSignal.timeout(Math.max(1,Math.min(2147483647,start.deadline-Date.now())));
 const attempts:Attempt[]=[],accepted:Attempt[]=[];
 let sequence=0;
 const record=async(kind:string,data:unknown)=>evidence.append({runId,sequence:++sequence,at:Date.now(),kind,data});
 async function invoke<T>(kind:Kind,fn:()=>Promise<T>):Promise<T>{
  if(signal.aborted)throw Error('DEADLINE');
  const id=randomUUID();await claim(budget,runId,kind,id,Date.now());
  let result:T;
  try{result=await fn()}catch(e){await complete(budget,runId,id,{error:String(e)});throw e}
  await complete(budget,runId,id,{result});
  if(signal.aborted)throw Error('DEADLINE');
  return result;
 }
 const snapshot=(a:Attempt[])=>Object.freeze(a.map(x=>Object.freeze({...x})));
 const stop=async(status:string)=>{await record('STOP',{status});return {status,attempts,accepted,certified:false as const}};
 await record('START',{root,provider:provider.id});
 try{
  while(!signal.aborted){
   const b=await budget.load(runId);
   const p=b.limits.provider-b.used.provider,v=b.limits.verifier-b.used.verifier;
   if(p<1||v<1)return await stop('BUDGET_EXHAUSTED');
   const rootOnly=p<=1||v<=1||b.used.lemma>=b.limits.lemma;
   const c=await invoke('provider',()=>provider.next(Object.freeze({root,attempts:snapshot(attempts),accepted:snapshot(accepted),rootOnly}),signal));
   await record('PROPOSAL',c);
   if(!c||!['lemma','root'].includes(c.kind)||typeof c.statement!=='string'||!c.statement.trim()||c.statement.length>12000||typeof c.proof!=='string'||!c.proof.trim()||c.proof.length>24000)return await stop('INVALID_CANDIDATE');
   if(c.kind==='root'&&c.statement!==root)return await stop('ROOT_MISMATCH');
   if(c.kind==='lemma'&&(rootOnly||c.statement===root))return await stop('INVALID_LEMMA');
   if(attempts.some(a=>a.statement===c.statement&&a.proof===c.proof)){
    const a={...c,status:'DUPLICATE',diagnostic:'Choose a different proof or strategy'};
    attempts.push(a);await record('ATTEMPT',a);continue;
   }
   if(c.kind==='lemma')await invoke('lemma',async()=>({statementHash:sha(c.statement)}));
   const q=Object.freeze({statement:c.statement,statementHash:sha(c.statement),proof:c.proof,proofHash:sha(c.proof)});
   const r=await invoke('verifier',()=>verify(q,signal));
   if(r.statementHash!==q.statementHash||r.proofHash!==q.proofHash||!['ACCEPTED','REJECTED','UNAVAILABLE'].includes(r.status)||typeof r.diagnostic!=='string'||r.diagnostic.length>8000)return await stop('RECEIPT_MISMATCH');
   const a={...c,status:r.status,diagnostic:r.diagnostic};
   attempts.push(a);await record('ATTEMPT',a);
   if(r.status==='UNAVAILABLE')return await stop('VERIFIER_UNAVAILABLE');
   if(r.status==='ACCEPTED'){
    if(c.kind==='root')return await stop('ROOT_ACCEPTED_UNATTESTED');
    accepted.push(a);await record('LEMMA_ACCEPTED',a);
   }
  }
  return await stop('DEADLINE');
 }catch(e){await record('ERROR',{error:String(e)});return await stop('STOPPED_ERROR')}
}
