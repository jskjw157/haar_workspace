# 기술 검토·재사용 경계·공식 출처

확인일 2026-10-16. 공개 공식 저장소와 제품 문서를 읽은 결과다. 사용자의 기존 VPS·Mac 설치 상태, 실제 계정 연동·API 호출은 검증하지 않았다. 아래 제품 선정 방향은 **사용자 합의**, 통합 방식·비용·업데이트 운영은 **기술 제안**이다.

## 1. 결론과 활용 범위

| 대상 | 공식 자료로 확인한 내용 | HAAR 적용 방향 | 구현 전 확인할 제약 |
| --- | --- | --- | --- |
| Paperclip | 작업·실행·checkout 중심의 control plane. 별도 MCP 패키지는 REST API 래퍼 | 작업 상태·실행기록 중심으로 활용 | 기존 설치 미확인, 고정 버전 API·상태·인증 매핑 검증 |
| Buzz | 사람·AI 채널, CLI·ACP 및 WS/REST 경로. README는 모바일·workflow approval gates 일부를 개발 중으로 표시 | 사람–AI 채널 모듈 활용 | 채널만 떼어도 인증·이벤트·DB·relay 의존성 존재, 승인 완성 가정 금지 |
| Argo | 공개 문서의 기억·인계·카드·스킬 UX. 공개 GitHub는 설치파일 배포 전용이며 앱 소스 비공개 | 공개 동작을 참고해 독자 구현 | 코드 재사용 금지, 외부 API/MCP 호출 계약 미확인, 직접 연동은 MVP 필수조건 아님 |

위 사실의 공식 근거는 각각 [P-01~P-06](#4-paperclip-공식-근거), [B-01~B-04](#5-buzz-공식-근거), [A-01~A-03](#6-argo-공식-근거)에 연결한다. 아래의 HAAR lease·action 승인·데이터 모델은 독자 설계 제안이며 upstream 기본 동작이라는 주장이 아니다.

## 2. 재사용 선택과 모듈 분리 비용 [제안]

| 선택 | 기대 효과 | 비용·위험 | 진행 기준 |
| --- | --- | --- | --- |
| Paperclip 확장/plugin/API로 Task Core 연결 | 기존 작업·run 기록·checkout 재사용 | 인증·원장 ID·상태 전이·사용자 승인·추가 필드의 경계 매핑 | 상태 권위가 하나이며 장애 시 이중 실행 없음 |
| Paperclip 포크/UI 수정 | 홈·SKU UX를 깊게 바꿀 수 있음 | upstream 변경 충돌, DB migration·보안 패치 추적 부담 증가 | 확장으로 불가능한 요구를 스파이크로 입증 후 비교 결정 |
| Buzz relay+채널 기능을 별도 서비스로 연결 | 서명 이벤트·채널·CLI 기반 활용 | Rust 서비스 + Postgres/Redis + media·인증 운영, HAAR ID 매핑·중복 수신·검색 권한·이벤트 bridge 필요 | 단일 상태 원장을 침범하지 않는 최소 채널 흐름 검증 |
| Buzz UI/채널 코드 일부 추출 | HAAR 웹에 통합된 UX | crate·schema·relay 의존성 분해, API 호환 shim, 프런트 의존성·디자인 변경, 보안 책임 독자 유지 | 추출 경계·의존성 목록·테스트 비용을 별도 설계 검토 |
| Argo UX 참고 독자 구현 | 기억 provenance·인계·카드·스킬을 HAAR에 맞춤 | 메모리 모델·평가·버전·승인 UX를 직접 설계·검증 | 공개 동작 수준만 참고하고 소스/API 접근을 전제하지 않음 |

상대적으로 Paperclip 확장/API 후보는 중간, 포크와 Buzz 세부 추출은 높은 통합·유지보수 부담으로 본다. 이는 일정/견적이 아닌 위험 평가다. M0에서 기능 경계별 의존성 그래프, 최소 흐름 성공 증거, 업데이트 시 수정 지점을 작성한 뒤 채택 단위를 정한다.

권고 경계는 `task-core bridge`, `channel bridge`, `execution gateway/adapter`, `SKU·memory·skill·approval 확장`이다. 같은 task.status를 두 DB가 독립적으로 확정하지 않는다. Buzz의 메시지 이벤트 원장과 Paperclip의 작업 원장은 서로 다른 책임을 가진다. HAAR 읽기 투영은 원장·커서로 재구축 가능해야 한다.

MCP 연결과 AI 실행은 별도 계약이다. 도구를 등록하면 해당 AI가 호출할 수 있을 뿐, 기존 GPT/dot 대화와 Mac의 모든 앱이 자동으로 깨지 않는다. 시작·상태 조회·중단·세션 재개를 지원하는 adapter가 있어야 직접 실행을 제공한다. 미지원 도구는 수동 인계로 표시한다.

## 3. 라이선스·의존성·업데이트 전략 [제안]

Paperclip의 루트 LICENSE는 [MIT](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/LICENSE), Buzz는 [Apache-2.0](https://github.com/block/buzz/blob/93ffc37cbdb7ced6a07eca11744931cdffb82e20/LICENSE)이다. 실제 코드 도입 시 원문 라이선스·저작권 고지, 수정 고지 및 해당 NOTICE 유무를 확인·보존한다. 루트 라이선스만으로 하위 의존성·이미지·폰트·상표까지 일괄 허용되었다고 판단하지 않는다.

이번 PR은 링크와 독자 요구사항 문서만 작성하며 upstream 코드를 가져오지 않는다. 이 저장소 전체에 MIT/Apache 라이선스를 새로 부여하지 않는다. 소스 도입 단계에서 파일·버전·출처·라이선스·수정 내역·전이 의존성·취약점·NOTICE를 목록화하고 배포물에 필요한 고지를 포함한다.

업데이트 운영 제안:

1. 채택 시 upstream commit/tag와 lockfile, contract 버전을 고정한다. `latest` 자동 운영 업데이트를 기본으로 두지 않는다.
2. 수정 코드는 bridge/확장에 모으고 포크 diff를 작게 유지한다. upstream 내부 함수 의존 여부를 별도로 기록한다.
3. 정기 호환성 검토와 보안 공지 검토 담당을 정한다. 실제 정기 자동화 생성은 이번 범위가 아니다.
4. 새 버전은 격리 환경에서 checkout 충돌·상태 매핑·이벤트 중복·승인·비밀 제거·재연결 회귀를 통과해야 한다.
5. DB migration·queue/event 커서·외부 action ledger가 있는 업데이트는 백업·복원·하위 호환성을 검증한다. 앱 버전만 되돌려 복구된다고 가정하지 않는다.
6. 실패하면 이전 배포/스킬 승인 버전으로 전환하고 실행 중 run의 실제 결과·승인 소비 기록을 보존한다.

## 4. Paperclip 공식 근거

검토 시 기본 브랜치 `master`의 커밋은 [`b294abb9eb96c33048b4f53a2a037e04886b7407`](https://github.com/PaperclipAI/paperclip/commit/b294abb9eb96c33048b4f53a2a037e04886b7407)였다. 아래는 이 커밋으로 고정한 출처다. 도입 시 다시 호환성을 확인한다.

| ID | 공식 출처 | 확인 내용·설계 반영 |
| --- | --- | --- |
| P-01 | [README](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/README.md) | 작업·실행·승인 중심의 제품 방향. HAAR 작업 원장 후보의 근거 |
| P-02 | [packages/mcp-server/README.md](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/packages/mcp-server/README.md) | MCP 패키지는 기존 REST를 감싸며 DB·업무 로직을 다시 구현하지 않음. MCP와 실행 adapter 구분 |
| P-03 | [doc/execution-semantics.md](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/doc/execution-semantics.md) | 단일 assignee, 구조/의존성/소유권/실행 분리, checkout 409 충돌 시 동일 checkout 반복 금지. HAAR 중복 방지·다음 행동 모델 근거 |
| P-04 | [doc/public-mcp.md](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/doc/public-mcp.md) | public assistant MCP는 Experimental 설정이며 기본 비활성. REST 래퍼와 public MCP 표면을 혼동하지 않음 |
| P-05 | [AGENTS.md](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/AGENTS.md) | 회사 범위·원자 checkout·승인·기록 원칙, telemetry/observability/run log 구분 참고. upstream 코드 수정 시 해당 지침 재확인 필요 |
| P-06 | [.agents/skills/create-agent-adapter/SKILL.md](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/.agents/skills/create-agent-adapter/SKILL.md) | server/UI/CLI 경계, 환경 점검·세션·출력 파싱·권한 경계 확인. HAAR 원격 큐 계약과 그대로 같은 API라고 가정하지 않음 |

추가로 `.agents/skills` 목록과 [doc-maintenance 스킬](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/.agents/skills/doc-maintenance/SKILL.md)을 읽어 문서 드리프트 점검 관점을 확인했다. 이는 외부 소스 조사이며 HAAR 저장소에 해당 코드·스킬을 설치하거나 upstream 문서 변경 워크플로를 실행한 것이 아니다.

## 5. Buzz 공식 근거

검토 시 기본 브랜치 `main`의 커밋은 [`93ffc37cbdb7ced6a07eca11744931cdffb82e20`](https://github.com/block/buzz/commit/93ffc37cbdb7ced6a07eca11744931cdffb82e20)였다.

| ID | 공식 출처 | 확인 내용·설계 반영 |
| --- | --- | --- |
| B-01 | [README](https://github.com/block/buzz/blob/93ffc37cbdb7ced6a07eca11744931cdffb82e20/README.md) | 채널·CLI·ACP·WS/REST와 현재/개발 중 기능 구분. 모바일·workflow approval gates를 완성된 MVP 의존성으로 두지 않음 |
| B-02 | [ARCHITECTURE.md](https://github.com/block/buzz/blob/93ffc37cbdb7ced6a07eca11744931cdffb82e20/ARCHITECTURE.md) | relay·서명 이벤트·인증·저장·팬아웃 경계. 단순 채팅 UI 복사 이상의 통합 비용 반영 |
| B-03 | [AGENTS.md](https://github.com/block/buzz/blob/93ffc37cbdb7ced6a07eca11744931cdffb82e20/AGENTS.md) | 제품/코드 경계와 검증 규칙 확인. 실제 Buzz 코드 수정 시 제품·검증 지침 재검토 필요 |
| B-04 | [.agents/skills/sprout-cli/SKILL.md](https://github.com/block/buzz/blob/93ffc37cbdb7ced6a07eca11744931cdffb82e20/.agents/skills/sprout-cli/SKILL.md) | CLI 출력·이벤트 ID·오류·명령별 제약 확인. CLI 출력만으로 모든 실행 이력이 완결된다고 가정하지 않음 |

`buzz-cli` 스킬은 공식 `.agents/skills/sprout-cli` 경로에 있는 파일을 읽었다. 기능표는 버전에 따라 달라질 수 있으므로 실제 채택 버전에서 모바일·승인 게이트·run 조회를 다시 시험한다. 이번 문서 작업에서는 Buzz 메시지를 발송하지 않았다.

## 6. Argo 공식 근거

| ID | 공식 출처 | 확인 내용·설계 반영 |
| --- | --- | --- |
| A-01 | [Argo docs](https://argo.ceo/docs) | 카드·기억·인계·스킬 UX 참고. 외부 CLI가 승인 gate를 거치지 않는 제약과 격리 한계를 명시. 로컬 우선이어도 로그인 시 회사 데이터의 클라우드 복제, 메신저 서버 저장 설명이 있으므로 ‘기기 밖으로 안 나감’으로 해석하지 않음 |
| A-02 | [Argo Messenger](https://argo.ceo/messenger) | 사람–AI 채널·멘션·인계·승인 UX의 공개 설명. 제품 설명이 HAAR가 호출할 수 있는 API 계약을 입증하지 않음 |
| A-03 | [beyondworks/argo-agent README](https://github.com/beyondworks/argo-agent/blob/main/README.md) | 설치파일 배포 전용, 앱 소스 비공개 명시. Argo 코드 재사용 계획 제외 |

Argo docs의 확인 시 표시된 갱신일은 2026-07-15였다. 문서·홍보 페이지 사이 제공 상태 표현은 달라질 수 있다. 위 비교는 공개 설명의 참고이며 설치·기능·보안의 실증 검증이 아니다. 비공개 소스·내부 시스템 프롬프트는 요청·수집하지 않는다. API/MCP 외부 호출의 인증·버전·권한 계약은 확인하지 못했으므로 직접 제품 연동은 후속 별도 조사로 남긴다.

## 7. 검증 범위와 남은 확인

확인한 것은 저장소 메타데이터, 공개 공식 문서·라이선스, 관련 `.agents/skills`와 구조다. 실제 서버 설치·소스 빌드·라이브 connector·Apple Keychain API·각 SNS/광고/CS 플랫폼의 쓰기 API는 이번에 실행·검증하지 않았다. 이에 관한 설계는 PRD에서 [제안] 또는 [미확인]으로 남긴다.

첫 구현 전에는 각 채택 버전의 공식 API, 라이선스·NOTICE·전이 의존성, 인증/권한 강제, 상태 매핑, 외부 결과 조회 방법을 별도 evidence로 기록해야 한다. Argo 계약 미확인이나 Buzz 모듈 분리 지연 때문에 기본 기록·집중·수동 검수까지 막히지 않도록 단계별 경계를 유지한다.
