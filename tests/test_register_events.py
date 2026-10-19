import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from app.register import Register,RegisterError
from app.server import Store
from test_register import document

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
class EventTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db.sqlite3';Store(self.path);self.r=Register(self.path);self.doc=document();raw=json.dumps(self.doc).encode();self.r.import_document(raw,'libfile_synthetic',8,0,hashlib.sha256(raw).hexdigest(),19)
 def tearDown(self):self.temp.cleanup()
 def event(self,**extra):
  return {'source_event_id':'parent-event-0001','idempotency_key':'delivery-key-0001','publisher_id':'haar-parent','expected_revision':8,'task_id':'TEST-000','base_task_sha256':digest(self.doc['tasks'][0]),'changes':{'status':'완료','status_detail':'Criteria verified','next_action':'Review result','blocker':'','last_verified_at':'2026-01-02T00:00:00Z'},'verification_note':'Observed actual result',**extra}
 def test_event_changes_one_task_once_and_preserves_all_protected_fields(self):
  self.assertTrue(callable(getattr(self.r,'apply_event',None)),'Missing change event API')
  a=self.r.apply_event(self.event());b=self.r.apply_event(self.event());self.assertEqual(a['revision'],9);self.assertTrue(b['duplicate']);s=self.r.snapshot();self.assertEqual(s['document']['tasks'][0]['status'],'완료');self.assertEqual(s['document']['tasks'][1:],self.doc['tasks'][1:]);self.assertEqual(s['document']['tasks'][0]['completion_criteria'],self.doc['tasks'][0]['completion_criteria']);self.assertEqual(s['document']['tasks'][0]['unknown_extra'],self.doc['tasks'][0]['unknown_extra']);self.assertEqual(s['source']['library_version'],8);self.assertEqual(s['source']['bridge'],'parent_events');self.assertEqual(s['source']['version'],9)
 def test_conflicts_old_evidence_and_approval_changes_never_overwrite(self):
  self.assertTrue(callable(getattr(self.r,'apply_event',None)),'Missing change event API')
  for patch in [{'expected_revision':7},{'base_task_sha256':'0'*64},{'changes':{**self.event()['changes'],'completion_criteria':'weaker'}},{'changes':{**self.event()['changes'],'priority_proposal':'P0'}},{'changes':{**self.event()['changes'],'last_verified_at':'2025-01-01T00:00:00Z'}}]:
   with self.assertRaises(RegisterError):self.r.apply_event(self.event(**patch))
   self.assertEqual(self.r.snapshot()['document'],self.doc)
 def test_event_id_collision_import_cutover_and_publisher_offline(self):
  self.assertTrue(callable(getattr(self.r,'apply_event',None)),'Missing change event API')
  self.r.apply_event(self.event())
  with self.assertRaises(RegisterError):self.r.apply_event(self.event(verification_note='Different event content'))
  raw=json.dumps(self.doc).encode()
  with self.assertRaises(RegisterError):self.r.import_document(raw,'libfile_synthetic',10,9,hashlib.sha256(raw).hexdigest(),19)
  with self.r.db() as db:db.execute("UPDATE register_stream SET last_seen_at='2000-01-01T00:00:00Z'")
  self.assertTrue(self.r.snapshot()['source']['publisher_offline']);self.r.heartbeat({'publisher_id':'haar-parent','pending':1,'blocked':0});self.assertEqual(self.r.snapshot()['source']['pending_delivery'],1);self.assertFalse(self.r.snapshot()['source']['publisher_offline'])

 def test_concurrent_distinct_changes_have_one_revision_winner(self):
  from concurrent.futures import ThreadPoolExecutor
  def deliver(n):
   try:return self.r.apply_event(self.event(source_event_id='parallel-event-000'+str(n),idempotency_key='parallel-key-000'+str(n)))
   except RegisterError as e:return e.code
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(deliver,[1,2]))
  self.assertEqual(sum(isinstance(r,dict) for r in results),1);self.assertIn('revision_conflict',results);self.assertEqual(self.r.snapshot()['source']['version'],9)
