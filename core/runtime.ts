import {randomUUID,createHash} from 'node:crypto';
import {searchProofPlan} from './search.ts';
import {validateDecomposition} from './decomposition.ts';
import {initialResearch,advanceResearch} from './research-state.ts';
import {claim,complete} from './budget.ts';
import type {DurableBudgetStore,Kind} from './budget.ts';
import type {RuntimeAdapters} from './runtime-contracts.ts';
const sha=(s:string)=>createHash('sha256').update(s).digest('hex');
export async function runPortable(runId:string,statement:string,adapters:RuntimeAdapters,store:DurableBudgetStore){
 if(!statement.trim()||statement.length>12000)throw Error('INVALID_STATEMENT');
 const start=await store.load(runId);
 if(start.revision!==0||start.pending)throw Error('FRESH_RUN_REQUIRED');
 const signal=AbortSignal.timeout(Math.max(1,Math.min(2147483647,start.deadline-Date.now())));
 let sequence=0;
 const record=async(kind:string,data:unknown)=>adapters.store.append({runId,sequence:++sequence,at:Date.now(),kind,data});
 async function invoke<T>(kind:Kind,operation:()=>Promise<T>):Promise<T>{
 const id=randomUUID();
 await claim(store,runId,kind,id,Date.now());
 if(signal.aborted)throw Error('DEADLINE');
 let result:T;
 try{result=await operation()}catch(e){await complete(store,runId,id,{error:String(e)});throw e}
 await complete(store,runId,id,{result});
 if(signal.aborted)throw Error('DEADLINE');
 return result;
 }
 await record('START',{statement,provider:adapters.provider.id,verifier:adapters.verifier.id});
 try{
 const plan=await searchProofPlan(statement,g=>invoke('provider',()=>adapters.provider.expand(g,signal)),Math.max(0,start.limits.provider-Math.min(2,start.limits.verifier)),12);
 await record('PLAN',plan);
 if(plan.plan){
 const nodes:{id:string;statement:string;dependsOn:string[]}[]=[];
 function visit(p:NonNullable<typeof plan.plan>):string{const id='n'+nodes.length;const node={id,statement:p.goal,dependsOn:[] as string[]};nodes.push(node);node.dependsOn=p.children.map(visit);return id}
 const root=visit(plan.plan);await record('STRUCTURE',validateDecomposition(statement,nodes,root));
 }
 const remaining=(await store.load(runId));
 const budget=Math.min(4,remaining.limits.provider-remaining.used.provider,remaining.limits.verifier-remaining.used.verifier);
 if(budget<1){await record('STOP',{reason:'BUDGET_EXHAUSTED'});return {status:'BUDGET_EXHAUSTED',certified:false}}
 let state=initialResearch(budget,Date.now());state.deadline=start.deadline;
 while(state.phase==='READY'){
 const c=await invoke('provider',()=>adapters.provider.propose(statement,Object.freeze([...state.diagnostics]),signal,Object.freeze([...state.proofs])));
 if(c.statement!==statement)throw Error('STATEMENT_MISMATCH');
 state=advanceResearch(state,{kind:'candidate',proof:c.proof},Date.now());
 if(state.phase!=='WAITING')break;
 const req=Object.freeze({statement,statementHash:sha(statement),proof:c.proof,proofHash:sha(c.proof)});
 const r=await invoke('verifier',()=>adapters.verifier.verify(req,signal));
 if(r.statementHash!==req.statementHash||r.proofHash!==req.proofHash||!['ACCEPTED','REJECTED','UNAVAILABLE'].includes(r.status)||typeof r.diagnostic!=='string'||r.diagnostic.length>8000)throw Error('RECEIPT_MISMATCH');
 state=advanceResearch(state,{kind:'receipt',status:r.status,diagnostic:r.diagnostic},Date.now());
 await record('STATE',state);
 }
 await record('STOP',state);return {status:state.reason,certified:false};
 }catch(e){await record('STOP',{reason:String(e)});return {status:'STOPPED_ERROR',error:String(e),certified:false}}
}
