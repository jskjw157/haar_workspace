# Library 작업대장과 Workspace 연결

## 상태 기준과 실제 지원 범위

Library JSON이 단일 상태 원본이다. MD는 JSON에서 만든 열람본이다. VPS는 마지막으로 검증해 가져온 JSON의 원문·Library 파일 ID/버전·SHA-256·가져온 시각을 보관한다. 문서 안 `version`과 Library 보관 버전은 별개이며 혼동하지 않는다. 상태를 Paperclip intake 단계로 변환하거나 기존 intake 기록과 합치지 않는다.

`/register`에서 고유 작업 ID, 원본 상태, 사용자 지정 우선순위, 최신 지시, 마지막 확인 시각, 근거, 블로커, 완료 기준, 결과 참조와 원본 전체 필드를 조회한다. 근거가 원본에 없으면 임의 보충하지 않고 누락 경고를 표시한다. 기존 작업 번호와 알려지지 않은 확장 필드도 그대로 보존한다. 홈 상단과 하단에서 작업대장으로 이동할 수 있다.

자동인 부분: 열려 있는 화면은 60초마다 VPS 확인본을 읽는다. 동일 원본의 새 Library 버전을 권한 있는 소비자가 가져와 import하면 다음 화면 조회에 반영된다. 입력 중에는 갱신으로 작성 내용을 지우지 않는다. 개별 작업의 마지막 확인 시각을 조회 시각으로 바꾸지 않는다.

자동이 아닌 부분: VPS에는 Library 인증·연결 계약이 없으며 새 키/OAuth/지속 접근권한을 만들지 않았다. 공식 Library 소비자의 materialization·업데이트 확인과 기존 SSH 경로를 통한 import가 필요하다. 파일 복사는 양방향 동기화 완료가 아니다. 각 AI 세션·Mac 앱·광고·게시·서버 작업의 실행 상태를 수집하거나 시작/중지하지 않는다. 기존 디자인 변경의 정지도 유지한다.

## 데이터와 API

- 기존 records/focus/commands/events는 변경하지 않는다. register_snapshots/state/proposals/commands/events와 pending 제안 고유 인덱스를 추가한다.
- `GET /api/register`: 확인본·원본 버전/해시·가져오기 시각·실패/구버전 표시·근거 누락 경고·제안과 최근 기록. no-store.
- `POST /api/register/proposals`: source version + idempotency key로 상태/설명/다음 행동/블로커/실제 확인 시각/근거의 제안을 저장한다. 완료 기준·지시·담당·참조/확장 필드는 바꿀 수 없다. 같은 작업의 대기 제안은 하나다. Library 원본은 그대로다.
- `POST /api/register/cancel`: 아직 대기 중인 제안만 취소한다. 실제 작업을 중지하지 않는다.
- `POST /api/register/export`: 특정 대기 제안의 JSON 후보·MD 열람본·원본 Library ID/expected version/해시를 동결해 내보낸다. 내보내기는 Library 반영 완료가 아니다.
- 원본 import HTTP 경로는 없다. 기존 권한의 서버 운영 CLI에서만 가져온다. Host/Origin/본문 제한과 외부 사이트 차단을 기존 API와 동일하게 적용한다.

## 가져오기·반영 흐름

1. 권한 있는 Library 소비자가 같은 원본 ID를 공식 materialization 경로로 내려받고 Library 버전 메타데이터를 보존한다. JSON·MD의 크기/해시/버전과 작업 수·고유 ID·필수 필드를 검사한다. 과거 파일과 새 버전은 분리 보존한다. 실제 작업 내용은 공개 Git에 넣지 않는다.
2. 현재 VPS 확인 버전을 조회한다. 서비스 배포·중지가 필요하면 HAAR 대상과 이유를 먼저 알린다. 기존 DB를 새 파일로 일관 백업하고 무결성을 확인한다. import CLI도 백업 파일을 새로 만들며 덮어쓰지 않는다.
3. `python3 -m app.register --data DB import --file MATERIALIZED_JSON --library-id SOURCE_ID --version LIBRARY_VERSION --minimum-version MINIMUM_KNOWN_VERSION --expected-version CURRENT_VPS_VERSION --expected-count TASK_COUNT --sha256 SHA256 --backup NEW_BACKUP_FILE`.
4. BEGIN IMMEDIATE 안에서 단일 원본 ID, 증가 버전, expected version을 검사한다. 같은 ID/버전/해시는 중복 재시도로 처리한다. 같은 버전의 다른 내용·이전 버전·기존 ID 삭제·중복 ID·해시/건수 오류는 거부하고 마지막 정상 확인본을 유지한다. 정상 확인본과 각 import/실패 이력을 보존한다. 중간 실패도 이전 확인본이 기준이다.
5. 화면 수정은 우선 대기 제안이다. JSON/MD 내보내기를 권한 있는 Library 소비자에게 전달한다. 소비자는 **최신 원본을 다시 확인하고** 원본 ID를 유지하며 `expected_current_version`으로 교체해야 한다. 원본이 이미 바뀌었으면 후보 전체 파일로 덮어쓰지 말고 최신본에 필요한 제안만 재검토한다. MD도 동일 JSON 내용으로 만든 열람본으로 교체하되, 각 파일의 버전 충돌을 별도로 검사한다. 이 환경의 호스트 업로더 제한은 원본 업데이트 경로가 생겼다는 의미가 아니다.
6. 실제 Library 새 버전을 다시 materialize/import한 후에만 해당 제안과 필드가 일치하는지 비교해 confirmed로 표시한다. 일치하지 않거나 다른 원본 변경이면 conflict로 남긴다. 여러 작업의 제안을 내보내더라도 소비자는 서로 다른 오래된 전체 후보를 연달아 덮어쓰면 안 된다. 항상 최신 원본에서 재검토한다.

CLI `export --proposal-id ID --directory NEW_DIRECTORY`는 candidate.json/candidate.md/manifest.json을 새 디렉터리에 만든다. 상태·근거·완료 기준·기타 필드를 모두 확인한 뒤 공식 소비자가 반영한다. JSON이 성공하고 MD가 실패하면 JSON이 기준이며 MD 불일치와 남은 작업을 명시한다. 확인 없이 양쪽 완료로 표시하지 않는다.

## 보안·실패·검증

새 인증/권한/방화벽/게시/광고 실행을 추가하지 않는다. 기존 loopback3310과 SSH3311만 사용한다. 원본 상태를 수정하는 것과 실제 작업 실행 권한은 분리한다. UI는 JSON을 HTML로 주입하지 않고 textContent로 표시한다. 개인정보/비밀정보가 포함된 원본·로그·실제 화면은 공개 저장소에 포함하지 않는다.

네트워크/Library 실패가 VPS에 전달되지 않으면 서버가 이를 자동 감지할 수 없다. 그래서 항상 확인본 버전·가져온 시각·Library 실시간 상태 미확인 표시를 유지한다. import 검증 실패는 구버전 경고를 남기고, 화면 조회 실패도 기존 렌더를 유지한다. 원본의 완료 상태는 해당 완료 기준에 한정하며 현재 실행 중이라는 뜻을 추론하지 않는다.

테스트는 기존 intake 데이터 보존, 중복·경합·같은 버전 내용 변경·다른 원본·삭제/필드 오류 차단, 제안의 원본 불변, 확장 필드/완료 기준 보존, 동결 export, 원본 새 버전 확인/충돌, 취소·재시작 이력, HTTP CSRF/경로 경계와 화면용 API 상태 변화를 확인한다. 실제 반영 영수증은 별도 기록한다.

구현·테스트·운영 반영 상태는 [검증 기록](REGISTER_SYNC_VERIFICATION.md)을 확인한다. 운영 배포는 별도 승인 대기이며, 로컬 검증과 구분한다.
