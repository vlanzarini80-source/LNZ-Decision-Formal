import type {DurableBudgetStore} from './budget.ts';
export async function inspectRecovery(store:DurableBudgetStore,runId:string,now:number){
 const s=await store.load(runId);
 if(!Number.isSafeInteger(now)||now<0)throw Error('INVALID_TIME');
 return {status:s.pending?'RECONCILIATION_REQUIRED':now>=s.deadline?'EXPIRED':s.revision===0?'FRESH':'HISTORY_REVIEW_REQUIRED',pending:s.pending,revision:s.revision,used:s.used,automaticRetry:false,certified:false} as const;
}
