"""Library-confirmed task register and version-scoped proposals. Never dispatches work."""
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class RegisterError(Exception):
    def __init__(self, code, message, status=422):
        self.code, self.message, self.status = code, message, status


def require(test, code, message, status=422):
    if not test:
        raise RegisterError(code, message, status)


def iso_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None, "invalid_time", "확인 시각에는 시간대가 필요합니다")
        require(parsed <= datetime.now(timezone.utc), "future_time", "미래를 확인 시각으로 기록할 수 없습니다")
    except (ValueError, AttributeError, TypeError):
        raise RegisterError("invalid_time", "올바른 확인 시각을 입력하세요")
    return value


def validate_document(raw):
    require(len(raw) <= 2_000_000, "too_large", "원본은 2MB 이내여야 합니다")
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise RegisterError("invalid_document", "원본 JSON을 확인하세요")
    require(isinstance(doc, dict), "invalid_document", "JSON 객체가 필요합니다")
    tasks, definitions = doc.get("tasks"), doc.get("status_definitions")
    require(isinstance(tasks, list) and 0 < len(tasks) <= 1000 and isinstance(definitions, dict) and definitions, "invalid_document", "작업과 상태 정의가 필요합니다")
    require(type(doc.get("version")) is int and doc["version"] > 0, "invalid_document", "문서 버전이 필요합니다")
    iso_time(doc.get("updated_at"))
    ids = set()
    for task in tasks:
        require(isinstance(task, dict), "invalid_task", "작업 객체가 필요합니다")
        task_id = task.get("id")
        require(isinstance(task_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", task_id) and task_id not in ids, "duplicate_id", "작업 ID는 고유해야 합니다")
        ids.add(task_id)
        require(isinstance(task.get("status"), str) and task["status"] in definitions, "invalid_status", "정의된 작업 상태가 필요합니다")
        for field in ("task_name", "completion_criteria"):
            require(isinstance(task.get(field), str) and task[field].strip(), "missing_field", field + "가 필요합니다")
        for field in ("status_detail", "next_action", "blocker", "latest_instruction"):
            require(isinstance(task.get(field), str), "missing_field", field + " 문자열이 필요합니다")
        require("verification_basis" not in task or isinstance(task["verification_basis"], dict), "invalid_evidence", "확인 근거 형식을 확인하세요")
        require("evidence" not in task or isinstance(task["evidence"], str), "invalid_evidence", "확인 근거 형식을 확인하세요")
        iso_time(task.get("last_verified_at"))
    return doc


class Register:
    def __init__(self, path):
        self.path = str(path)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS register_snapshots (
                    library_id TEXT NOT NULL, version INTEGER NOT NULL, digest TEXT NOT NULL,
                    document TEXT NOT NULL, imported_at TEXT NOT NULL,
                    PRIMARY KEY(library_id, version)
                );
                CREATE TABLE IF NOT EXISTS register_state (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), library_id TEXT,
                    version INTEGER, last_attempt_at TEXT, last_error TEXT
                );
                INSERT OR IGNORE INTO register_state(singleton) VALUES(1);
                CREATE TABLE IF NOT EXISTS register_proposals (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, base_version INTEGER NOT NULL,
                    changes TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL,
                    exported_at TEXT, candidate TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS register_one_pending ON register_proposals(task_id) WHERE state='pending';
                CREATE TABLE IF NOT EXISTS register_stream (singleton INTEGER PRIMARY KEY CHECK(singleton=1), library_version INTEGER NOT NULL, last_seen_at TEXT NOT NULL, pending INTEGER NOT NULL, blocked INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS register_deliveries (source_event_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, digest TEXT NOT NULL, receipt TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS register_commands (key TEXT PRIMARY KEY, digest TEXT NOT NULL, receipt TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS register_events (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, task_id TEXT, body TEXT NOT NULL, occurred_at TEXT NOT NULL);
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=5000")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def current(self, db):
        return db.execute("SELECT s.* FROM register_snapshots s JOIN register_state p ON p.library_id=s.library_id AND p.version=s.version WHERE p.singleton=1").fetchone()

    def event(self, db, kind, task_id, body):
        db.execute("INSERT INTO register_events(kind,task_id,body,occurred_at) VALUES(?,?,?,?)", (kind, task_id, json.dumps(body, ensure_ascii=False), timestamp()))

    def import_document(self, raw, library_id, version, expected_version, expected_sha, expected_count=None):
        try:
            require(re.fullmatch(r"libfile_[a-zA-Z0-9_-]+", library_id or ""), "invalid_source", "Library 원본 ID가 필요합니다")
            require(type(version) is int and version > 0 and type(expected_version) is int, "invalid_version", "Library 버전을 확인하세요")
            digest = hashlib.sha256(raw).hexdigest()
            require(digest == expected_sha, "digest_mismatch", "원본 파일 해시가 다릅니다")
            doc = validate_document(raw)
            require(expected_count is None or len(doc["tasks"]) == expected_count, "count_mismatch", "작업 수가 기대값과 다릅니다")
            with self.db() as db:
                db.execute("BEGIN IMMEDIATE")
                old = self.current(db)
                require(not old or old["library_id"] == library_id, "source_conflict", "다른 Library 원본으로 교체할 수 없습니다", 409)
                require(not db.execute("SELECT 1 FROM register_stream").fetchone(), "event_source_active", "운영 원본은 부모 이벤트입니다. Library import로 덮어쓸 수 없습니다", 409)
                current_version = old["version"] if old else 0
                if old and version == current_version:
                    require(digest == old["digest"], "version_conflict", "같은 Library 버전의 내용이 다릅니다", 409)
                    db.execute("UPDATE register_state SET last_attempt_at=?,last_error=NULL WHERE singleton=1", (timestamp(),))
                    return {"duplicate": True, "version": version, "count": len(doc["tasks"])}
                require(version > current_version and current_version == expected_version, "version_conflict", "원본 버전이 변경되었습니다. 최신본을 다시 확인하세요", 409)
                if old:
                    prior_ids = {t["id"] for t in json.loads(old["document"])["tasks"]}
                    require(prior_ids <= {t["id"] for t in doc["tasks"]}, "removed_task", "기존 작업 삭제는 별도 확인이 필요합니다", 409)
                db.execute("INSERT INTO register_snapshots VALUES(?,?,?,?,?)", (library_id, version, digest, raw.decode("utf-8"), timestamp()))
                db.execute("UPDATE register_state SET library_id=?,version=?,last_attempt_at=?,last_error=NULL WHERE singleton=1", (library_id, version, timestamp()))
                tasks = {t["id"]: t for t in doc["tasks"]}
                for p in db.execute("SELECT * FROM register_proposals WHERE state='pending'").fetchall():
                    changes = json.loads(p["changes"])
                    state = "confirmed" if all(tasks.get(p["task_id"], {}).get(k) == v for k, v in changes.items()) else "conflict"
                    db.execute("UPDATE register_proposals SET state=? WHERE id=?", (state, p["id"]))
                    self.event(db, state, p["task_id"], {"proposal_id": p["id"], "source_version": version})
                self.event(db, "import", None, {"library_id": library_id, "version": version, "digest": digest, "count": len(doc["tasks"])})
                return {"duplicate": False, "version": version, "count": len(doc["tasks"])}
        except RegisterError as e:
            with self.db() as db:
                db.execute("UPDATE register_state SET last_attempt_at=?,last_error=? WHERE singleton=1", (timestamp(), e.code))
                self.event(db, "import_failed", None, {"code": e.code})
            raise

    def snapshot(self):
        with self.db() as db:
            current = self.current(db)
            state = dict(db.execute("SELECT * FROM register_state WHERE singleton=1").fetchone())
            proposals = [dict(p) for p in db.execute("SELECT id,task_id,base_version,changes,state,created_at,exported_at FROM register_proposals ORDER BY created_at DESC")]
            for p in proposals:
                p["changes"] = json.loads(p["changes"])
            events = [dict(e) for e in db.execute("SELECT * FROM register_events ORDER BY id DESC LIMIT 50")]
            for e in events:
                e["body"] = json.loads(e["body"])
            from app.register_events import source_status
            bridge = source_status(db, current)
            document = json.loads(current["document"]) if current else None
            warnings = [{"task_id": t["id"], "field": "verification_basis", "message": "원본에 확인 근거가 미기록되어 있습니다"} for t in document["tasks"] if not t.get("verification_basis") and not t.get("evidence")] if document else []
            return {"source": {**state, "digest": current["digest"] if current else None, "imported_at": current["imported_at"] if current else None, "automatic_library_refresh": False, "bridge": "authorized_consumer_import", **bridge, "stale": bool(state["last_error"] or bridge.get("publisher_offline") or bridge.get("pending_delivery") or bridge.get("blocked_delivery"))}, "document": document, "warnings": warnings, "proposals": proposals, "events": events, "fetched_at": timestamp(), "dispatched": False}

    def apply_event(self, data):
        from app.register_events import apply_event
        return apply_event(self, data)

    def heartbeat(self, data):
        from app.register_events import heartbeat
        return heartbeat(self, data)

    def revision(self):
        with self.db() as db:
            from app.register_events import source_status
            current = self.current(db)
            return {"revision": current["version"] if current else 0, "cursor": db.execute("SELECT COALESCE(MAX(id),0) FROM register_events").fetchone()[0], **source_status(db,current)}

    def command(self, operation, data):
        require(isinstance(data, dict), "invalid_json", "JSON 객체가 필요합니다", 400)
        key = data.get("idempotency_key")
        require(isinstance(key, str) and re.fullmatch(r"[A-Za-z0-9_-]{8,128}", key), "invalid_key", "요청 식별자가 필요합니다")
        digest = hashlib.sha256(json.dumps([operation, data], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT * FROM register_commands WHERE key=?", (key,)).fetchone()
            if prior:
                require(prior["digest"] == digest, "idempotency_conflict", "같은 요청 식별자의 내용이 다릅니다", 409)
                return json.loads(prior["receipt"])
            if operation == "cancel":
                p = db.execute("SELECT * FROM register_proposals WHERE id=?", (data.get("proposal_id"),)).fetchone()
                require(p and p["state"] == "pending", "proposal_conflict", "반영 대기 제안을 다시 확인하세요", 409)
                db.execute("UPDATE register_proposals SET state='cancelled' WHERE id=?", (p["id"],))
                result = {"proposal_id": p["id"], "state": "cancelled"}
                self.event(db, "cancelled", p["task_id"], result)
            else:
                require(operation == "propose", "unknown_command", "지원하지 않는 요청입니다", 404)
                old = self.current(db)
                require(old and type(data.get("expected_source_version")) is int and data["expected_source_version"] == old["version"], "source_conflict", "Library 확인본이 변경되었습니다", 409)
                doc = json.loads(old["document"])
                task = next((t for t in doc["tasks"] if t["id"] == data.get("task_id")), None)
                require(task, "not_found", "작업을 찾을 수 없습니다", 404)
                require(not db.execute("SELECT 1 FROM register_proposals WHERE task_id=? AND state='pending'", (task["id"],)).fetchone(), "proposal_conflict", "이미 반영 대기 제안이 있습니다", 409)
                fields = ("status", "status_detail", "next_action", "blocker", "last_verified_at", "verification_note")
                require(not set(data) - set(fields) - {"task_id", "expected_source_version", "idempotency_key"}, "invalid_field", "허용되지 않은 수정 필드입니다")
                for field in fields:
                    require(isinstance(data.get(field), str) and len(data[field]) <= 4000, "invalid_field", field + " 문자열을 확인하세요")
                require(data["status"] in doc["status_definitions"], "invalid_status", "정의된 상태를 선택하세요")
                require(data["verification_note"].strip() and data["status_detail"].strip(), "missing_evidence", "상태 설명과 확인 근거가 필요합니다")
                iso_time(data["last_verified_at"])
                require(datetime.fromisoformat(data["last_verified_at"].replace("Z", "+00:00")) >= datetime.fromisoformat(task["last_verified_at"].replace("Z", "+00:00")), "stale_evidence", "기존 확인 시각보다 과거인 제안은 저장할 수 없습니다", 409)
                changes = {k: data[k] for k in fields if k != "verification_note"}
                changes["verification_basis"] = {"type": "workspace_user_confirmation", "note": data["verification_note"], "previous": task.get("verification_basis", {"evidence": task.get("evidence")})}
                proposal_id = str(uuid.uuid4())
                db.execute("INSERT INTO register_proposals VALUES(?,?,?,?,?,?,NULL,NULL)", (proposal_id, task["id"], old["version"], json.dumps(changes, ensure_ascii=False), "pending", timestamp()))
                result = {"proposal_id": proposal_id, "state": "pending", "task_id": task["id"], "source_version": old["version"]}
                self.event(db, "proposed", task["id"], result)
            receipt = {**result, "saved_at": timestamp(), "dispatched": False, "library_updated": False}
            db.execute("INSERT INTO register_commands VALUES(?,?,?)", (key, digest, json.dumps(receipt, ensure_ascii=False)))
            return receipt

    def export(self, proposal_id):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            require(not db.execute("SELECT 1 FROM register_stream").fetchone(), "event_source_active", "부모 이벤트 원본의 제안은 부모가 검토해야 합니다. Library 후보 내보내기는 중지됐습니다", 409)
            current = self.current(db)
            p = db.execute("SELECT * FROM register_proposals WHERE id=?", (proposal_id,)).fetchone()
            require(current and p and p["state"] == "pending" and p["base_version"] == current["version"], "source_conflict", "원본이 바뀌었거나 유효한 반영 대기 제안이 아닙니다", 409)
            if p["candidate"]:
                return json.loads(p["candidate"])
            doc = json.loads(current["document"])
            next(t for t in doc["tasks"] if t["id"] == p["task_id"]).update(json.loads(p["changes"]))
            doc["version"] += 1
            doc["updated_at"] = timestamp()
            exported = {"proposal_id": p["id"], "library_file_id": current["library_id"], "expected_current_version": current["version"], "base_sha256": current["digest"], "candidate_document": doc, "markdown": render_markdown(doc)}
            db.execute("UPDATE register_proposals SET exported_at=?,candidate=? WHERE id=?", (timestamp(), json.dumps(exported, ensure_ascii=False), p["id"]))
            self.event(db, "exported", p["task_id"], {"proposal_id": p["id"], "base_version": p["base_version"]})
            return exported


def render_markdown(doc):
    lines = ["# " + doc.get("title", "작업대장"), "", "JSON 원본에서 생성한 열람본입니다.", ""]
    for key, value in doc.items():
        if key != "tasks":
            lines += [f"## {key}", "", json.dumps(value, ensure_ascii=False, indent=2), ""]
    for task in doc["tasks"]:
        lines += [f"## {task['id']} · {task['task_name']}", ""]
        for key, value in task.items():
            lines += [f"- **{key}**: " + (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))]
        lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", required=True)
    sub = p.add_subparsers(dest="action", required=True)
    i = sub.add_parser("import")
    i.add_argument("--minimum-version", type=int, default=1)
    for name in ("file", "library-id", "sha256", "backup"):
        i.add_argument("--" + name, required=True)
    for name in ("version", "expected-version", "expected-count"):
        i.add_argument("--" + name, type=int, required=True)
    sub.add_parser("status")
    e = sub.add_parser("export"); e.add_argument("--proposal-id", required=True); e.add_argument("--directory", required=True)
    a = p.parse_args()
    if a.action == "import":
        import os
        os.umask(0o077)
        require(a.version >= a.minimum_version, "stale_source", "지정한 최소 Library 버전보다 오래된 원본입니다")
        source = Path(a.data).resolve(strict=True)
        backup = Path(a.backup)
        with backup.open("xb"):
            pass
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as original, sqlite3.connect(backup) as target:
            original.backup(target)
            require(target.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "backup_failed", "백업 무결성 검사 실패")
        result = Register(a.data).import_document(Path(a.file).read_bytes(), a.library_id, a.version, a.expected_version, a.sha256, a.expected_count)
    elif a.action == "export":
        result = Register(a.data).export(a.proposal_id)
        dest = Path(a.directory); dest.mkdir(parents=True, exist_ok=True)
        for name, body in [("candidate.json", json.dumps(result["candidate_document"], ensure_ascii=False, indent=2)), ("candidate.md", result["markdown"]), ("manifest.json", json.dumps({k: v for k, v in result.items() if k not in ("candidate_document", "markdown")}, ensure_ascii=False, indent=2))]:
            with (dest / name).open("x", encoding="utf-8") as f:
                f.write(body)
        result = {"exported": True, "directory": str(dest), "library_updated": False}
    else:
        result = Register(a.data).snapshot()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
