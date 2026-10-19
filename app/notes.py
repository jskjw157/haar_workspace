"""Independent block notes linked to stable task IDs; SQLite is the shared source."""
from contextlib import contextmanager
import hashlib,json,re,sqlite3,uuid
from app.register import require,timestamp

def validate_blocks(blocks):
    require(isinstance(blocks,list) and len(blocks)<=200,'invalid_blocks','블록은 200개 이내로 작성하세요')
    ids=set()
    for b in blocks:
        require(isinstance(b,dict) and isinstance(b.get('id'),str) and re.fullmatch('[A-Za-z0-9_-]{1,100}',b['id']) and b['id'] not in ids,'invalid_blocks','블록 ID를 확인하세요');ids.add(b['id'])
        kind=b.get('type');require(kind in ('paragraph','heading','check','table'),'invalid_blocks','지원되는 블록을 선택하세요')
        if kind=='table':
            require(set(b)=={'id','type','cells'} and isinstance(b['cells'],list) and 1<=len(b['cells'])<=30,'invalid_table','표는 1~30행이어야 합니다')
            width=len(b['cells'][0]) if isinstance(b['cells'][0],list) else 0
            require(1<=width<=6 and all(isinstance(row,list) and len(row)==width and all(isinstance(c,str) and len(c)<=2000 for c in row) for row in b['cells']),'invalid_table','표는 1~6열의 같은 길이 행으로 작성하세요')
        else:
            require(set(b)==({'id','type','text','checked'} if kind=='check' else {'id','type','text'}) and isinstance(b.get('text'),str) and len(b['text'])<=10000,'invalid_blocks','블록 내용을 확인하세요')
            if kind=='check':require(type(b['checked']) is bool,'invalid_blocks','체크 상태를 확인하세요')

class Notes:
    def __init__(self,path):
        self.path=str(path)
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS note_pages(id TEXT PRIMARY KEY,task_id TEXT NOT NULL,parent_id TEXT,title TEXT NOT NULL,blocks TEXT NOT NULL,revision INTEGER NOT NULL,updated_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS note_task_pages ON note_pages(task_id);
                CREATE TABLE IF NOT EXISTS note_commands(key TEXT PRIMARY KEY,digest TEXT NOT NULL,receipt TEXT NOT NULL);''')
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        try:yield db;db.commit()
        except Exception:db.rollback();raise
        finally:db.close()
    def task(self,db,task_id):
        row=db.execute('SELECT s.document FROM register_snapshots s JOIN register_state p ON s.library_id=p.library_id AND s.version=p.version WHERE p.singleton=1').fetchone()
        task=next((t for t in json.loads(row['document'])['tasks'] if t['id']==task_id),None) if row else None
        require(task is not None,'task_not_found','연결할 작업을 찾을 수 없습니다',404)
        return {'id':task['id'],'title':task['task_name']}
    def page(self,page_id):
        with self.db() as db:
            row=db.execute('SELECT * FROM note_pages WHERE id=?',(page_id,)).fetchone();require(row is not None,'note_not_found','노트를 찾을 수 없습니다',404)
            result=dict(row);result['blocks']=json.loads(row['blocks']);return result
    def list(self,task_id,query=''):
        require(isinstance(query,str) and len(query)<=120,'invalid_query','검색어는 120자 이내로 입력하세요')
        with self.db() as db:
            task=self.task(db,task_id);rows=db.execute('SELECT * FROM note_pages WHERE task_id=? ORDER BY updated_at DESC,id',(task_id,)).fetchall();pages=[]
            for row in rows:
                if query:
                    content=[row['title']]
                    for block in json.loads(row['blocks']):
                        content.extend(cell for cells in block['cells'] for cell in cells) if block['type']=='table' else content.append(block['text'])
                    if query.casefold() not in ' '.join(content).casefold():continue
                pages.append({k:row[k] for k in ['id','task_id','parent_id','title','revision','updated_at']})
            return {'task':task,'pages':pages}
    def command(self,operation,data):
        require(isinstance(data,dict),'invalid_json','JSON 객체가 필요합니다',400)
        key=data.get('idempotency_key');require(isinstance(key,str) and re.fullmatch('[A-Za-z0-9_-]{8,128}',key),'invalid_key','저장 요청 ID를 확인하세요')
        digest=hashlib.sha256(json.dumps([operation,data],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        title=data.get('title');require(isinstance(title,str) and len(title)<=120,'invalid_title','노트 제목은 120자 이내로 입력하세요')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');prior=db.execute('SELECT * FROM note_commands WHERE key=?',(key,)).fetchone()
            if prior:
                require(prior['digest']==digest,'idempotency_conflict','같은 요청 ID의 내용이 다릅니다',409);return json.loads(prior['receipt'])
            now=timestamp()
            if operation=='create':
                require(set(data)=={'task_id','title','parent_id','idempotency_key'},'invalid_field','새 노트 필드를 확인하세요');self.task(db,data['task_id'])
                require(db.execute('SELECT count(*) FROM note_pages WHERE task_id=?',(data['task_id'],)).fetchone()[0]<100,'too_many_notes','작업별 노트는 100개까지 만들 수 있습니다')
                parent=data['parent_id'];require(parent is None or isinstance(parent,str) and re.fullmatch('[A-Za-z0-9_-]{1,100}',parent),'invalid_parent','상위 노트 ID를 확인하세요');depth=0
                while parent:
                    row=db.execute('SELECT task_id,parent_id FROM note_pages WHERE id=?',(parent,)).fetchone();require(row is not None and row['task_id']==data['task_id'],'invalid_parent','같은 작업의 상위 노트를 선택하세요');depth+=1;require(depth<=8,'too_deep','하위 페이지는 8단계까지 만들 수 있습니다');parent=row['parent_id']
                page_id=str(uuid.uuid4());db.execute('INSERT INTO note_pages VALUES(?,?,?,?,?,?,?)',(page_id,data['task_id'],data['parent_id'],title,json.dumps([{'id':str(uuid.uuid4()),'type':'paragraph','text':''}]),1,now));revision=1
            else:
                require(operation=='save' and set(data)=={'page_id','expected_revision','title','blocks','idempotency_key'},'invalid_field','허용된 노트 저장 필드를 확인하세요');validate_blocks(data['blocks'])
                require(len(json.dumps(data['blocks']).encode())<=250000,'too_large','노트 크기를 줄여 주세요')
                require(isinstance(data['page_id'],str) and re.fullmatch('[A-Za-z0-9_-]{1,100}',data['page_id']),'invalid_page','노트 ID를 확인하세요');row=db.execute('SELECT revision FROM note_pages WHERE id=?',(data['page_id'],)).fetchone();require(row is not None,'note_not_found','노트를 찾을 수 없습니다',404)
                require(type(data['expected_revision']) is int and row['revision']==data['expected_revision'],'note_conflict','다른 곳에서 노트가 수정됐습니다. 입력을 보존하고 서버본을 확인하세요',409)
                page_id=data['page_id'];revision=row['revision']+1;db.execute('UPDATE note_pages SET title=?,blocks=?,revision=?,updated_at=? WHERE id=?',(title,json.dumps(data['blocks'],ensure_ascii=False),revision,now,page_id))
            receipt={'page_id':page_id,'revision':revision,'updated_at':now,'saved':True};db.execute('INSERT INTO note_commands VALUES(?,?,?)',(key,digest,json.dumps(receipt)));return receipt
