import importlib.util,json,tempfile,threading,unittest
from pathlib import Path
from app.server import build_server
from test_register import document
import hashlib
class PublisherTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.server=build_server(self.tmp.name+'/server.sqlite3',0);doc=document();raw=json.dumps(doc).encode();self.server.register.import_document(raw,'libfile_synthetic',8,0,hashlib.sha256(raw).hexdigest(),19);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.origin='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def publisher(self):
  self.assertIsNotNone(importlib.util.find_spec('app.publisher'),'Missing durable publisher')
  from app.publisher import Publisher
  return Publisher(Path(self.tmp.name)/'queue.sqlite3',self.origin)
 def draft(self,event='actual-event-00001'):
  return {'source_event_id':event,'task_id':'TEST-000','changes':{'status':'완료','status_detail':'Actual observation','last_verified_at':'2026-01-02T00:00:00Z'},'verification_note':'Criteria verified'}
 def test_offline_queue_survives_restart_then_delivers_without_manual_import(self):
  p=self.publisher();p.sync();p.origin='http://127.0.0.1:1';p.enqueue(self.draft());self.assertIsNone(p.flush_once(now=1));self.assertEqual(p.status()['pending'],1)
  from app.publisher import Publisher
  reopened=Publisher(p.path,self.origin);self.assertEqual(reopened.flush_once(now=10000000000)['revision'],9);self.assertEqual(reopened.status()['acked'],1);self.assertEqual(self.server.register.snapshot()['document']['tasks'][0]['status'],'완료')
 def test_lost_ack_retry_is_deduplicated_and_conflict_holds_queue(self):
  p=self.publisher();p.enqueue(self.draft());payload=p.head()['payload'];self.server.register.apply_event(payload);receipt=p.flush_once(now=10000000000);self.assertTrue(receipt['duplicate']);self.assertEqual(len([e for e in self.server.register.snapshot()['events'] if e['kind']=='parent_change']),1)
  p.enqueue(self.draft('actual-event-00002'));payload=p.head()['payload'];other={**payload,'source_event_id':'external-event-0003','idempotency_key':'external-key-00003'};self.server.register.apply_event(other);self.assertIsNone(p.flush_once(now=10000000000));self.assertEqual(p.status()['conflict'],1);self.assertEqual(self.server.register.snapshot()['source']['version'],10)
 def test_same_source_id_changed_content_is_not_silently_replaced(self):
  p=self.publisher();p.enqueue(self.draft())
  with self.assertRaises(ValueError):p.enqueue({**self.draft(),'verification_note':'Different content'})
