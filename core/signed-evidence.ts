import {verify,createHash,createPublicKey} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
export type Evidence={worker:string;requestId:string;statementHash:string;proofHash:string;contextHash:string;status:'ACCEPTED'|'REJECTED'|'UNAVAILABLE';diagnostic:string};
export function payload(e:Evidence){return Buffer.from(JSON.stringify(['LNZ-EVIDENCE-1',e.worker,e.requestId,e.statementHash,e.proofHash,e.contextHash,e.status,e.diagnostic]));}
export class EvidenceRegistry{
 private db:DatabaseSync;
 constructor(path:string,private keys:ReadonlyMap<string,string>){
 this.db=new DatabaseSync(path);
 this.db.exec('PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS evidence(request_id TEXT PRIMARY KEY,body TEXT NOT NULL,signature TEXT NOT NULL); CREATE TABLE IF NOT EXISTS quarantine(id INTEGER PRIMARY KEY,reason TEXT NOT NULL,body TEXT NOT NULL);');
 }
 ingest(e:Evidence,signature:string,expected:Pick<Evidence,'worker'|'requestId'|'statementHash'|'proofHash'|'contextHash'>){
 const body=JSON.stringify(e);
 const reject=(reason:string)=>{this.db.prepare('INSERT INTO quarantine(reason,body) VALUES(?,?)').run(reason,body);return {status:reason,certified:false as const};};
 if(!e||typeof e!=='object'||typeof signature!=='string'||!/^[0-9a-f]{128}$/.test(signature))return reject('MALFORMED');
 for(const k of ['statementHash','proofHash','contextHash'] as const)if(!/^[0-9a-f]{64}$/.test(e[k]))return reject('MALFORMED');
 if(!['ACCEPTED','REJECTED','UNAVAILABLE'].includes(e.status)||typeof e.diagnostic!=='string'||e.diagnostic.length>8000)return reject('MALFORMED');
 for(const k of ['worker','requestId','statementHash','proofHash','contextHash'] as const)if(typeof e[k]!=='string'||e[k]!==expected[k])return reject('BINDING_MISMATCH');
 const key=this.keys.get(e.worker);if(!key)return reject('UNKNOWN_WORKER');
 try{const pub=createPublicKey(key);if(pub.asymmetricKeyType!=='ed25519'||!verify(null,payload(e),pub,Buffer.from(signature,'hex')))return reject('INVALID_SIGNATURE');}catch{return reject('INVALID_SIGNATURE');}
 const r=this.db.prepare('INSERT INTO evidence VALUES(?,?,?) ON CONFLICT(request_id) DO NOTHING').run(e.requestId,body,signature);
 if(Number(r.changes)!==1)return reject('REPLAY_OR_CONFLICT');
 return {status:'SIGNED_EVIDENCE_UNATTESTED',certified:false as const};
 }
 close(){this.db.close();}
}
