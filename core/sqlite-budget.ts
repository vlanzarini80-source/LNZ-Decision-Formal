import {DatabaseSync} from 'node:sqlite';
import type {BudgetState,DurableBudgetStore} from './budget.ts';
export class SQLiteBudgetStore implements DurableBudgetStore {
 private db:DatabaseSync;
 constructor(path:string){
 this.db=new DatabaseSync(path);
 this.db.exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000; PRAGMA foreign_keys=ON; CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,state TEXT NOT NULL); CREATE TABLE IF NOT EXISTS events(run_id TEXT NOT NULL REFERENCES runs(id),revision INTEGER NOT NULL,id TEXT NOT NULL,kind TEXT NOT NULL,evidence TEXT NOT NULL,PRIMARY KEY(run_id,revision),UNIQUE(run_id,id,kind));");
 }
 create(id:string,state:BudgetState){if(state.revision!==0||state.pending)throw Error('INVALID_INITIAL_STATE');this.db.prepare('INSERT INTO runs VALUES(?,?,?)').run(id,0,JSON.stringify(state));}
 async load(id:string):Promise<BudgetState>{const row=this.db.prepare('SELECT state FROM runs WHERE id=?').get(id);if(!row)throw Error('UNKNOWN_RUN');return JSON.parse(String(row.state));}
 async compareAndAppend(id:string,revision:number,next:BudgetState,event:Readonly<{id:string;kind:'RESERVED'|'FINISHED';evidence:unknown}>){
 if(next.revision!==revision+1)throw Error('INVALID_REVISION');
 this.db.exec('BEGIN IMMEDIATE');
 try{
 const r=this.db.prepare('UPDATE runs SET revision=?,state=? WHERE id=? AND revision=?').run(next.revision,JSON.stringify(next),id,revision);
 if(Number(r.changes)!==1){this.db.exec('ROLLBACK');return false;}
 this.db.prepare('INSERT INTO events VALUES(?,?,?,?,?)').run(id,next.revision,event.id,event.kind,JSON.stringify(event.evidence));
 this.db.exec('COMMIT');return true;
 }catch(e){this.db.exec('ROLLBACK');throw e;}
 }
 events(id:string){return this.db.prepare('SELECT * FROM events WHERE run_id=? ORDER BY revision').all(id);}
 close(){this.db.close();}
}
