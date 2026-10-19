import http.client
import json
import tempfile
import threading
import unittest
from app.server import build_server


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server = build_server(cls.tmp.name + '/test.sqlite3', 0)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def request(self, method, path, body=None, host=None, origin=None, content_type='application/json'):
        host = host or f'127.0.0.1:{self.port}'
        headers = {'Host':host}
        if body is not None:
            headers.update({'Content-Type':content_type, 'Origin':origin or 'http://' + host})
        connection = http.client.HTTPConnection('127.0.0.1', self.port)
        connection.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=headers)
        response = connection.getresponse()
        data = response.read()
        result = (response.status, dict(response.getheaders()), data)
        connection.close()
        return result

    def test_loopback_only_and_host_rebinding_denied(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        self.assertEqual(self.request('GET', '/api/board?date=2026-10-17', host='evil.example:3310')[0],403)
        self.assertEqual(self.request('GET', '/api/health')[0],200)

    def test_external_origin_and_wrong_content_type_denied(self):
        data = {'idempotency_key':'http-csrf-test', 'title':'CSRF'}
        self.assertEqual(self.request('POST','/api/records',data,origin='https://evil.example')[0],403)
        self.assertEqual(self.request('POST','/api/records',data,content_type='text/plain')[0],415)

    def test_security_headers_and_static_allowlist(self):
        status, headers, body = self.request('GET','/')
        self.assertEqual(status,200)
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(headers['Referrer-Policy'],'no-referrer')
        self.assertIn(b'HAAR',body)
        self.assertEqual(self.request('GET','/../server.py')[0],404)
        self.assertEqual(self.request('GET','/.data/workspace.sqlite3')[0],404)
        paths = [f'/illustrations/{name}.webp' for name in ('focus', 'empty', 'review', 'connection')]
        paths += [f'/banners/{name}.webp' for name in ('today', 'all', 'review', 'agents')]
        for image_path in paths:
            status, image_headers, image = self.request('GET',image_path)
            self.assertEqual(status,200)
            self.assertEqual(image_headers['Content-Type'],'image/webp')
            self.assertEqual(image[:4],b'RIFF')
        self.assertEqual(self.request('GET','/illustrations/../server.py')[0],404)
        self.assertEqual(self.request('GET','/illustrations/unknown.webp')[0],404)
        self.assertEqual(self.request('GET','/banners/../server.py')[0],404)
        self.assertEqual(self.request('GET','/banners/unknown.webp')[0],404)

    def test_unknown_and_oversized_requests_not_accepted(self):
        self.assertEqual(self.request('POST','/api/execute',{'idempotency_key':'no-execution'})[0],404)
        self.assertEqual(self.request('POST','/api/records',{'title':'a' * 17000})[0],413)
        self.assertEqual(self.request('GET','/api/board?date=2026-02-30')[0],422)

    def test_valid_create_returns_stable_receipt(self):
        data = {'idempotency_key':'http-create-test','title':'지속 저장'}
        first = self.request('POST','/api/records',data)
        second = self.request('POST','/api/records',data)
        self.assertEqual(first[0],200)
        self.assertEqual(first[2],second[2])
        self.assertFalse(json.loads(first[2])['dispatched'])

    def test_parent_events_keep_same_origin_and_body_limits(self):
        for path in ('/api/register/events','/api/register/heartbeat'):
            self.assertEqual(self.request('POST',path,{},origin='https://evil.example')[0],403)
            self.assertEqual(self.request('POST',path,{'payload':'a'*17000})[0],413)
        self.assertEqual(self.request('GET','/api/register/revision')[0],200)

    def test_register_boundary_and_empty_source(self):
        status,headers,body=self.request('GET','/api/register')
        self.assertEqual(status,200);self.assertIsNone(json.loads(body)['document']);self.assertFalse(json.loads(body)['source']['automatic_library_refresh'])
        self.assertEqual(self.request('GET','/register')[0],200)
        self.assertEqual(self.request('GET','/register.js')[0],200)
        self.assertEqual(self.request('GET','/register.css')[0],200)
        self.assertEqual(self.request('POST','/api/register/import',{})[0],404)
        self.assertEqual(self.request('POST','/api/register/proposals',{'idempotency_key':'register-csrf'},origin='https://evil.example')[0],403)
        self.assertEqual(self.request('POST','/api/register/export',[])[0],400)
        self.assertEqual(self.request('GET','/register/../register.py')[0],404)

class RegisterFlowHTTPTests(unittest.TestCase):
    request=HTTPTests.request

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=build_server(self.tmp.name+'/http.sqlite3',0);self.port=self.server.server_port;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.tmp.cleanup()

    def test_import_proposal_export_confirmation_is_visible_in_http_and_audit(self):
        from test_register import document
        import hashlib
        doc=document();raw=json.dumps(doc,ensure_ascii=False).encode();self.server.register.import_document(raw,'libfile_synthetic',1,0,hashlib.sha256(raw).hexdigest(),19)
        s=json.loads(self.request('GET','/api/register')[2]);self.assertEqual(len(s['document']['tasks']),19)
        body={'idempotency_key':'http-register-proposal','task_id':'TEST-000','expected_source_version':1,'status':'정지','status_detail':'Paused on request','next_action':'Wait','blocker':'Needs approval','last_verified_at':'2026-01-02T00:00:00Z','verification_note':'Synthetic confirmed instruction'}
        status,_,result=self.request('POST','/api/register/proposals',body);self.assertEqual(status,200);proposal=json.loads(result)
        s=json.loads(self.request('GET','/api/register')[2]);self.assertEqual(s['proposals'][0]['state'],'pending');self.assertEqual(s['document']['tasks'][0]['status'],'대기');self.assertEqual(s['events'][0]['kind'],'proposed')
        status,_,export=self.request('POST','/api/register/export',{'proposal_id':proposal['proposal_id']});self.assertEqual(status,200);candidate=json.loads(export)['candidate_document'];raw=json.dumps(candidate,ensure_ascii=False).encode();self.server.register.import_document(raw,'libfile_synthetic',2,1,hashlib.sha256(raw).hexdigest(),19)
        s=json.loads(self.request('GET','/api/register')[2]);self.assertEqual(s['document']['tasks'][0]['status'],'정지');self.assertEqual(s['source']['version'],2);self.assertEqual(s['proposals'][0]['state'],'confirmed');self.assertIn('confirmed',[e['kind'] for e in s['events']]);self.assertFalse(s['dispatched'])


if __name__ == '__main__':
    unittest.main()
