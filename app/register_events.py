"""Parent-reported changes to one canonical register. No work dispatch or Library polling."""
from datetime import datetime,timezone
import hashlib,json,re
from app.register import RegisterError,require,iso_time,timestamp

def task_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def source_status(db,current):
    row=db.execute('SELECT * FROM register_stream WHERE singleton=1').fetchone()
    if not row:return {'library_version':current['version'] if current else None,'publisher_offline':False,'pending_delivery':0,'blocked_delivery':0,'event_updates':False}
    row=dict(row);age=(datetime.now(timezone.utc)-datetime.fromisoformat(row['last_seen_at'].replace('Z','+00:00'))).total_seconds()
    return {'bridge':'parent_events','library_version':row['library_version'],'event_updates':True,'publisher_id':'haar-parent','publisher_last_seen':row['last_seen_at'],'publisher_offline':age>90,'pending_delivery':row['pending'],'blocked_delivery':row['blocked'],'automatic_library_refresh':False}

def heartbeat(register,data):
    require(isinstance(data,dict) and data.get('publisher_id')=='haar-parent','invalid_publisher','부모 게시자 ID를 확인하세요')
    require(set(data)<={'publisher_id','pending','blocked'},'invalid_field','허용되지 않은 heartbeat 필드입니다')
    for key in ['pending','blocked']:require(type(data.get(key)) is int and 0<=data[key]<=100000,'invalid_count','대기열 건수를 확인하세요')
    with register.db() as db:
        db.execute('UPDATE register_stream SET last_seen_at=?,pending=?,blocked=? WHERE singleton=1',(timestamp(),data['pending'],data['blocked']))
    return {'received':True,'dispatched':False}

def apply_event(register,data):
    try:return _apply(register,data)
    except RegisterError as e:
        with register.db() as db:register.event(db,'delivery_rejected',None,{'code':e.code})
        raise

def _apply(register,data):
    require(isinstance(data,dict),'invalid_json','변경 이벤트 객체가 필요합니다',400)
    keys={'source_event_id','idempotency_key','publisher_id','expected_revision','task_id','base_task_sha256','changes','verification_note'}
    require(set(data)==keys and data['publisher_id']=='haar-parent','invalid_publisher','부모 이벤트 계약을 확인하세요')
    for field in ['source_event_id','idempotency_key']:require(isinstance(data[field],str) and re.fullmatch(r'[A-Za-z0-9_-]{8,128}',data[field]),'invalid_key','이벤트 식별자가 필요합니다')
    require(type(data['expected_revision']) is int,'invalid_version','기준 revision이 필요합니다')
    changes=data['changes'];allowed={'status','status_detail','next_action','blocker','last_verified_at'}
    require(isinstance(changes,dict) and set(changes)<=allowed and {'status','status_detail','last_verified_at'}<=set(changes),'invalid_field','지시·완료 기준·우선순위·승인 범위를 변경할 수 없습니다')
    require(all(isinstance(v,str) and len(v)<=4000 for v in changes.values()),'invalid_field','변경 문자열을 확인하세요')
    require(isinstance(data['verification_note'],str) and 0<len(data['verification_note'].strip())<=4000 and changes['status_detail'].strip(),'missing_evidence','확인 근거와 설명이 필요합니다')
    iso_time(changes['last_verified_at']);payload_hash=task_digest(data)
    with register.db() as db:
        db.execute('BEGIN IMMEDIATE')
        prior=db.execute('SELECT * FROM register_deliveries WHERE source_event_id=? OR idempotency_key=?',(data['source_event_id'],data['idempotency_key'])).fetchall()
        if prior:
            require(len(prior)==1 and prior[0]['digest']==payload_hash,'idempotency_conflict','동일 이벤트/요청 ID의 내용이 다릅니다',409)
            return {**json.loads(prior[0]['receipt']),'duplicate':True}
        current=register.current(db);require(current is not None,'source_missing','초기 확인본이 필요합니다',409)
        require(current['version']==data['expected_revision'],'revision_conflict','원본이 바뀌었습니다. 최신본을 확인하세요',409)
        doc=json.loads(current['document']);task=next((t for t in doc['tasks'] if t['id']==data['task_id']),None)
        require(task is not None,'not_found','작업이 없습니다',404)
        require(task_digest(task)==data['base_task_sha256'],'task_conflict','작업 내용이 바뀌었습니다',409)
        require(changes['status'] in doc['status_definitions'],'invalid_status','정의된 상태가 필요합니다')
        require(datetime.fromisoformat(changes['last_verified_at'].replace('Z','+00:00'))>=datetime.fromisoformat(task['last_verified_at'].replace('Z','+00:00')),'stale_evidence','과거 확인 기록으로 덮어쓸 수 없습니다',409)
        old_status=task['status'];basis=task.get('verification_basis',{'evidence':task.get('evidence')})
        if basis.get('type')=='parent_report':basis=basis.get('previous',{})
        task.update(changes);task['verification_basis']={'type':'parent_report','note':data['verification_note'],'source_event_id':data['source_event_id'],'previous':basis}
        revision=current['version']+1;now=timestamp();doc['version']+=1;doc['updated_at']=now
        raw=json.dumps(doc,ensure_ascii=False).encode();digest=hashlib.sha256(raw).hexdigest()
        require(len(raw)<=2_000_000,'too_large','대장이 허용 크기를 초과했습니다')
        db.execute('INSERT INTO register_snapshots VALUES(?,?,?,?,?)',(current['library_id'],revision,digest,raw.decode(),now))
        db.execute('UPDATE register_state SET version=?,last_attempt_at=?,last_error=NULL WHERE singleton=1',(revision,now))
        db.execute('INSERT OR IGNORE INTO register_stream VALUES(1,?,?,0,0)',(current['version'],now))
        db.execute('UPDATE register_stream SET last_seen_at=? WHERE singleton=1',(now,))
        # An intervening parent observation needs explicit review of outstanding UI proposals.
        for p in db.execute("SELECT id FROM register_proposals WHERE task_id=? AND state='pending'",(task['id'],)).fetchall():
            db.execute("UPDATE register_proposals SET state='conflict' WHERE id=?",(p['id'],));register.event(db,'conflict',task['id'],{'proposal_id':p['id'],'source_revision':revision})
        receipt={'source_event_id':data['source_event_id'],'revision':revision,'task_id':task['id'],'sha256':digest,'duplicate':False,'dispatched':False,'library_updated':False}
        db.execute('INSERT INTO register_deliveries VALUES(?,?,?,?)',(data['source_event_id'],data['idempotency_key'],payload_hash,json.dumps(receipt)))
        register.event(db,'parent_change',task['id'],{'source_event_id':data['source_event_id'],'revision':revision,'from':old_status,'to':task['status'],'changed_fields':sorted(changes)})
        return receipt
