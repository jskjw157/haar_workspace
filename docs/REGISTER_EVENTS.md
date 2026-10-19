# 부모 변경 이벤트와 자동 갱신 계약

## 원본과 연결 범위

초기 자료는 기존 Library 확인본이다. 첫 부모 이벤트 수신 이후 **VPS 작업대장이 단일 운영 상태 원본**이며 `source.version`은 대장 revision이다. `source.library_version`은 초기 Library 보관 버전으로 고정된다. 둘을 같은 버전으로 표시하지 않는다. 최초 JSON의 record_policy 등 확장 필드는 당시 출처 기록으로 보존한다. 이벤트 모드에서는 과거 import와 Library 후보 export를 409로 차단해 두 원본이 경쟁하지 않게 한다.

현재 Library 도구에는 파일 읽기/교체 기능만 노출돼 있고 VPS가 구독할 변경 이벤트나 상시 수집 인증 계약은 없다. 따라서 Library 자동 수집을 구현했다고 주장하지 않는다. 부모가 실제 결과/상태를 확인한 때 변경을 발행한다. 다른 AI 대화·실행기를 자동 깨우거나 직접 관찰하지 않는다. 상태 완료는 각 행의 기존 완료 기준에 한정되며 게시·광고·CS 실행 권한을 부여하지 않는다.

전달은 기존 SSH localhost 경로만 사용한다. 새 토큰/OAuth/키/사용자/방화벽/상시 권한을 만들지 않는다. `POST /api/register/events`는 기존 API와 같은 Host/Origin/16KiB/JSON 경계를 따른다. 신뢰 경계는 기존 SSH 터널에 접근 가능한 운영자다. 인터넷에 공개할 인증 API가 아니다.

## 부모 실행 프로토콜

Mac의 체크아웃·산출물·실행 대기열·임시는 마운트된 X9 Pro 아래에 둔다. 기본 경로:

```
/Volumes/X9 Pro/orca/haar-workspace-register-events-20261019/
  repo/       # 이 브랜치의 실행 코드
  runtime/    # 비공개 queue.sqlite3, 변경 JSON, tmp/
```

원본을 확인하는 부모는 아래 순서를 실제 상태 변경마다 수행한다. Library 파일만 바꾸거나 이 문서를 읽는 것으로 이벤트가 발생하지 않는다.

1. 기존 터널 `http://127.0.0.1:3311`을 사용한다. `GET /api/register`로 현 상태·ID·기준·우선순위·검증 시각을 확인한다.
2. 확인한 변경만 비공개 JSON에 적는다. `source_event_id`는 논리적 변경마다 새 고유 ID이고, 같은 변경을 재시도할 때는 유지한다. 문자열 중 비밀번호·토큰은 포함하지 않는다.
3. 실행 중인 worker의 outbox에 enqueue한다. producer는 임포트나 운영 DB 직접 수정 없이 이벤트만 기록한다.
4. worker가 자동 전송하고 성공 receipt를 보관한다. 대시보드의 5초 revision 감지가 새 상태를 읽는다. 입력 중인 폼은 보존하고 새 버전 대기를 안내한다.

예시 JSON은 **가상 작업**이다. 실제 ID/상태/검증 시각과 근거로 바꿔 별도 파일에 저장한다.

```json
{
  "source_event_id": "parent-observation-unique-0001",
  "task_id": "TASK-001",
  "changes": {
    "status": "검토대기",
    "status_detail": "확인한 산출물을 사용자 검토로 전달함",
    "next_action": "산출물 검토",
    "blocker": "",
    "last_verified_at": "2026-01-01T00:00:00Z"
  },
  "verification_note": "실제로 확인한 결과와 근거 참조"
}
```

```sh
# 각 명령은 위 repo 디렉터리에서 실행. --file은 실제 외장 JSON 경로.
python3 -m app.publisher --queue '/Volumes/X9 Pro/orca/haar-workspace-register-events-20261019/runtime/queue.sqlite3' enqueue --file '/Volumes/X9 Pro/orca/haar-workspace-register-events-20261019/runtime/change.json'
python3 -m app.publisher --queue '/Volumes/X9 Pro/orca/haar-workspace-register-events-20261019/runtime/queue.sqlite3' status
# worker 하나만 실행. 시작 후 enqueue가 추가되면 별도 flush 없이 처리.
python3 -m app.publisher --queue '/Volumes/X9 Pro/orca/haar-workspace-register-events-20261019/runtime/queue.sqlite3' watch
```

worker는 기존 localhost API를 사용한다. 1초 간격으로 대기열을 확인하고, 실패 시 2/4/8/16/30초 지수 대기 후 같은 payload를 재전송한다. 동일 queue의 worker는 파일 잠금으로 하나만 실행된다. JSON/SQLite는 0600이며 코드·Git과 별도다. Mac CLI는 X9 Pro가 마운트되지 않았거나 내장 경로를 지정하면 실패하며 fallback하지 않는다. worker는 이번 실행의 프로세스이며 부팅/로그인 자동 실행 설정은 만들지 않는다. 종료·재부팅 후에는 위 watch 명령을 다시 실행해야 한다. 대기열은 보존된다.

## HTTP 계약과 충돌

`enqueue`는 최신 상태 조회에 성공하면 캐시를 갱신한다. 오프라인에서는 마지막 확인본 캐시를 사용한다. 최초 캐시가 없으면 연결을 먼저 요구한다. 전송 payload에는 다음 필드를 추가한다.

- `publisher_id=haar-parent`
- `expected_revision`: 확인한 전역 revision
- `base_task_sha256`: 기준 작업 전체 객체의 정렬 JSON SHA-256
- `idempotency_key`: source_event_id와 동일한 안정 키

정렬 JSON은 `json.dumps(task,sort_keys=True,ensure_ascii=False,separators=(',',':'))` UTF-8이다. 직접 API를 호출하는 부모도 같은 계약을 사용한다. `POST`의 Origin은 실제 localhost origin과 정확히 같아야 한다.

서버는 BEGIN IMMEDIATE에서 전역 revision·작업 해시·검증 시각·필드 허용 목록을 검사하고, 한 번에 새 스냅샷·수신 영수증·감사 이력을 저장한다. HTTP 성공 응답은 `source_event_id/revision/task_id/sha256/duplicate/dispatched=false/library_updated=false`를 포함한다. 같은 ID/키/내용 재전송은 이전 revision 영수증을 돌려준다. 같은 ID의 다른 내용은 409다. 완료 기준·사용자 우선순위·승인 범위·지시·담당·다른 행·기타 확장 필드는 수정할 수 없다. 근거와 timezone 포함 확인 시각은 필수며 미래/과거 확인으로 덮어쓰지 않는다.

충돌 또는 잘못된 요청(4xx, 408/429 제외)은 `conflict`로 보관하고 뒤 이벤트 전송도 보류한다. 자동 재기준화/덮어쓰기를 하지 않는다. 부모가 최신 대장을 검토한 뒤 충돌 이벤트를 사유와 함께 취소하고 새 ID로 재작성한다. 여러 오프라인 변경이 같은 과거 revision에서 작성됐다면 같은 절차가 필요하다. outbox 취소는 실제 작업을 취소하지 않는다.

```sh
python3 -m app.publisher --queue '/Volumes/X9 Pro/orca/haar-workspace-register-events-20261019/runtime/queue.sqlite3' cancel --event-id '기존-이벤트-ID' --reason '최신 상태와 대조해 새 이벤트로 재작성'
```

기존 화면 제안은 운영 원본을 즉시 바꾸지 않는다. 부모의 새 관측이 같은 행에 도착하면 미반영 제안을 conflict로 남겨 다시 검토하게 한다. 이벤트 모드의 Library 후보 다운로드는 차단된다.

## 오프라인·관측과 복구

worker는 30초마다 접촉·전송 대기/충돌 건수를 heartbeat로 보낸다. 마지막 접촉 90초 초과 시 화면에 게시자 연결 미확인을 표시한다. heartbeat/화면 조회가 각 작업의 검증 시각을 갱신하지 않는다. 작업이 진행 중이라는 관측은 해당 이벤트의 근거에만 의존한다.

`GET /api/register/revision`은 revision/cursor/연결 메타데이터만 돌려준다. 화면은 5초마다 조회하고 cursor가 바뀌었을 때만 전체 대장을 다시 읽는다. 새로고침 실패 시 기존 렌더를 유지하고 연결 끊김을 표시한다. 입력 중 갱신은 보류되고 저장의 CAS 검사로 오래된 편집을 차단한다.

배포 전 일관 DB 백업을 만든다. 추가 스키마는 register_stream/register_deliveries뿐이며 기존 intake 데이터는 변경하지 않는다. 실패 시 기존 확인본·queue·영수증·백업을 보존한다. 코드 복구 시 DB를 과거 백업으로 자동 덮어쓰지 않는다. Mac helper가 중단돼도 이미 확인된 VPS 원본은 유지된다.

운영 반영과 실제 자동 전달 검증은 [운영 검증 기록](REGISTER_EVENTS_VERIFICATION.md)을 참고한다.
