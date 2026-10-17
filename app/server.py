"""HAAR M0 intake board. No scheduler or external write capability."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid
from urllib.parse import urlsplit

ROOT = Path(__file__).parent
ROUTES = [
    {"id": "vps_hermes", "name": "Hermes", "location": "VPS", "initials": "H", "observation": "프로세스 확인 · 실행 adapter 미연결"},
    {"id": "vps_openclaw", "name": "OpenClaw", "location": "VPS", "initials": "O", "observation": "서비스 확인 · 실행 adapter 미연결"},
    {"id": "mac_cokacdir", "name": "COKACDIR", "location": "Mac", "initials": "C", "observation": "CLI 확인 · 실행 adapter 미연결"},
    {"id": "mac_orca", "name": "Orca", "location": "Mac", "initials": "O", "observation": "연결 계약 확인 필요"},
    {"id": "gpt", "name": "GPT", "location": "웹 / API 미정", "initials": "G", "observation": "호출 방식 확인 필요"},
]
AREAS = ["상품·상세페이지", "착용샷·영상", "SNS 콘텐츠", "광고", "Cafe24·개발", "CS", "기타"]
STAGES = ["planned", "blocked", "review", "archived"]


def now():
    return datetime.now(timezone.utc).isoformat()


class Problem(Exception):
    def __init__(self, code, message, status=422):
        self.code, self.message, self.status = code, message, status


def text_field(data, key, limit=2000, required=False):
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > limit:
        raise Problem("invalid_field", f"{key}: 최대 {limit}자의 문자열을 입력하세요")
    value = value.strip()
    if required and not value:
        raise Problem("missing_field", f"{key}: 내용을 입력하세요")
    return value


def calendar_date(value):
    try:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError()
        date.fromisoformat(value)
    except ValueError:
        raise Problem("invalid_date", "올바른 날짜를 입력하세요")
    return value


def link_url(value):
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise Problem("invalid_link", "결과 링크에는 로그인 정보가 없는 https 주소를 사용하세요")
    if any(c.isspace() for c in value):
        raise Problem("invalid_link", "주소에 공백을 넣을 수 없습니다")
    return value


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, body TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS focus (
                    local_date TEXT PRIMARY KEY, ids TEXT NOT NULL, revision INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS commands (
                    idempotency_key TEXT PRIMARY KEY, digest TEXT NOT NULL, receipt TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY, record_id TEXT, kind TEXT NOT NULL, occurred_at TEXT NOT NULL
                );
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def record(self, db, record_id):
        row = db.execute("SELECT body, revision FROM records WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise Problem("not_found", "항목을 찾을 수 없습니다", 404)
        return {**json.loads(row["body"]), "revision": row["revision"]}

    def snapshot(self, local_date):
        calendar_date(local_date)
        with self.connection() as db:
            rows = db.execute("SELECT id FROM records ORDER BY rowid DESC").fetchall()
            records = [self.record(db, row["id"]) for row in rows]
            focus = db.execute("SELECT ids, revision FROM focus WHERE local_date=?", (local_date,)).fetchone()
        return {"records": records, "focus": {"ids": json.loads(focus["ids"]) if focus else [], "revision": focus["revision"] if focus else 0, "local_date": local_date},
                "routes": [{**r, "connection": "not_connected", "can_execute": False, "last_seen": None,
                             "instructions": "미등록", "skill_version": "미등록", "mcp_permissions": "부여 안 됨"} for r in ROUTES],
                "areas": AREAS, "mode": "intake_only", "paperclip": {"connected": False, "message": "서버 설치 미확인 · 등록 전 초안 보관"},
                "buzz": {"connected": False, "message": "기존 relay 중지 · 채팅 미연결"}, "fetched_at": now()}

    def command(self, operation, payload):
        if not isinstance(payload, dict):
            raise Problem("invalid_json", "JSON 객체를 입력하세요", 400)
        key = text_field(payload, "idempotency_key", 128, True)
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", key):
            raise Problem("invalid_key", "요청 식별자가 올바르지 않습니다")
        digest = hashlib.sha256(json.dumps([operation, payload], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT digest, receipt FROM commands WHERE idempotency_key=?", (key,)).fetchone()
            if previous:
                if previous["digest"] != digest:
                    raise Problem("idempotency_conflict", "같은 요청 식별자의 내용이 다릅니다. 최신 내용을 확인하세요", 409)
                return json.loads(previous["receipt"])
            if operation == "create":
                result = self.create(db, payload)
            elif operation == "focus":
                result = self.set_focus(db, payload)
            elif operation == "demo":
                result = self.demo(db)
            elif operation in ("edit", "artifact", "review", "handoff"):
                result = self.change(db, operation, payload)
            else:
                raise Problem("unknown_command", "지원하지 않는 요청입니다", 404)
            receipt = {"command_id": str(uuid.uuid4()), "operation": operation, "saved_at": now(), "data": result,
                       "dispatched": False, "run_id": None, "action_id": None}
            db.execute("INSERT INTO commands VALUES (?, ?, ?)", (key, digest, json.dumps(receipt, ensure_ascii=False)))
            db.execute("INSERT INTO events VALUES (?, ?, ?, ?)", (str(uuid.uuid4()), result.get("id"), operation, receipt["saved_at"]))
            return receipt

    def create(self, db, data, sample=False):
        if db.execute("SELECT count(*) FROM records").fetchone()[0] >= 1000:
            raise Problem("capacity", "체험판 보관 상한 1,000개입니다. 운영 원장 연결 후 확장하세요", 429)
        priority = data.get("priority", "P1")
        route_id = data.get("route_id", "gpt")
        area = data.get("area", AREAS[0])
        if priority not in ("P0", "P1", "P2", "P3") or route_id not in [r["id"] for r in ROUTES] or area not in AREAS:
            raise Problem("invalid_selection", "우선순위·영역·AI 선택을 확인하세요")
        deadline = text_field(data, "deadline", 10)
        if deadline:
            calendar_date(deadline)
        record = {"id": str(uuid.uuid4()), "task_id": None, "paperclip_issue_id": None,
                  "title": text_field(data, "title", 160, True), "brief": text_field(data, "brief", 4000),
                  "next_action": text_field(data, "next_action", 1000), "sku": text_field(data, "sku", 100),
                  "area": area, "priority": priority, "deadline": deadline, "route_id": route_id,
                  "intake_stage": "planned", "wait_reason": "paperclip_not_connected", "run_id": None,
                  "sample": sample, "artifacts": [], "handoffs": [], "created_at": now(), "updated_at": now()}
        db.execute("INSERT INTO records (id, body) VALUES (?, ?)", (record["id"], json.dumps(record, ensure_ascii=False)))
        return {**record, "revision": 1}

    def change(self, db, operation, data):
        record_id = text_field(data, "id", 100, True)
        record = self.record(db, record_id)
        revision = data.get("expected_revision")
        if type(revision) is not int or revision != record["revision"]:
            raise Problem("stale_revision", "다른 창에서 변경되었습니다. 입력 내용을 복사한 뒤 항목을 닫고 다시 열어 최신본에서 수정하세요", 409)
        if operation == "edit":
            allowed = {"priority", "deadline", "next_action", "intake_stage", "title", "brief", "route_id", "sku", "area", "id", "expected_revision", "idempotency_key"}
            if set(data) - allowed:
                raise Problem("invalid_field", "수정할 수 없는 필드입니다")
            for field, limit in [("title", 160), ("brief", 4000), ("sku", 100), ("next_action", 1000)]:
                if field in data:
                    record[field] = text_field(data, field, limit, field == "title")
            for field, choices in [("priority", ("P0", "P1", "P2", "P3")), ("route_id", [r["id"] for r in ROUTES]), ("area", AREAS), ("intake_stage", STAGES)]:
                if field in data:
                    if data[field] not in choices:
                        raise Problem("invalid_selection", "올바른 선택값을 사용하세요")
                    record[field] = data[field]
            if "deadline" in data:
                record["deadline"] = calendar_date(data["deadline"]) if data["deadline"] else ""
            if record["intake_stage"] == "review" and not record["artifacts"]:
                raise Problem("no_artifact", "결과 링크를 등록하면 검토 대기로 이동합니다")
        elif operation == "artifact":
            artifact = {"version_id": str(uuid.uuid4()), "label": text_field(data, "label", 160, True),
                        "url": link_url(text_field(data, "url", 2048, True)), "source": "manual_link", "review": "pending",
                        "review_note": "", "added_at": now(), "reviewed_at": None,
                        "version_note": text_field(data, "version_note", 500, True)}
            if len(record["artifacts"]) >= 50:
                raise Problem("limit", "항목당 결과 버전은 50개까지 보관합니다")
            record["artifacts"].append(artifact)
            record["intake_stage"] = "review"
        elif operation == "review":
            decision = data.get("decision")
            if decision not in ("approved", "changes_requested"):
                raise Problem("invalid_decision", "검토 결정을 선택하세요")
            if not record["artifacts"] or record["artifacts"][-1]["version_id"] != data.get("version_id"):
                raise Problem("stale_artifact", "최신 결과 버전을 다시 확인하세요", 409)
            artifact = record["artifacts"][-1]
            if artifact["review"] != "pending":
                raise Problem("reviewed", "이미 검토한 버전입니다. 변경본을 새 버전으로 등록하세요", 409)
            artifact.update(review=decision, review_note=text_field(data, "note", 1000, True), reviewed_at=now())
            record["intake_stage"] = "planned" if decision == "approved" else "blocked"
        elif operation == "handoff":
            if len(record["handoffs"]) >= 50:
                raise Problem("limit", "항목당 인계 기록은 50개까지 보관합니다")
            record["handoffs"].append({"id": str(uuid.uuid4()), "note": text_field(data, "note", 3000, True),
                                       "url": link_url(text_field(data, "url", 2048)), "created_at": now(), "delivery": "manual"})
        record["updated_at"] = now()
        record.pop("revision")
        db.execute("UPDATE records SET body=?, revision=revision+1 WHERE id=?", (json.dumps(record, ensure_ascii=False), record_id))
        return self.record(db, record_id)

    def set_focus(self, db, data):
        local_date = calendar_date(data.get("local_date"))
        ids = data.get("ids")
        if not isinstance(ids, list) or len(ids) > 3 or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise Problem("focus_limit", "오늘 집중은 서로 다른 항목 최대 3개입니다")
        for record_id in ids:
            if self.record(db, record_id)["intake_stage"] == "archived":
                raise Problem("archived", "보관한 항목은 집중 목록에 추가할 수 없습니다")
        row = db.execute("SELECT revision FROM focus WHERE local_date=?", (local_date,)).fetchone()
        revision = row["revision"] if row else 0
        if type(data.get("expected_revision")) is not int or data["expected_revision"] != revision:
            raise Problem("stale_revision", "집중 목록이 변경되었습니다. 새로고침 후 다시 선택하세요", 409)
        db.execute("INSERT INTO focus VALUES (?, ?, ?) ON CONFLICT(local_date) DO UPDATE SET ids=excluded.ids, revision=excluded.revision", (local_date, json.dumps(ids), revision + 1))
        return {"ids": ids, "local_date": local_date, "revision": revision + 1}

    def demo(self, db):
        if db.execute("SELECT 1 FROM records WHERE json_extract(body, '$.sample')=1").fetchone():
            raise Problem("demo_exists", "예시 항목이 이미 있습니다", 409)
        examples = [
            {"title": "실버 이어링 상세페이지 구성", "brief": "가상 SKU의 원본 사진을 확인하고 핵심 구성을 정리해요. 실제 제품 사양은 확인 후 입력하세요.", "sku": "DEMO-E01", "area": AREAS[0], "route_id": "mac_orca", "priority": "P0", "next_action": "원본 사진과 확인된 소재 정보를 연결하기"},
            {"title": "주말 신상품 인스타그램 기획", "brief": "실제 게시 없이 이미지 순서와 캡션 초안을 검토해요.", "sku": "DEMO-E01", "area": AREAS[2], "route_id": "gpt", "priority": "P1", "next_action": "레퍼런스와 브랜드 말투 정리하기"},
            {"title": "착용 영상, 15초 숏츠 콘티", "brief": "가상 샘플의 촬영 순서와 필요한 컷을 정리해요.", "sku": "DEMO-V02", "area": AREAS[1], "route_id": "mac_cokacdir", "priority": "P2", "next_action": "촬영 원본 링크 확인하기"}]
        records = [self.create(db, e, sample=True) for e in examples]
        return {"ids": [r["id"] for r in records], "sample": True}


class Handler(BaseHTTPRequestHandler):
    server_version = "HAAR-M0"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass  # No task text, URLs, headers or credentials in access logs.

    def send(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def boundary(self, mutation=False):
        host = self.headers.get("Host", "")
        if not re.fullmatch(r"(localhost|127\.0\.0\.1):\d{1,5}", host):
            raise Problem("host_denied", "SSH 터널의 localhost 주소로 접속하세요", 403)
        if mutation and self.headers.get("Origin") != "http://" + host:
            raise Problem("origin_denied", "같은 웹 화면에서 저장하세요", 403)
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise Problem("origin_denied", "외부 사이트에서의 요청은 허용하지 않습니다", 403)

    def do_GET(self):
        try:
            self.boundary()
            path = urlsplit(self.path)
            if path.path == "/api/health":
                return self.send(200, {"status": "ok", "mode": "intake_only", "dispatch_enabled": False})
            if path.path == "/api/board":
                from urllib.parse import parse_qs
                local_date = parse_qs(path.query).get("date", [date.today().isoformat()])[0]
                return self.send(200, self.server.store.snapshot(local_date))
            files = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8"), "/favicon.svg": ("favicon.svg", "image/svg+xml")}
            if path.path not in files:
                raise Problem("not_found", "페이지를 찾을 수 없습니다", 404)
            filename, content_type = files[path.path]
            self.send(200, (ROOT / "static" / filename).read_bytes(), content_type)
        except Problem as e:
            self.send(e.status, {"error": {"code": e.code, "message": e.message}})
        except Exception:
            self.send(500, {"error": {"code": "server_error", "message": "조회에 실패했습니다. 잠시 후 새로고침하세요"}})

    def do_POST(self):
        try:
            self.boundary(mutation=True)
            if self.headers.get("Content-Type") != "application/json":
                raise Problem("content_type", "JSON 요청만 허용합니다", 415)
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 16384:
                raise Problem("body_limit", "요청은 16KB 이내여야 합니다", 413)
            data = json.loads(self.rfile.read(length))
            operation = {"/api/records": "create", "/api/focus": "focus", "/api/demo": "demo", "/api/records/edit": "edit", "/api/artifacts": "artifact", "/api/reviews": "review", "/api/handoffs": "handoff"}.get(self.path)
            if not operation:
                raise Problem("not_found", "요청 경로를 확인하세요", 404)
            return self.send(200, self.server.store.command(operation, data))
        except Problem as e:
            self.send(e.status, {"error": {"code": e.code, "message": e.message}})
        except (ValueError, json.JSONDecodeError):
            self.send(400, {"error": {"code": "invalid_json", "message": "올바른 JSON 요청을 사용하세요"}})
        except Exception:
            self.send(500, {"error": {"code": "save_failed", "message": "저장 결과를 확인할 수 없습니다. 같은 요청으로 다시 확인하세요"}})


def build_server(path, port=3310):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.store = Store(path)
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=3310)
    parser.add_argument("--data", default=os.environ.get("HAAR_DATA", ".data/workspace.sqlite3"))
    args = parser.parse_args()
    os.umask(0o077)
    server = build_server(args.data, args.port)
    print(f"HAAR M0 on http://127.0.0.1:{args.port} — intake only, dispatch disabled", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
