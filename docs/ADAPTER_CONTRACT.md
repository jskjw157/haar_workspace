# 실행 adapter 계약 초안

버전 0.1 / 2026-10-16. 이 문서는 **[제안] HAAR 내부 계약**이며 구현된 API 또는 Paperclip/Buzz의 실제 API 명세가 아니다. 사용자 확정 요구는 중앙 지시, 연결 단절 시 대기, 단일 상태 기준, 중복 방지, 실제 완료 확인 전 재실행 금지다. 상위 문서: [PRD](PRD.md).

## 1. 책임과 권위 경계

| 구성 | 책임 | 소유하지 않는 것 |
| --- | --- | --- |
| 중앙 Task Core | 작업 원장 명령·권한·우선순위·상태 전이·최종 조회 | 기기 프로세스가 실제 끝났다는 추측 |
| 실행 gateway/큐 | 내구성 접수·전달·claim·heartbeat·복구·이벤트 중복 제거 | 별도의 독립 작업 상태 |
| Mac/VPS adapter | capability 신고·환경 점검·실행·기기 내 journal·결과 조회·증거 보고 | 사용자 승인·브랜드 사실 확정 |
| 실행 런타임 | 지정 범위에서 생성·도구 사용, 결과 반환 | 임의 추가 권한·외부 쓰기 우회 |
| 채널 bridge | 메시지 출처·작성자 검증, task 연결, 명시적 지시 변환 | 대화 표현으로 상태·승인 자동 확정 |

Task Core는 Paperclip의 issue/run·checkout을 권위 경로로 사용한다. HAAR lease는 원장 소유권과 원자적으로 결합하거나 실패 시 실행 전 정리되는 예약으로 구현해야 한다. 서로 독립된 두 lock을 성공으로 간주해 실행하는 설계는 금지한다. 구현 수단(원장 확장 vs 검증된 gateway 매핑)은 M0 결정 사항이다.

## 2. 식별자와 중복 처리

| 필드 | 생성·수명 | 필수 규칙 |
| --- | --- | --- |
| task_id | 중앙이 생성, 업무 수명 동안 고정 | 원장 issue_id와 1:1 매핑, 여러 run을 연결 |
| run_id | 허용된 새 실행 시도마다 중앙 생성 | 단순 전달 재시도는 같은 run_id, 실제 재실행만 새 run_id |
| action_id | 하나의 의미 있는 외부 행동에 중앙 생성 | run이 바뀌어도 같은 게시/발송 재확인은 동일 action_id |
| source_event_id | 출처 원본 메시지/이벤트 ID | `(workspace_id, source, source_event_id)` 유일; 다른 출처 ID 충돌 방지 |
| idempotency_key | 명령 발신자가 생성, 서버가 저장 | `(workspace_id, actor_id, operation, key)` 유일; 같은 키·다른 payload는 409 |
| event_id | 보고 이벤트마다 생성 | 전달 재시도에는 같은 ID, 수신 중복은 이전 ACK 재전달 |
| lease_epoch | 중앙이 소유권 세대마다 증가 | 오래된 세대의 상태 변경·부수효과 요청 거부 |
| revision | 작업·정책 변경 시 증가 | stale UI 수정은 409, 읽기 후 명시적으로 병합 |

idempotency는 전달 중복 제거와 의미 중복 방지를 함께 다룬다. 새 키를 만들어 동일한 게시물을 다시 실행하는 경우까지 전달 중복 제거로 해결되지 않는다. 동일 action_id·대상·승인 digest의 외부 효과는 한 번만 허용하고, 의도적인 재게시에는 새 action과 새 승인이 필요하다.

이벤트는 최소 한 번 전달(at-least-once)을 전제로 한다. 외부 서비스가 멱등성을 제공하지 않으면 ‘exactly once 보장’이라고 표현하지 않는다. 상태 조회·영수증 확인·불확실 시 중단으로 중복 위험을 제어한다. 작업/승인/행동 이력이 남는 동안 관련 중복 방지 기록을 함께 보존하며 조기 TTL 만료로 재실행을 허용하지 않는다.

## 3. 연결과 capability 협상

Mac은 기본적으로 중앙에 outbound HTTPS로 등록·요청한다. 전달 방식은 long polling을 초기 후보로 두고 WS는 후속 후보로 둔다. 통신 수단이 상태 원장을 바꾸지 않는다. VPS에서 Mac에 임의 shell을 직접 여는 구조를 기본값으로 삼지 않는다.

등록에는 `adapter_id`, 실행 위치, adapter/protocol 버전, 사용 가능한 런타임과 버전, 허용 작업 루트, 지원 capability, 마지막 환경 점검을 포함한다. 비밀 값은 포함하지 않는다.

| capability | 의미 | 미지원 시 UX |
| --- | --- | --- |
| execute | 새 실행을 시작하고 started 영수증 보고 | 기록·수동 인계만 제공 |
| query_run | 기기 journal·런타임에서 실제 실행 상태 조회 | 단절 후 자동 재실행 금지, 사용자 확인 필요 |
| resume_session | 같은 작업·같은 범위의 세션 이어가기 | 승인된 인계 패킷으로 새 세션; 재실행 안전성 별도 확인 |
| cancel | 실제 실행 중단 요청·확인 | ‘중단 요청됨’만 표시, 중단 완료로 추측 금지 |
| artifacts | 결과 참조·digest·버전 반환 | 링크 수동 등록 및 검수 |
| enforce_action_gate | 외부 쓰기 경로를 코드/OS 경계로 강제 | 게시·CS 발송·광고 변경 실행 금지 |
| query_external_action | action별 외부 영수증 조회 | 불명 결과의 자동 재시도 금지 |

환경 점검은 명령 설치, 버전, 허용 작업 루트, 필요한 연결의 사용 가능 여부만 검사한다. 로그인 원문·토큰을 읽어 보고하지 않는다. GUI 앱의 자동 깨우기·세션 재개는 별도 지원이 확인될 때만 capability를 켠다.

## 4. 개념적 메시지와 엔드포인트

아래 경로는 구현 전 검토할 HAAR endpoint 이름 예시다. 실제 upstream API로 호출해서는 안 된다. 인증·인가·workspace 검증·schema validation을 모든 요청에 적용한다.

| 예시 경로 | 요청/응답 계약 |
| --- | --- |
| `POST /v1/task-commands` | revision·명령·idempotency_key 검증 후 중앙 접수 영수증; 실행 시작을 뜻하지 않음 |
| `POST /v1/adapters/hello` | 프로토콜·capability 협상, 허용 범위 반환 |
| `POST /v1/runs/claim` | 준비된 task를 원자 checkout, run_id·lease_epoch·유효기한 반환 |
| `POST /v1/runs/{run_id}/started` | 기기 journal·런타임 접수 증거 후 실행 시작 보고 |
| `POST /v1/runs/{run_id}/heartbeat` | 현재 세대·기계 상태·마지막 이벤트 커서, 실행 중이라는 증거 범위 명시 |
| `POST /v1/runs/{run_id}/events` | 이벤트 ID·sequence·결과 참조, 내구성 기록 후 ACK |
| `GET /v1/runs/{run_id}` | 중앙 상태와 마지막 기기 관측을 구분해 반환 |
| `POST /v1/runs/{run_id}/reconcile` | 실제 조회 요청과 관측 결과·증거; 새 실행 아님 |
| `POST /v1/runs/{run_id}/cancel` | 중단 의도 기록; 취소 확인 이벤트와 분리 |
| `POST /v1/actions/{action_id}/execute` | 승인 digest·권한·기한·단일 소비·실행 소유권 검증 |

지시 예시(가상 값):

```json
{
  "protocol_version": "0.1",
  "workspace_id": "ws_demo",
  "task_id": "task_demo_001",
  "source": "web",
  "source_event_id": "web_demo_001",
  "idempotency_key": "instruction_demo_001",
  "expected_revision": 3,
  "instruction": "승인된 원본으로 착용샷 초안을 생성한다",
  "adapter_id": "adapter_demo_mac",
  "context_snapshot": {
    "sku_id": "SKU-DEMO-001",
    "instruction_version": "iv_3",
    "skill_versions": ["skill_wearing_v2"],
    "memory_revisions": ["brand_rules_r4", "sku_facts_r2"],
    "artifact_versions": ["original_v1"]
  },
  "allowed_effects": ["create_draft_artifact"],
  "deadline_at": null
}
```

필수 맥락이 권한 오류·미확인 상품 사실·삭제된 파일로 누락되면 실행 전 차단한다. 원본 외부 링크는 실행 시 권한과 승인 버전을 재확인한다. 드라이브 bearer 링크나 인증 문자열은 모델 입력·일반 로그로 넣지 않는다.

결과 이벤트 예시:

```json
{
  "event_id": "evt_demo_009",
  "task_id": "task_demo_001",
  "run_id": "run_demo_001",
  "adapter_id": "adapter_demo_mac",
  "lease_epoch": 2,
  "sequence": 9,
  "type": "run.result_submitted",
  "observed_at": "2026-10-16T12:00:00Z",
  "status": "succeeded",
  "artifact_version_ids": ["wearing_output_v1"],
  "next_action": "운영자가 제품 형태와 색상을 검수한다",
  "usage": {"cost_status": "unavailable"}
}
```

결과는 검수 요청을 만들 수 있지만 사용자 승인 이벤트를 위조할 수 없다. `succeeded`는 실행 결과이며 task `done` 명령이 아니다. schema 밖 필드·명령·출력의 코드는 실행하지 않는다.

## 5. 실행 순서와 소유권

1. 웹/채널이 인증된 명령을 등록한다. 서버는 source_event_id와 idempotency_key를 확인하고 task 변경과 outbox 이벤트를 함께 내구성 기록한다.
2. 큐는 사용자 우선순위·마감·선행 의존성·권한·기기 가용성을 확인한다. offline 기기에는 새 run을 실행 중으로 표시하지 않는다.
3. adapter가 claim하면 단일 assignee와 원자 checkout을 확인하고 run 소유권·lease_epoch를 부여한다. 경쟁자는 409를 받고 중단한다. 같은 checkout을 루프로 재시도하지 않는다.
4. adapter는 기기 journal에 run_id·실행 요청 digest·lease 세대·아직 미시작임을 먼저 기록한다. 이미 받은 run이면 새 프로세스를 시작하지 않고 journal 결과를 반환한다.
5. 실행 직전 최신 정책·승인·맥락 버전·기기 범위를 재검증한다. revoke·취소·stale lease는 시작을 차단한다.
6. 프로세스 접수/시작을 journal에 기록하고 started 이벤트를 보낸다. ACK 유실 시 같은 이벤트를 재전송한다. heartbeat는 run 상태와 마지막 확인 근거를 보고한다.
7. 결과·산출물 버전·사용량·결정·다음 행동을 journal과 중앙에 기록한다. 중앙은 소유권·이벤트 순서를 확인하고 `in_review`로 전환한다.
8. 필수 검수 승인 후 task를 완료한다. 외부 행동이 필요하면 별도 action/approval을 만든다.

원장의 checkout은 task를 `in_progress`로 만들 수 있다. run이 `claimed`이면 UI는 ‘시작 준비’로 표시하고, started 영수증 이후 `running`을 ‘실행 중’으로 표시한다. claim·접수·실제 시작을 하나의 성공 신호로 합치지 않는다.

DB 변경과 이벤트 발행은 transactional outbox 또는 동등한 내구성 장치로 결합한다. 외부 통신과 DB 쓰기 전체를 하나의 원자 트랜잭션으로 가정하지 않는다. 중앙 재시작 시 ACK되지 않은 이벤트는 같은 ID로 재전달한다.

단일 task에서 동시에 살아 있는 쓰기 실행 소유권은 하나다. 병렬 이미지 시안처럼 독립 결과가 필요하면 자식 task를 나누고 각각 소유권을 부여한다. 동일 파일·SKU 확정 사실을 병렬 수정할 때는 revision과 artifact version 충돌을 별도로 검사한다.

## 6. heartbeat·단절·재연결

**[제안 시작값]** heartbeat 30초, 90초 미수신 degraded, 180초 미수신 offline. 이 기준은 네트워크 판정용이며 완료/실패 판정용이 아니다. 실제 값은 M0 환경 검증 후 조정한다.

- 미시작 단절: task `todo`, `wait_reason=adapter_offline`, 사용자에게 연결 대기와 마지막 수신시간 표시.
- 실행 중 단절: run `reconciling`, task `blocked`와 복구 책임자·조회 행동, 외부 action은 필요하면 `unknown`. 새 소유권으로 실행을 넘기지 않는다.
- 기기 재연결: adapter journal과 중앙 ACK 커서를 교환하고 run별 실제 상태를 조회한다. 완료 결과를 우선 재전송하고 실행 중이면 같은 실행에 다시 붙는다.
- “세션을 못 찾음”은 미실행 증거가 아니다. 프로세스·기기 journal·외부 action receipt까지 확인하고, 안전한 미시작이 증명되거나 운영자가 증거 기반으로 복구 결정한 경우에만 새 run을 만든다.
- stale 세대 결과는 권위 상태를 덮어쓰지 않는다. 늦은 결과를 감사·복구 증거로 보존하고 필요한 경우 운영자가 유효한 산출물을 채택한다.
- 기기 분실·영구 조회 불가: `unknown`과 담당자·다음 행동을 남긴다. 자동 재실행하지 않는다. 새 action으로 재시도하려면 중복 위험·완료 조회 근거를 검토하고 새 승인을 받는다.

lease 만료는 이전 소유자의 새 부수효과를 차단하는 fencing에 사용한다. 이미 실행된 원격 요청이나 기기 프로세스를 자동으로 되돌리지 않는다. 과거 run의 실제 결과를 확인한 뒤만 안전한 소유권 이전을 허용한다.

## 7. 실패와 복구

| 상황 | 상태·사용자 표시 | 복구·재시도 조건 |
| --- | --- | --- |
| 접수 응답 유실 | ‘접수 확인 중’, 동일 키 조회 | 같은 키로 재전송, 새 task/run 생성 금지 |
| claim 경쟁·409 | 다른 소유자와 최신 상태 표시 | 충돌 실행은 중단, 원장 조회 후 새 사용자 의도만 별도 명령 |
| 명령 미설치·로그인 필요 | `blocked`, 기기·해결 담당 표시 | 로컬 설치/로그인 후 환경 점검; 비밀 값 전송 금지 |
| 중앙 재시작 | outbox·큐·영수증 복구 | 같은 event/run ID 재전달, journal 확인 |
| adapter 실행 전 종료 | journal 상태 ‘미시작’ 여부 조회 | 실제 미시작 확인 후 동일 전달 재개 또는 새 run 기록 |
| 실행 중 기기/망 단절 | ‘실제 결과 확인 중’ | query_run과 외부 receipt 조회 먼저, 무조건 재실행 금지 |
| 런타임 timeout | `timed_out`은 관측된 실행 결과, 효과는 별도 불명 가능 | 프로세스 종료와 외부 결과 확인 후 안전한 단계만 재시도 |
| 결과 ACK 유실 | journal 결과 보존 | 같은 event_id·artifact version 재전송, 재생성 금지 |
| Drive 접근 불가·파일 변경 | 검수 불가·권한/버전 문제 | 접근 복구·고정 버전 확보·digest 확인 후 재검수 |
| 취소와 완료 경합 | `cancel_requested`, 기존 결과 증거 보존 | 중단/완료 실제 관측을 직렬화; 이미 발생한 게시를 취소로 숨기지 않음 |
| 외부 게시/발송 응답 유실 | action `reconciling` 후 필요 시 `unknown` | 계정·외부 ID·중복 키로 실제 조회, 영수증 확인 전 재호출 금지 |
| 승인 만료·대상 변경 | `expired` 또는 새 승인 필요 | 같은 행동을 최신 버전으로 검토·승인 |
| 영구 조회 불가 | `unknown`·운영자 확인 필요 | 수동 확인 증거와 사유 기록, 재실행 판단·승인 분리 |

일시적인 읽기 요청·미전달 이벤트에는 지수 backoff+jitter와 제한 횟수를 적용할 수 있다. **[제안]** 5초·15초·60초 뒤 총 3회 이후 복구함으로 보낸다. 이 규칙은 checkout 409, 권한 거부, 결과 불명인 외부 쓰기에 적용하지 않는다.

## 8. 인계·세션·스냅샷

인계 패킷의 필수 내용은 목표·수용조건, 현재 상태, 완료분과 근거, 미완료, 결정·이유, 원본/결과 버전, 검증된 상품 사실, 금지사항, 막힘, 다음 행동·책임자다. 지침·스킬·기억은 정확한 버전 참조를 포함한다.

세션 재개는 동일 workspace/task·허용 경로·런타임 호환성을 확인해야 한다. 다른 프로젝트의 session_ref를 재사용하지 않는다. 새 AI에게 인계해도 과거 외부 승인·도구 권한·기기 credential은 자동 승계하지 않는다. 사용자 지침·스킬 변경은 다음 run의 스냅샷부터 적용하는 것을 기본값으로 제안한다. 긴급 revoke는 현재 run의 실행 경계를 즉시 차단하고 중단 여부를 확인한다.

## 9. 관측과 호환성 검증

필수 이벤트: `command.accepted`, `run.claimed`, `run.started`, `run.heartbeat`, `run.connection_lost`, `run.reconcile_requested`, `run.result_submitted`, `run.failed`, `run.cancel_requested`, `run.cancelled`, `artifact.reviewed`, `action.approval_decided`, `action.receipt_recorded`. 이벤트 이름은 제안이고 스키마 버전을 함께 보낸다.

실제 run이 없는 장시간 대기에는 모델을 반복 호출하지 않는다. 기기 재연결·명시적 지시·구조화된 선행조건 해제 등 유효한 wake 경로를 기록한다. 대시보드에는 마지막 활동 시각, 처리 지연, 최근 오류 코드, 복구 책임자·다음 확인을 표시한다.

구현 시 최소 호환성 시험은 중복 명령/이벤트, 2개 adapter의 동시 claim, 단절 전후 결과 조회, ACK 유실, 중앙·기기 재시작, 오래된 lease, unknown session, 취소 경합, 미지원 capability, protocol 불일치다. 미지원 protocol은 명확한 업그레이드 필요 오류로 차단하고 잘못된 기본값으로 실행하지 않는다. 검증 ID는 [AC-07~12, 20~22](ACCEPTANCE_CRITERIA.md)를 따른다.
