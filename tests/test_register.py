import concurrent.futures
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from app.register import Register, RegisterError, validate_document
from app.server import Store


def document():
    return {"title": "Synthetic register", "version": 1, "updated_at": "2026-01-01T00:00:00Z", "status_definitions": {"대기": "waiting", "정지": "paused", "완료": "completed only to criteria"}, "guardrails": ["No dispatch"], "owner": "synthetic", "tasks": [{"id": f"TEST-{n:03d}", "task_name": f"Synthetic task {n}", "status": "대기", "status_detail": "Awaiting verification", "latest_instruction": "Do not dispatch", "next_action": "Check evidence", "blocker": "Needs user", "last_verified_at": "2026-01-01T00:00:00Z", "verification_basis": {"type": "synthetic"}, "completion_criteria": "Verified scope only", "unknown_extra": {"retained": [n]}, "result_library_ids": []} for n in range(19)]}


class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite3';self.intake=Store(self.path);self.register=Register(self.path);self.doc=document()

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, doc=None, version=1, expected=0, source='libfile_synthetic'):
        raw=json.dumps(doc or self.doc,ensure_ascii=False).encode()
        return self.register.import_document(raw,source,version,expected,hashlib.sha256(raw).hexdigest(),19)

    def proposal(self, **extra):
        return {"idempotency_key": "proposal-request-1", "task_id": "TEST-000", "expected_source_version": 1, "status": "정지", "status_detail": "Paused by verified request", "next_action": "Wait", "blocker": "Needs approval", "last_verified_at": "2026-01-02T00:00:00Z", "verification_note": "Explicit synthetic request", **extra}

    def test_initial_import_preserves_every_field_and_intake(self):
        before=self.intake.command('create',{'idempotency_key':'intake-preserve-1','title':'Existing intake'})
        self.assertEqual(self.load()['count'],19);self.assertEqual(self.register.snapshot()['document'],self.doc)
        self.assertEqual(self.intake.snapshot('2026-01-01')['records'][0]['id'],before['data']['id'])
        self.assertFalse(self.register.snapshot()['source']['automatic_library_refresh'])

    def test_duplicate_and_same_version_different_content(self):
        self.load();self.assertTrue(self.load()['duplicate']);changed=copy.deepcopy(self.doc);changed['tasks'][0]['status']='완료'
        with self.assertRaises(RegisterError):self.load(changed)
        snap=self.register.snapshot();self.assertEqual(snap['document'],self.doc);self.assertTrue(snap['source']['stale']);self.assertEqual(sum(e['kind']=='import' for e in snap['events']),1)

    def test_missing_duplicate_ids_and_bad_evidence_are_atomic(self):
        self.load()
        for kind in ('duplicate','criteria','time','status'):
            d=copy.deepcopy(self.doc)
            if kind=='duplicate':d['tasks'][1]['id']=d['tasks'][0]['id']
            if kind=='criteria':del d['tasks'][0]['completion_criteria']
            if kind=='time':d['tasks'][0]['last_verified_at']='invalid'
            if kind=='status':d['tasks'][0]['status']={}
            with self.assertRaises(RegisterError):self.load(d,2,1)
            self.assertEqual(self.register.snapshot()['document'],self.doc)

    def test_proposal_does_not_change_canonical_or_dispatch(self):
        self.load();first=self.register.command('propose',self.proposal());self.assertEqual(first,self.register.command('propose',self.proposal()));self.assertFalse(first['dispatched']);self.assertFalse(first['library_updated'])
        self.assertEqual(self.register.snapshot()['document'],self.doc)
        with self.assertRaises(RegisterError):self.register.command('propose',self.proposal(status='완료'))
        with self.assertRaises(RegisterError):self.register.command('propose',self.proposal(idempotency_key='another-request-2'))

    def test_export_is_frozen_and_preserves_criteria_unknown_and_other_tasks(self):
        self.load();r=self.register.command('propose',self.proposal());export=self.register.export(r['proposal_id']);self.assertEqual(export,self.register.export(r['proposal_id']))
        candidate=export['candidate_document'];self.assertEqual(candidate['tasks'][1:],self.doc['tasks'][1:]);self.assertEqual(candidate['tasks'][0]['completion_criteria'],self.doc['tasks'][0]['completion_criteria']);self.assertEqual(candidate['tasks'][0]['unknown_extra'],self.doc['tasks'][0]['unknown_extra']);self.assertEqual(export['expected_current_version'],1)
        self.assertIn('unknown_extra',export['markdown']);self.assertEqual(candidate['tasks'][0]['status'],'정지');self.assertEqual(self.register.snapshot()['document']['tasks'][0]['status'],'대기')
        self.load(candidate,2,1);snap=self.register.snapshot();self.assertEqual(snap['proposals'][0]['state'],'confirmed');self.assertEqual(snap['document']['tasks'][0]['status'],'정지')

    def test_original_change_conflicts_pending_proposal(self):
        self.load();p=self.register.command('propose',self.proposal());d=copy.deepcopy(self.doc);d['version']=2;d['tasks'][1]['status']='정지';self.load(d,2,1)
        self.assertEqual(self.register.snapshot()['proposals'][0]['state'],'conflict')
        with self.assertRaises(RegisterError):self.register.export(p['proposal_id'])
        with self.assertRaises(RegisterError):self.register.command('propose',self.proposal(idempotency_key='stale-new-request'))

    def test_source_and_removed_tasks_and_hash_fail_closed(self):
        self.load()
        with self.assertRaises(RegisterError):self.load(version=2,expected=1,source='libfile_other')
        d=copy.deepcopy(self.doc);d['tasks'][0]['id']='replacement'
        with self.assertRaises(RegisterError):self.load(d,2,1)
        with self.assertRaises(RegisterError):self.register.import_document(b'{}','libfile_synthetic',2,1,'0'*64)
        self.assertEqual(self.register.snapshot()['document'],self.doc)

    def test_concurrent_import_and_proposals_are_single_writer(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.load(),range(2)))
        self.assertEqual(sum(not r['duplicate'] for r in results),1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:receipts=list(pool.map(lambda _:self.register.command('propose',self.proposal()),range(2)))
        self.assertEqual(receipts[0],receipts[1]);self.assertEqual(len(self.register.snapshot()['proposals']),1)

    def test_cancel_and_restart_keep_audit(self):
        self.load();p=self.register.command('propose',self.proposal());r=self.register.command('cancel',{'idempotency_key':'cancel-request-1','proposal_id':p['proposal_id']});self.assertEqual(r['state'],'cancelled')
        reopened=Register(self.path).snapshot();self.assertEqual(len(reopened['document']['tasks']),19);self.assertEqual(reopened['proposals'][0]['state'],'cancelled');self.assertEqual(reopened['events'][0]['kind'],'cancelled')

    def test_unknown_fields_and_future_evidence_rejected(self):
        self.load()
        for patch in ({'completion_criteria':'Changed goal'},{'last_verified_at':'2999-01-01T00:00:00Z'},{'verification_note':''}):
            with self.assertRaises(RegisterError):self.register.command('propose',self.proposal(**patch))

    def test_missing_source_evidence_is_preserved_and_flagged_without_invention(self):
        del self.doc['tasks'][0]['verification_basis'];self.load();s=self.register.snapshot();self.assertEqual(s['warnings'][0]['task_id'],'TEST-000');self.assertNotIn('verification_basis',s['document']['tasks'][0])


if __name__=='__main__':unittest.main()
