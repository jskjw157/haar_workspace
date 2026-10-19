"""Durable parent-event outbox. Existing localhost SSH tunnel only; no credentials."""
import argparse,fcntl,hashlib,json,os,sqlite3,sys,time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from app.register_events import task_digest

class Publisher:
    def __init__(self,path,origin):
        parsed=urlsplit(origin)
        if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost') or not parsed.port or parsed.path or parsed.username or parsed.password:raise ValueError('Existing localhost SSH tunnel origin required')
        self.path=Path(path);self.origin=origin;self.path.parent.mkdir(parents=True,exist_ok=True);os.umask(0o077)
        with self.db() as db:
            db.executescript("CREATE TABLE IF NOT EXISTS items(event_id TEXT PRIMARY KEY,draft_sha TEXT,payload TEXT,state TEXT,attempts INTEGER,next_attempt REAL,last_error TEXT,receipt TEXT); CREATE TABLE IF NOT EXISTS cache(singleton INTEGER PRIMARY KEY CHECK(singleton=1),body TEXT);")
        os.chmod(self.path,0o600)
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        try:yield db;db.commit()
        except Exception:db.rollback();raise
        finally:db.close()
    def request(self,path,body=None):
        req=Request(self.origin+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers={'Origin':self.origin,'Content-Type':'application/json'})
        with urlopen(req,timeout=3) as r:return json.load(r)
    def sync(self):
        snapshot=self.request('/api/register')
        with self.db() as db:db.execute('INSERT OR REPLACE INTO cache VALUES(1,?)',(json.dumps(snapshot,ensure_ascii=False),))
        return snapshot
    def enqueue(self,draft):
        if set(draft)!={'source_event_id','task_id','changes','verification_note'}:raise ValueError('Expected source_event_id,task_id,changes,verification_note')
        digest=task_digest(draft)
        with self.db() as db:
            old=db.execute('SELECT draft_sha FROM items WHERE event_id=?',(draft['source_event_id'],)).fetchone()
            if old:
                if old['draft_sha']!=digest:raise ValueError('Event ID already queued with different content')
                return {'queued':True,'duplicate':True,'source_event_id':draft['source_event_id']}
        try:snapshot=self.sync()
        except (OSError,ValueError):
            with self.db() as db:row=db.execute('SELECT body FROM cache WHERE singleton=1').fetchone()
            if not row:raise ValueError('No confirmed baseline cache; connect existing tunnel once first')
            snapshot=json.loads(row['body'])
        task=next((t for t in snapshot['document']['tasks'] if t['id']==draft['task_id']),None)
        if not task:raise ValueError('Unknown stable task ID')
        payload={**draft,'publisher_id':'haar-parent','expected_revision':snapshot['source']['version'],'base_task_sha256':task_digest(task),'idempotency_key':draft['source_event_id']}
        with self.db() as db:db.execute('INSERT INTO items VALUES(?,?,?,\'pending\',0,0,NULL,NULL)',(draft['source_event_id'],digest,json.dumps(payload,ensure_ascii=False)))
        return {'queued':True,'duplicate':False,'source_event_id':draft['source_event_id']}
    def head(self):
        with self.db() as db:row=db.execute("SELECT * FROM items WHERE state IN ('pending','conflict') ORDER BY rowid LIMIT 1").fetchone()
        return {**dict(row),'payload':json.loads(row['payload'])} if row else None
    def status(self):
        with self.db() as db:counts={r[0]:r[1] for r in db.execute('SELECT state,count(*) FROM items GROUP BY state')}
        return {k:counts.get(k,0) for k in ['pending','conflict','acked','cancelled']}
    def flush_once(self,now=None):
        now=time.time() if now is None else now;item=self.head()
        if not item or item['state']=='conflict' or item['next_attempt']>now:return None
        try:
            receipt=self.request('/api/register/events',item['payload'])
            if receipt.get('source_event_id')!=item['event_id'] or type(receipt.get('revision')) is not int:raise ValueError('Uncertain delivery receipt')
        except (OSError,ValueError) as e:
            conflict=isinstance(e,HTTPError) and 400<=e.code<500 and e.code not in (408,429)
            error='http_'+str(e.code) if isinstance(e,HTTPError) else 'transport_uncertain'
            if isinstance(e,HTTPError):e.close()
            with self.db() as db:db.execute('UPDATE items SET state=?,attempts=attempts+1,next_attempt=?,last_error=? WHERE event_id=?',('conflict' if conflict else 'pending',now+min(30,2**min(item['attempts']+1,5)),error,item['event_id']))
            return None
        with self.db() as db:db.execute("UPDATE items SET state='acked',attempts=attempts+1,last_error=NULL,receipt=? WHERE event_id=?",(json.dumps(receipt),item['event_id']))
        try:self.sync()
        except (OSError,ValueError):pass
        return receipt
    def heartbeat(self):
        counts=self.status()
        return self.request('/api/register/heartbeat',{'publisher_id':'haar-parent','pending':counts['pending'],'blocked':counts['conflict']})
    def cancel(self,event_id,reason):
        if not reason.strip():raise ValueError('A review reason is required')
        with self.db() as db:
            cursor=db.execute("UPDATE items SET state='cancelled',last_error=? WHERE event_id=? AND state IN ('pending','conflict')",('reviewed: '+reason,event_id))
            if cursor.rowcount!=1:raise ValueError('No pending/conflicting event found')
    def watch(self):
        lock_path=self.path.with_suffix('.lock')
        with lock_path.open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);last_contact=0
            while True:
                receipt=self.flush_once()
                if receipt:print(json.dumps({'delivered':receipt['source_event_id'],'revision':receipt['revision']}),flush=True)
                if time.monotonic()-last_contact>=30:
                    try:self.sync();self.heartbeat()
                    except (OSError,ValueError):pass
                    last_contact=time.monotonic()
                time.sleep(1)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--queue',required=True);p.add_argument('--origin',default='http://127.0.0.1:3311');sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('watch');sub.add_parser('status');e=sub.add_parser('enqueue');e.add_argument('--file',required=True);c=sub.add_parser('cancel');c.add_argument('--event-id',required=True);c.add_argument('--reason',required=True)
    args=p.parse_args();path=Path(args.queue).expanduser().absolute()
    if sys.platform=='darwin':
        volume=Path('/Volumes/X9 Pro')
        if not os.path.ismount(volume) or volume not in path.parents or path.resolve().parts[:3]!=volume.parts:raise SystemExit('Mounted X9 Pro required; internal fallback is disabled')
    publisher=Publisher(path,args.origin)
    if args.action=='watch':publisher.watch();return
    result=publisher.enqueue(json.loads(Path(args.file).read_text())) if args.action=='enqueue' else publisher.cancel(args.event_id,args.reason) if args.action=='cancel' else publisher.status()
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
