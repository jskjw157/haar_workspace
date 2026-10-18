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

if __name__ == '__main__':
    unittest.main()
