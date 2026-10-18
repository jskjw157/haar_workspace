from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from app.server import Store, Problem


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.store = Store(self.path)
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, operation, **data):
        self.n += 1
        return self.store.command(operation, {'idempotency_key': f'test-request-{self.n}', **data})['data']

    def create(self, **data):
        return self.command('create', title='실제 초안 테스트', **data)

    def test_persistence_and_no_fabricated_execution(self):
        result = self.create(route_id='vps_openclaw', deadline='2026-10-18')
        board = Store(self.path).snapshot('2026-10-17')
        self.assertEqual(board['records'][0]['id'], result['id'])
        self.assertIsNone(result['task_id'])
        self.assertIsNone(result['run_id'])
        self.assertFalse(result['sample'])
        self.assertTrue(all(not r['can_execute'] for r in board['routes']))

    def test_duplicate_command_returns_same_receipt_and_conflict_rejects(self):
        payload = {'idempotency_key': 'request-same-01', 'title': '하나만 생성'}
        first = self.store.command('create', payload)
        self.assertEqual(first, self.store.command('create', payload))
        self.assertFalse(first['dispatched'])
        with self.assertRaises(Problem) as error:
            self.store.command('create', {**payload, 'title':'다른 내용'})
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(len(self.store.snapshot('2026-10-17')['records']), 1)

    def test_concurrent_retry_is_single_writer(self):
        payload = {'idempotency_key': 'concurrent-key-01', 'title': '단일 접수'}
        with ThreadPoolExecutor(max_workers=6) as pool:
            receipts = list(pool.map(lambda _: self.store.command('create', payload), range(6)))
        self.assertTrue(all(r == receipts[0] for r in receipts))
        self.assertEqual(len(self.store.snapshot('2026-10-17')['records']), 1)

    def test_focus_three_unique_per_date_and_revision(self):
        records = [self.create() for _ in range(4)]
        ids = [r['id'] for r in records]
        self.command('focus', ids=ids[:3], local_date='2026-10-17', expected_revision=0)
        for invalid in [ids, [ids[0],ids[0]]]:
            with self.assertRaises(Problem):
                self.command('focus', ids=invalid, local_date='2026-10-17', expected_revision=1)
        with self.assertRaises(Problem) as error:
            self.command('focus', ids=[], local_date='2026-10-17', expected_revision=0)
        self.assertEqual(error.exception.code, 'stale_revision')
        self.assertEqual(self.store.snapshot('2026-10-18')['focus']['ids'], [])

    def test_stale_edit_rejected_without_overwriting(self):
        r = self.create()
        self.command('edit', id=r['id'], expected_revision=1, title='최신 제목')
        with self.assertRaises(Problem) as error:
            self.command('edit', id=r['id'], expected_revision=1, title='오래된 제목')
        self.assertEqual(error.exception.code, 'stale_revision')
        self.assertEqual(self.store.snapshot('2026-10-17')['records'][0]['title'], '최신 제목')

    def test_review_is_version_scoped_and_never_dispatches(self):
        r = self.create()
        r = self.command('artifact', id=r['id'], expected_revision=r['revision'], label='결과 v1', url='https://example.com/result', version_note='확인할 PDF v1')
        old_version = r['artifacts'][-1]['version_id']
        self.assertEqual(r['intake_stage'], 'review')
        r = self.command('review', id=r['id'], expected_revision=r['revision'], version_id=old_version, decision='approved', note='내용 확인')
        self.assertEqual(r['artifacts'][-1]['review'], 'approved')
        self.assertIsNone(r['run_id'])
        r = self.command('artifact', id=r['id'], expected_revision=r['revision'], label='결과 v2', url='https://example.com/v2', version_note='수정본 v2')
        with self.assertRaises(Problem) as error:
            self.command('review', id=r['id'], expected_revision=r['revision'], version_id=old_version, decision='approved', note='이전 버전 재승인')
        self.assertEqual(error.exception.code, 'stale_artifact')
        self.assertEqual(r['artifacts'][-1]['review'], 'pending')

    def test_link_validation_and_handoff_persistence(self):
        r = self.create()
        for url in ['javascript:alert(1)', 'http://example.com', 'https://user:password@example.com', 'https://example.com/ bad']:
            with self.assertRaises(Problem):
                self.command('artifact', id=r['id'], expected_revision=1, label='잘못된 링크', url=url, version_note='v1')
        r = self.command('handoff', id=r['id'], expected_revision=1, note='원본 확인 후 다음 작업', url='https://example.com/reference')
        self.assertEqual(r['handoffs'][0]['delivery'], 'manual')

    def test_schema_rejects_unreal_execution_and_bad_date(self):
        r = self.create()
        with self.assertRaises(Problem):
            self.command('edit', id=r['id'], expected_revision=1, intake_stage='in_progress')
        with self.assertRaises(Problem):
            self.create(deadline='2026-02-30')
        with self.assertRaises(Problem):
            self.command('edit', id=r['id'], expected_revision=1, run_id='forged-run')

    def test_sample_only_on_explicit_seed(self):
        self.assertEqual(self.store.snapshot('2026-10-17')['records'], [])
        self.command('demo')
        records = self.store.snapshot('2026-10-17')['records']
        self.assertEqual(len(records), 3)
        self.assertTrue(all(r['sample'] and r['sku'].startswith('DEMO') for r in records))
        with self.assertRaises(Problem):
            self.command('demo')

if __name__ == '__main__':
    unittest.main()
