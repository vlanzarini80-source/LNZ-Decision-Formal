import {decideEvidence} from './trusted-policy.ts';
import {createHash,createPublicKey,verify} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
const sha=(x:string|Buffer)=>createHash('sha256').update(x).digest('hex');
export type Binding={requestId:string;statementHash:string;proofHash:string;contextHash:string;sourceHash:string};
export class TrustedReceiptStore{
 private db:DatabaseSync;
 private key:ReturnType<typeof createPublicKey>;
 private commit:string;
 private version:string;
 constructor(path:string,pem:string,commit:string,version:string){
 this.key=createPublicKey(pem);if(this.key.asymmetricKeyType!=='ed25519')throw Error('KEY_TYPE');
 this.commit=commit;this.version=version;
 this.db=new DatabaseSync(path);
 this.db.exec('PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS trusted_receipts(id TEXT PRIMARY KEY,payload TEXT NOT NULL,signature TEXT NOT NULL); CREATE TABLE IF NOT EXISTS trusted_quarantine(id INTEGER PRIMARY KEY,reason TEXT NOT NULL,raw TEXT NOT NULL)');
 }
 ingest(raw:string,b:Binding){
 const reject=(reason:string):never=>{this.db.prepare('INSERT INTO trusted_quarantine(reason,raw) VALUES(?,?)').run(reason,raw.slice(0,200000));throw Error(reason)};
 if(raw.length>200000)return reject('LIMIT');
 let x:any,e:any;
 try{x=JSON.parse(raw);if(typeof x.payload!=='string'||typeof x.signature!=='string'||!/^[a-f0-9]{128}$/.test(x.signature))throw Error();}catch{return reject('MALFORMED')}
 if(!verify(null,Buffer.from(x.payload),this.key,Buffer.from(x.signature,'hex')))return reject('SIGNATURE');
 try{e=JSON.parse(x.payload);if(!e||typeof e!=='object'||Array.isArray(e))throw Error()}catch{return reject('PAYLOAD')}
 for(const k of ['requestId','statementHash','proofHash','contextHash','sourceHash'] as const)if(typeof b[k]!=='string'||e[k]!==b[k])return reject('BINDING');
 if(e.worker!==sha(this.key.export({type:'spki',format:'der'}))||e.workerCommit!==this.commit||e.leanVersion!==this.version||e.protocol!=='LNZ-WORKER-1'||e.certified!==false)return reject('IDENTITY');
 if(typeof e.log!=='string'||sha(e.log)!==e.logHash||typeof e.diagnostic!=='string'||e.diagnostic.length>8000||!['ACCEPTED','REJECTED','UNAVAILABLE'].includes(e.status)||!Number.isInteger(e.exitCode))return reject('RESULT');
 if(e.status==='ACCEPTED'&&(e.exitCode!==0||!Array.isArray(e.axioms)||!e.axioms.every((a:unknown)=>['propext','Classical.choice','Quot.sound'].includes(a as string))))return reject('AXIOMS');
 if(e.status==='REJECTED'&&e.exitCode===0&&!e.axioms?.includes('sorryAx'))return reject('RESULT');
 const r=this.db.prepare('INSERT INTO trusted_receipts VALUES(?,?,?) ON CONFLICT(id) DO NOTHING').run(b.requestId,x.payload,x.signature);
 if(Number(r.changes)!==1)return reject('REPLAY_OR_CONFLICT');
 if(e.status==='ACCEPTED'&&decideEvidence({signature:true,context:true,worker:true,fresh:Number(r.changes)===1,compiled:e.exitCode===0,axioms:Array.isArray(e.axioms)&&e.axioms.every((a:unknown)=>['propext','Classical.choice','Quot.sound'].includes(a as string)),attested:false,sufficient:false})!=='ABSTAIN')return reject('POLICY');
 return {statementHash:b.statementHash,proofHash:b.proofHash,status:e.status as 'ACCEPTED'|'REJECTED'|'UNAVAILABLE',diagnostic:e.diagnostic as string,certified:false as const};
 }
 close(){this.db.close()}
}
