import hashlib,http.client,json,tempfile,threading,unittest
from app.server import build_server
from test_register import document
class NotesHTTPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=self.tmp.name+'/notes.sqlite3';self.start();raw=json.dumps(document()).encode();self.server.register.import_document(raw,'libfile_synthetic',8,0,hashlib.sha256(raw).hexdigest(),19)
 def start(self):
  self.server=build_server(self.path,0);self.port=self.server.server_port;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def stop(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def tearDown(self):self.stop();self.tmp.cleanup()
 def req(self,method,path,body=None,origin=None):
  host='127.0.0.1:'+str(self.port);c=http.client.HTTPConnection('127.0.0.1',self.port);c.request(method,path,json.dumps(body).encode() if body is not None else None,{'Host':host,'Origin':origin or 'http://'+host,'Content-Type':'application/json'});r=c.getresponse();b=r.read();status=r.status;c.close();return status,json.loads(b) if path.startswith('/api/') else b
 def test_save_fresh_connection_and_server_restart_restore_shared_note(self):
  status,p=self.req('POST','/api/notes/pages',{'task_id':'TEST-000','title':'공유 노트','parent_id':None,'idempotency_key':'http-note-create1'});self.assertEqual(status,200)
  blocks=[{'id':'b1','type':'paragraph','text':'<img src=x onerror=alert(1)>'},{'id':'b2','type':'table','cells':[['구분','결과'],['재접속','확인']]}]
  payload={'page_id':p['page_id'],'title':'공유 메모','blocks':blocks,'expected_revision':1,'idempotency_key':'http-note-save01'}
  a=self.req('POST','/api/notes/save',payload);self.assertEqual(a[0],200);self.assertEqual(a,self.req('POST','/api/notes/save',payload));self.stop();self.start();status,page=self.req('GET','/api/notes/page?page_id='+p['page_id']);self.assertEqual(status,200);self.assertEqual(page['blocks'],blocks);self.assertEqual(page['revision'],2)
  self.assertEqual(self.req('POST','/api/notes/save',{**payload,'idempotency_key':'http-stale-save1'})[0],409)
 def test_notes_keep_host_origin_size_and_static_boundaries(self):
  self.assertEqual(self.req('POST','/api/notes/pages',{},origin='https://evil.example')[0],403)
  status,error=self.req('POST','/api/notes/save',{'text':'a'*270000});self.assertEqual(status,413);self.assertIn('256KiB',error['error']['message'])
  self.assertEqual(self.req('GET','/api/notes?task_id=UNKNOWN')[0],404)
  self.assertEqual(self.req('GET','/notes?task=TEST-000')[0],200)
  self.assertEqual(self.req('GET','/notes-state.js')[0],200)
