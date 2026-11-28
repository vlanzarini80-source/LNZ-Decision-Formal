export type Kind='provider'|'verifier'|'lemma';
export type Limits=Readonly<Record<Kind,number>>;
export type BudgetState={limits:Limits;used:Record<Kind,number>;deadline:number;pending:{id:string;kind:Kind} | null;revision:number};
export function initialBudget(limits:Limits,deadline:number):BudgetState{
 for(const k of ['provider','verifier','lemma'] as const)if(!Number.isSafeInteger(limits[k])||limits[k]<0||limits[k]>256)throw Error('INVALID_LIMIT');
 if(!Number.isSafeInteger(deadline)||deadline<0)throw Error('INVALID_DEADLINE');
 return {limits:{...limits},used:{provider:0,verifier:0,lemma:0},deadline,pending:null,revision:0};
}
export function reserve(s:BudgetState,kind:Kind,id:string,now:number):BudgetState{
 if(!Number.isSafeInteger(now)||now<0||now>=s.deadline)throw Error('DEADLINE');
 if(s.pending)throw Error('INTERRUPTED_OR_BUSY');
 if(!['provider','verifier','lemma'].includes(kind)||!id||id.length>128)throw Error('INVALID_RESERVATION');
 if(s.used[kind]>=s.limits[kind])throw Error('EXHAUSTED');
 return {...s,used:{...s.used,[kind]:s.used[kind]+1},pending:{id,kind},revision:s.revision+1};
}
export function finish(s:BudgetState,id:string):BudgetState{
 if(!s.pending||s.pending.id!==id)throw Error('RESERVATION_MISMATCH');
 return {...s,pending:null,revision:s.revision+1};
}
// Adapter must atomically persist state and evidence, compare revision, and enforce unique reservation IDs.
// A failed or uncertain commit must never authorize an external call.
export interface DurableBudgetStore {
 load(runId:string):Promise<BudgetState>;
 compareAndAppend(runId:string,expectedRevision:number,next:BudgetState,event:Readonly<{id:string;kind:'RESERVED'|'FINISHED';evidence:unknown}>):Promise<boolean>;
}
export async function claim(store:DurableBudgetStore,runId:string,kind:Kind,id:string,now:number){
 const s=await store.load(runId),next=reserve(s,kind,id,now);
 if(!await store.compareAndAppend(runId,s.revision,next,{id,kind:'RESERVED',evidence:{resource:kind}}))throw Error('CONFLICT');
 return next;
}
export async function complete(store:DurableBudgetStore,runId:string,id:string,evidence:unknown){
 const s=await store.load(runId),next=finish(s,id);
 if(!await store.compareAndAppend(runId,s.revision,next,{id,kind:'FINISHED',evidence}))throw Error('CONFLICT');
 return next;
}
