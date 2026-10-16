# 데이터·API·MCP 명세

버전 0.1 / 2026-10-16. **[제안] HAAR 논리 계약**이며 현재 제공되는 서버 API·OpenAPI·MCP 서버가 아니다. Paperclip/Buzz 실제 표면은 [공식 근거와 코드 조사](TECHNICAL_REVIEW.md), 실행 상세는 [adapter 계약](ADAPTER_CONTRACT.md)을 따른다. 미확인 매핑을 실제 지원으로 표시하지 않는다.

## 1. 기준과 공통 타입

엔터티 목록은 [PRD 9절](PRD.md#9-데이터-모델), task/run/artifact/action 상태 어휘는 PRD 8절을 기준으로 유지한다. 이 문서는 필드 제약·인덱스·외부 계약을 보충한다. 승인 decision은 보안설계, 전달·lease·복구는 adapter 계약이 권위 기준이다.

- ID는 클라이언트가 해석하지 않는 opaque string이다. 예시 `task_demo_001`은 가상 값이며 실제 UUID/전역 ID 형식은 구현 때 고정한다.
- 모든 자원·키·외부 매핑에 workspace 범위를 포함한다. 시간은 RFC3339 UTC, 표시 시간대는 IANA timezone으로 보존한다. 날짜만 있는 마감의 의미/변환은 화면설계 3.1절 및 PRD O-07 검토 후 확정하고 서버가 임의 시각을 채우지 않는다.
- 필수 문자열의 공백·최대 길이, 페이지/업로드/버퍼 크기 상한은 측정·UX 검토 후 유한 값으로 확정한다. 상한 미설정 상태를 운영 허용으로 해석하지 않는다.
- `revision`은 특정 aggregate의 낙관적 충돌 토큰이다. 모든 편집에 expected revision을 검사한다. `schema_version`과 `protocol_version`은 내용 구조 호환성이고 revision과 다르다.
- 서버가 actor·권한·workspace를 인증 컨텍스트에서 결정한다. body의 actor_id·approved_by·다른 workspace를 믿지 않는다. 비밀 값·인증 헤더·쿠키 필드는 수용하지 않는다.

## 2. 원장 매핑과 저장 제약

| 데이터/필드 | 제안 제약·인덱스 | 원천·미확인 매핑 |
| --- | --- | --- |
| TaskBinding | unique(workspace_id, task_id), unique(workspace_id, paperclip_issue_id); 프로젝트/SKU 참조는 같은 workspace | issue.id/companyId 매핑은 CR-05에서 필드 존재 확인, tenancy 결합 방식 V-01 |
| Task 상태·담당·우선순위 | 별도 확정 원장 금지; 상태/담당 읽기 투영에는 origin version·fetched_at 포함 | issue.status/assigneeAgentId/assigneeUserId/priority 재사용. P0~P3↔upstream priority 값은 V-01 검증 |
| 확장 revision | SKU/목표/마감/검수/승인 등 aggregate별 단조 증가, stale 수정 거부 | upstream statusVersion은 소유권/상태 관련 값이며 전체 편집 ETag와 동일하다고 가정하지 않음 |
| FocusSelection | 사용자·local_date 내 rank 1~3 유일, task 중복 불가; 트랜잭션에서 개수 검사 | HAAR 확장 후보, 원장 작업 상태는 변경하지 않음 |
| RunBinding | unique(workspace_id, run_id), upstream run 참조, route_id·adapter_id·node_id·host_group·lease_epoch·receipt | heartbeat_runs 존재 확인 CR-06; 원격 run mapping·재실행 hold는 V-02 |
| Receipt/Event | unique(workspace, source, source_event_id), unique(run_id,event_id), unique(run_id,sequence) | 같은 ID/sequence·다른 digest는 충돌. source 원본 ID와 중앙 event ID 분리 |
| CommandLedger | unique(workspace, actor, operation, idempotency_key), request digest·결과 영수증·수명 | upstream create 멱등성/보존정책을 그대로 action ledger 정책으로 사용하지 않음 |
| ArtifactVersion | unique(artifact_id, version_id), SKU/변형·run·원본 lineage·고정 파일 버전·digest | Drive stable version/copy 지원 V-05. URL만으로 불변 파일 승인 불가 |
| Approval/Action | action_id↔digest↔승인 decision·consumed_at·external_receipt; 단일 소비를 트랜잭션으로 보장 | HAAR 외부 실행 모델. upstream 승인과의 정책 결합 V-02/08 |
| Memory/Skill/Instruction | unique(resource_id, revision/version), provenance·scope·updated_at·approver·digest | Argo 공개 UX 참고 독자 모델. run은 적용 snapshot 참조 고정 |
| ChannelBinding | source channel/thread/message↔task/run/route, source cursor·작성자 매핑 | Buzz 서명/멤버십·인증 연결 V-03 |
| ResourceReservation | host_group·node·run·slot·측정 프로파일·reservation state | 같은 호스트 합산, 실제 종료 확인 전 불명 실행의 예약 해제 금지 |

삭제/보존은 [보안설계](SECURITY_APPROVALS.md)를 따른다. 연결된 과거 승인 artifact·action receipt·멱등성 이력을 파일 교체나 task 완료와 함께 삭제하지 않는다. 보존기간과 hard delete는 미결정이며 감사·재실행 위험을 검토한 뒤 정한다.

## 3. 공통 HTTP 계약

`/v1`은 HAAR 제안 API namespace다. upstream `/api`와 구분한다. 명령 mutation은 body의 `idempotency_key`를 요구하고 생성된 receipt를 조회할 수 있게 한다. 이벤트는 adapter 계약의 event_id/sequence로 중복 처리한다. 같은 명령 키·같은 payload는 같은 결과, 같은 키·다른 payload는 409다. 접수 응답에는 `command_id`, task 참조, 상태, 조회 경로를 제공하며 실행 시작을 뜻하지 않는다.

조회 응답은 `data`, `meta.schema_version`, `meta.fetched_at`, `meta.origin_revision`, 선택적 cursor를 제공한다. task 복합 조회는 원장 상태·로컬 검수·연결 관측의 갱신 시각을 구분한다. 목록은 cursor/limit, 필터를 사용하고 전체 대화·원본·로그를 기본 응답에 넣지 않는다.

| 상태/오류 코드 [제안] | 의미 | 클라이언트 행동 |
| --- | --- | --- |
| 400 `invalid_request` / 422 `validation_failed` | schema/필수 맥락/상품 사실 조건 오류 | 필드·해제 행동 표시, 자동 재전송 없음 |
| 401 `authentication_required` / 403 `scope_denied` | 인증·권한 부족 | 재인증/권한 확인, 비밀 입력을 채팅으로 요구하지 않음 |
| 404 `resource_unavailable` | 없음 또는 접근 불가 자원 | 다른 workspace 자원 존재 노출 금지 |
| 409 `stale_revision` / `idempotency_conflict` / `ownership_conflict` | 편집·키·소유권 충돌 | 최신값/영수증 조회, checkout 반복 금지 |
| 409 `approval_invalid` / `result_unknown` | 승인 대상·기한·실제 결과 불확실 | 재검토 또는 실제 결과 조회, 쓰기 재시도 금지 |
| 429 `capacity_exceeded` | 접수 상한/요청률 초과 | Retry-After 존중, 같은 키 유지; 이미 접수된 대기는 오류 대신 wait_reason |
| 503 `dependency_unavailable` | 원장/bridge 조회 불가 | 접수 여부 조회, 미접수 증거 없이 새 키 재실행 금지 |

오류 예시:

```json
{
  "error": {
    "code": "stale_revision",
    "message": "작업 내용이 변경되어 다시 확인해야 합니다",
    "request_id": "req_demo_001",
    "task_id": "task_demo_001",
    "current_revision": 4,
    "next_action": "최신 작업을 읽고 변경 내용을 비교한다",
    "retryable": false
  }
}
```

## 4. 웹·대화용 명령/조회 표

이 표는 API 계약 초안이다. 실제 handler·인증 미들웨어·OpenAPI 파일은 향후 구현 산출물이며 지금 만들지 않는다. 운영자/검토자/AI의 권한 차이는 보안설계 8절에서 검사한다.

| API ID / 제안 경로 | 필수 입력·선행조건 | 반환·효과 | 연결 AC |
| --- | --- | --- | --- |
| API-01 `GET /v1/today` | local_date·timezone·접근 workspace | 집중·기한·승인/막힘 집계·진행 그래프·갱신 시각 | 01~04, 14 |
| API-02 `PUT /v1/focus` | 날짜·ordered task IDs≤3·expected_revision·key | 저장 revision, 실행/상태 전이 없음 | 01~02 |
| API-03 `GET /v1/tasks` / `GET /v1/tasks/{task_id}` | filters/cursor 또는 ID | 원장 상태·담당·다음 행동·run/결과 요약, 큰 로그는 별도 조회 | 03~04, 12, 21 |
| API-04 `POST /v1/tasks` | 목표·수용조건·source event·key, SKU 등 선택 | 생성 receipt와 task mapping; 첫 지시와 별도임을 표시 | 04, 07, 13 |
| API-05 `POST /v1/task-commands` | task_id·command_type·expected_revision·idempotency_key, instruct이면 route_id·instruction·context_snapshot·allowed_effects | 중앙 command receipt; instruct/priority·마감 편집/cancel/handoff 등 명령별 allowlist 검사 | 07~11, 15, 20, 23~24 |
| API-06 `GET /v1/commands/{command_id}` | 원 요청자 또는 범위 권한 | 접수/반영 대기·task/run/결과 참조; 응답 유실 복구 | 07, 10~11 |
| API-07 `GET /v1/products/{sku_id}` | SKU·variant 선택 | 검증된 사실·출처·원본/최신생성/최신승인 버전, 권한 있는 preview 참조 | 05~06 |
| API-08 `POST /v1/artifact-versions/{version_id}/reviews` | approve/changes_requested·사유·expected_revision·observed_digest·key | 검수 decision; 게시 승인·외부 실행은 발생하지 않음 | 05~06, 12, 18 |
| API-09 `GET /v1/agents` / `GET /v1/agents/{agent_id}` | route/역할 필터 또는 ID | 지침·스킬·MCP권한·실행위치·capability/연결과 확인시각 | 17, 23 |
| API-10 `POST /v1/handoffs` | task/run·목표/완료/미완료/근거/결정/금지/다음행동·대상 route·key·revision | 인계 검토본·새 run/자식 작업 계획, 기존 실행 조회/소유권 확인 전 dispatch 금지 | 08, 10~11, 15~16 |
| API-11 `POST /v1/memory-revisions` / `POST /v1/skill-candidates` | 출처·scope·변경 근거·base revision·key | 후보 생성; 확정 기억·active skill로 자동 승격하지 않음 | 16, 22 |
| API-12 `POST /v1/skill-versions/{version_id}/activation` | 승인된 버전·범위·평가·expected_revision·key | 다음 run 적용/롤백 결정, 현재 run snapshot 보존 | 16, 22 |
| API-13 `POST /v1/actions` | 검수 버전·target·payload·일정/비용·key | digest 고정한 action 초안·승인 요청, 외부 효과 없음 | 06, 18 |
| API-14 `POST /v1/approvals/{approval_id}/decisions` | 사람이 결정·target digest·revision·key | 승인/거절/철회. 외부 실행 예약은 승인 소비 규칙과 별도 검사 | 13, 18~19 |
| API-15 `GET /v1/actions/{action_id}` | action 접근 권한 | 승인·소비·실제 영수증·unknown/복구 다음 행동 | 18~19 |

`API-05 command_type`은 `instruct`, `update_priority`, `update_deadline`, `cancel`, `handoff_request` 등의 검증된 명령만 허용한다. 자유로운 DB patch나 임의 URL/셸 실행 문자열을 중앙 업무 명령으로 해석하지 않는다. `API-10`은 인계 패킷 자원이고 `handoff_request`는 해당 인계를 실제 명령 경계로 진행시키는 요청이다. 역할에 따라 두 단계 중 허용 범위가 다르다.

접수 예시:

```json
{
  "data": {
    "command_id": "command_demo_001",
    "task_id": "task_demo_001",
    "status": "accepted",
    "wait_reason": "adapter_offline",
    "route_id": "mac_orca",
    "run_id": null,
    "status_url": "/v1/commands/command_demo_001"
  },
  "meta": {
    "schema_version": "0.1",
    "fetched_at": "2026-10-16T12:00:00Z"
  }
}
```

## 5. 내부 adapter·이벤트·승인 실행

hello/claim/started/heartbeat/events/query/reconcile/cancel/action execute의 경로·순서는 [adapter 계약 4~7절](ADAPTER_CONTRACT.md#4-개념적-메시지와-엔드포인트)을 그대로 참조한다. 추가 해석 규칙:

- hello는 route·node·host_group·protocol/capability·측정 프로파일을 검증한다. 실제 설치/이름이 미확인이면 supported로 승격하지 않는다.
- run 이벤트는 run_id·event_id·sequence·lease_epoch·observed_at·type을 가진다. 역순은 제한된 버퍼/누락 재조회로 처리하고 오래된 이벤트가 terminal 상태를 과거로 되돌리지 않는다.
- stale lease는 권위 쓰기를 거부하되 늦은 결과·외부 receipt는 별도 증거로 보존한다. 중앙의 run 조회와 adapter의 실제 프로세스/외부 결과 조회를 구분한다.
- 승인 digest는 `canonicalization_version`을 고정한 UTF-8 정규화 데이터의 SHA-256 후보다. target·account·본문·artifact version/digest·일정·금액/통화/범위를 포함하고 값의 순서/단위를 정규화한다. 정확한 canonicalization 알고리즘·필드 목록은 구현 전 contract fixture로 확정한다.
- 실행 직전 실제 payload에서 digest를 재계산하고 승인 범위·기한·철회·단일 소비·소유권을 검사한다. 미확인 상품 사실/변경된 파일은 action을 차단한다. 응답 유실은 기존 영수증 조회로 복구한다.

## 6. MCP 도구 명세 초안

아래 `haar_*`는 **새로 제안한 이름**이며 현재 사용 가능한 도구가 아니다. Paperclip의 기존 `paperclip*` 도구와 혼동하지 않는다. public MCP가 기본 비활성이라는 사실도 일반 실행 adapter 연결과 별개다.

| 제안 도구 | 입출력·권한 | 제한 |
| --- | --- | --- |
| `haar_get_task`, `haar_list_tasks` | API-03과 같은 조회, actor workspace/할당 범위 | 숨겨진 회사·비밀·원문 로그 제외 |
| `haar_get_task_context` | task와 허용된 SKU/지침/스킬/기억 snapshot·다음 행동 반환 | 요청자가 원본에 접근할 수 있어야 함 |
| `haar_instruct_task` | API-05 instruct 계약, key·revision·선택 route·허용 효과 | 인증된 지시 권한 필요, 멘션만으로 임의 추가 권한 부여 불가 |
| `haar_submit_artifact` | 실행 소유자가 결과 참조·버전·digest 제출 | 같은 task/run 소유권 검사, 승인·done 위조 불가 |
| `haar_propose_memory`, `haar_propose_skill` | API-11 후보 제안 | 자동 활성화·스스로 승인 금지 |
| `haar_request_action_approval` | API-13 승인 요청 생성 | 승인/외부 실행 권한은 부여하지 않음 |

사람의 최종 승인 도구는 AI에 노출하지 않는다. 사용자 웹 승인과 외부 action broker 실행 경계를 사용한다. generic REST passthrough/임의 SQL/셸을 통해 이 권한을 우회하지 못하게 allowlist를 적용한다. MCP 요청의 actor는 tool body가 아니라 연결 인증·run scope로 결정한다. MCP를 설치/연결하는 것만으로 GUI/GPT 대화를 자동 깨우는 계약은 없다.

## 7. 미확인 가정과 검증 과제

| ID | 미확인 가정/선택 | 검증·책임·중단 조건 |
| --- | --- | --- |
| V-01 | Paperclip extension/plugin/API와 workspace↔company·priority·revision 결합 | Task Core 담당이 고정 버전 contract 시험; 권한/단일 원장 불가면 방식 재검토 |
| V-02 | native 큐/run에 원격 adapter·unknown 재실행 hold·승인을 결합 | adapter/보안 담당이 자동 회복까지 실패 주입; hold 강제 불가면 직접 실행 출시 보류 |
| V-03 | Buzz 채널의 외부 인증·선택 route·서명/cursor·API 분리 지원 | 채널 담당이 실제 지원 표면/의존성·리소스 확인; 지원하지 않는 경로를 있다고 표기 금지 |
| V-04 | 다섯 경로의 실제 이름·설치·API/CLI/GPT 호출·세션/취소 지원 | 운영자 명칭 확인 + adapter 담당 진단/계약 시험; 미지원 capability는 비활성 |
| V-05 | Drive 접근·고정 버전/복사본·digest·preview | 파일 담당이 공식 지원·권한/변경 시험; 고정 검증 불가 시 자동 게시 보류 |
| V-06 | Mac helper API·서명·Keychain 등록과 웹 로그인 | 보안 담당이 공식 API/OS 경계 확인; Apple Passwords 자동 접근/중앙 token 저장 전제 금지 |
| V-07 | 실제 VPS 용량·idle/peak·pool/버퍼/슬롯 상한·Rust 비용 | 운영 담당이 ADR-001 측정; 미측정 MiB·무제한 동시성을 운영 설정으로 사용 금지 |
| V-08 | SNS/CS/광고 API·권한·비용·실제 결과 조회 | 연동 담당이 공식 문서/테스트 환경과 명시 승인 검증; 조회/승인 강제 불가 시 쓰기 출시 보류 |

검증은 향후 구현 단계의 과제다. 이번에는 코드의 일부 정적 경로만 확인했고 실제 API 호출·설치·connector 지원이나 성능을 시험하지 않았다.
