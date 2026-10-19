import hashlib,json,tempfile,unittest,importlib.util
from pathlib import Path
from app.register import Register,RegisterError
from app.server import Store
from test_register import document
class NotesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3';Store(self.path);self.reg=Register(self.path);raw=json.dumps(document()).encode();self.reg.import_document(raw,'libfile_synthetic',8,0,hashlib.sha256(raw).hexdigest(),19)
 def tearDown(self):self.tmp.cleanup()
 def store(self):
  self.assertIsNotNone(importlib.util.find_spec('app.notes'),'Missing VPS notes store')
  from app.notes import Notes
  return Notes(self.path)
 def create(self,s,**patch):return s.command('create',{'task_id':'TEST-000','title':'운영 메모','parent_id':None,'idempotency_key':'create-note-00001',**patch})
 def blocks(self):return [{'id':'block-1','type':'paragraph','text':'<script>plain text</script>'},{'id':'block-2','type':'check','text':'확인','checked':True},{'id':'block-3','type':'table','cells':[['항목','상태'],['저장','검증']]}]
 def save(self,s,p,**patch):return s.command('save',{'page_id':p['page_id'],'expected_revision':1,'title':'업무 메모','blocks':self.blocks(),'idempotency_key':'save-note-000001',**patch})
 def test_saved_blocks_restore_after_reconnect_without_touching_register(self):
  s=self.store();before=self.reg.snapshot()['document'];p=self.create(s);r=self.save(s,p);self.assertEqual(r['revision'],2);reopened=self.store().page(p['page_id']);self.assertEqual(reopened['blocks'],self.blocks());self.assertEqual(self.reg.snapshot()['document'],before)
 def test_idempotent_save_collision_and_concurrent_revision_conflict(self):
  s=self.store();p=self.create(s);a=self.save(s,p);self.assertEqual(self.save(s,p),a)
  with self.assertRaises(RegisterError):self.save(s,p,title='changed payload')
  with self.assertRaises(RegisterError):self.save(s,p,idempotency_key='stale-save-00002')
  self.assertEqual(s.page(p['page_id'])['revision'],2)
 def test_child_page_search_and_cross_task_parent_rejected(self):
  s=self.store();p=self.create(s);child=self.create(s,parent_id=p['page_id'],title='상품 검수',idempotency_key='child-note-00001');self.assertEqual(s.page(child['page_id'])['parent_id'],p['page_id']);self.assertEqual(len(s.list('TEST-000','상품')['pages']),1);self.save(s,p);self.assertEqual(len(s.list('TEST-000','block-1')['pages']),0)
  with self.assertRaises(RegisterError):self.create(s,task_id='TEST-001',parent_id=p['page_id'],idempotency_key='wrong-task-00001')
 def test_unknown_task_and_invalid_blocks_do_not_write(self):
  s=self.store()
  with self.assertRaises(RegisterError):self.create(s,task_id='UNKNOWN')
  p=self.create(s)
  for blocks in [[{'id':'x','type':'html','text':'unsafe'}],[{'id':'x','type':'table','cells':[['a'],['a','b']]}],[{'id':'x','type':'check','text':'a','checked':'true'}]]:
   with self.assertRaises(RegisterError):self.save(s,p,blocks=blocks)
  self.assertEqual(s.page(p['page_id'])['revision'],1)

 def test_two_writers_have_one_revision_winner(self):
  from concurrent.futures import ThreadPoolExecutor
  s=self.store();p=self.create(s)
  def write(n):
   try:return self.save(s,p,idempotency_key='parallel-notes-000'+str(n))
   except RegisterError as e:return e.code
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(write,[1,2]))
  self.assertEqual(sum(isinstance(r,dict) for r in results),1);self.assertIn('note_conflict',results)
