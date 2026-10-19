# 작업 노트 검증·운영 반영 상태

검증일: 2026-10-19. 기능 커밋 `4f7a5428d06f8f5d1d33afd825bbbd667ea2f2e0`. 부모 이벤트 자동 전달 PR #4 위의 독립 후속 변경이다.

## 완료된 검증

- Python 42개, Node 16개 테스트 통과. 실제 HTTP의 새 연결/서버 재시작 후 복원, 멱등 재요청, 동시 편집 단일 승자와 409, 잘못된 블록/상위 페이지/작업, Origin·본문 경계를 포함한다.
- 격리된 가상 작업의 실제 브라우저에서 슬래시→제목/체크/표, 하위 페이지, 제목/내용 검색, 자동 저장을 확인했다. 이 탭의 저장 요청만 실패시키고 현재 입력 보존/재연결 저장을 검증했다. 별도 실제 HTTP 클라이언트가 먼저 저장한 뒤 자동 덮어쓰기 없이 충돌이 멈추고, 서버본을 명시적으로 열어도 이전 초안 표시가 남는 것을 확인했다.
- 1440×1000·390×844 캡처에서 가로 넘침·계산된 텍스트 대비 위반 없음. 체크박스의 네이티브 label 클릭 영역은 44×44px이고 시각 체크박스는 24px다. 실제 label 클릭과 원래 체크 상태 복원을 확인했다.
- 독립 마무리 검수 `ship`. 디자인 문서 검수 `No changes`: 기존 DESIGN.md/sidecar·공통 스타일·이미지·정지된 전체 리디자인을 보존한다. 로컬 편집기의 글자 크기 차이를 전역 규칙으로 승격하지 않았다.
- 추가 패키지나 원본 튜토리얼 코드 재사용 없음. 개인 노트·캡처·DB·런타임 자료는 공개 Git에 포함하지 않는다.

## 승인 후 운영 반영 완료

이전 배포 요청은 명시적인 이번 릴리스 운영 승인 미확인으로 명령 실행 전에 거절됐다. 이후 사용자가 노트 배포·HAAR 단일 서비스 재시작과 주소 연결을 승인했고, 새 승인 근거로 한 번 재시도해 성공했다. 거절된 시도가 실행됐다고 소급해 표현하지 않는다.

- 운영 코드: `4f7a5428d06f8f5d1d33afd825bbbd667ea2f2e0`. 릴리스 사전 Python 42개 테스트 통과와 변경 허용 파일 SHA 검사를 완료했다. 공통 CSS·홈 JavaScript·이미지·기존 백업 코드는 바뀌지 않았다.
- SQLite 일관 백업 후 기존 11개 테이블의 스키마/행/user_version 해시가 배포 전후 동일했다: `03e66daabbd2e0e39889ebe5d8d9ea0a84f2dd3ba12ee691bdedc6a421ead888`. 정상 worker heartbeat의 `last_seen_at`만 비교에서 명시적으로 정규화했다. 그 외 필드·대장 전체 내용은 보존했다.
- `note_pages`/`note_commands` 두 테이블과 작업 인덱스만 추가했다. 기존 작업대장은 revision 10/28건이며 실제 작업의 우선순위·승인·완료 기준은 그대로다.
- `haar-workspace-mvp` 단일 서비스만 재시작했다. health 정상·dispatch 비활성, DynamicUser/ProtectSystem strict/ProtectHome yes/MemoryMax 128MiB/TasksMax 32·unit 파일 유지. 다른 VPS 서비스와 정지된 전체 디자인 작업은 변경하지 않았다.
- 실제 작업에 연결한 사실 기반 운영 메모 1개를 HTTP로 저장하고 새 연결에서 재조회했다. 외부 브라우저가 revision 3을 자동 저장하고 별도 모바일 브라우저 컨텍스트가 같은 본문을 복원했다. 작업대장 문서는 이 노트 저장 전후 동일했다. 개인 노트 본문과 페이지 ID는 공개 Git에 넣지 않는다.

## 외부 HTTPS·로그인 검증 완료

확정 [외부 작업대장](https://workspace.76.13.212.135.sslip.io/register). iPhone에서는 이 HTTPS 주소를 사용한다.

기존 Caddy의 80/443에 HAAR 전용 호스트만 추가했다. 설정·실행 구성을 먼저 백업한 뒤 validate/adapt 검증과 reload만 수행했다. 기존 10개 호스트의 라우트 동작과 모든 실행 중 컨테이너의 PID/시작 시각을 보존했다. Caddy가 생성하는 그룹 식별자 차이만 정규화해 의미를 비교했다. 새 포트·방화벽·DNS 계정 권한·도메인 구매/결제·다른 서비스 재시작은 없다. 무료 공개 DNS의 기존 VPS 방식과 Let's Encrypt TLS를 사용한다.

전용 Basic Auth 계정으로 모든 화면·정적 파일·API를 보호한다. 새 임의 암호는 서비스 전용 Mac 키체인 항목에만 저장하고 서버 Caddyfile에는 bcrypt cost14 해시만 둔다. 기존 Apple Passwords 항목을 읽지 않았다. 평문 암호/Authorization은 모델 출력·로그·DB·Git·산출물에 기록하지 않았다. 새 호스트 접근 로그는 discard다. upstream으로 Authorization을 제거하며 앱은 loopback에 그대로 바인딩한다.

변경 요청은 외부 HTTPS Origin의 정확 일치 여부를 프록시에서 검사하고 통과한 요청만 기존 localhost Host/Origin으로 전달한다. 앱의 기존 JSON·본문·Sec-Fetch-Site·CSP 경계도 유지한다.

검증 결과:

- 외부 TLSv1.3 인증서 검증 성공, 해당 호스트 SAN, Let's Encrypt 발급, 2027-01-17 만료 확인. HTTP는 HTTPS로 308 전환된다. 인증서 자동 갱신은 기존 Caddy 동작에 맡긴다.
- `/`, `/register`, `/notes`, `/api/register`, `/api/notes`, `/style.css`, `/notes.js`, `/api/health` 모두 비인증 401. 잘못된 암호도 401.
- 올바른 로그인 후 health/작업대장/노트 조회 성공. 외부 Origin과 누락 Origin의 POST는 403.
- 실제 외부 URL에서 데스크톱 1440×1000와 모바일 390×844 별도 인증 컨텍스트를 검증했다. 저장·복원 revision 3, 가로 넘침 없음, JavaScript 오류 없음, 모바일 체크 터치 영역 44×44px. 실제 iPhone 하드웨어/Safari 검증을 주장하지 않는다.
- 검증용 브라우저 컨텍스트는 모두 종료했고, 운영 자동 전달 worker와 기존 SSH 터널은 유지한다.

로그인 암호는 Mac의 ‘키체인 접근’에서 `HAAR Workspace HTTPS workspace.76.13.212.135.sslip.io` 항목을 찾아 사용자가 직접 표시·복사한다. 이 항목의 계정은 `haar-owner`다. iPhone 암호 자동 공유/동기화가 설정됐다고 가정하지 않는다. 기존 localhost 터널도 계속 사용할 수 있다.

[Caddy Basic Auth](https://caddyserver.com/docs/caddyfile/directives/basic_auth), [reload·hash-password](https://caddyserver.com/docs/command-line), [reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)의 공식 계약을 확인했다.

증거는 X9 Pro 비공개 `output/notes/`에 보존한다. 배포 영수증·실제 HTTP 노트 재조회·`external/access-proof.json`·`external/browser-proof.json`·외부 데스크톱/모바일 캡처·Caddy 백업/변경 영수증이다. 비밀번호·개인 DB·실제 화면은 공개 Git에서 제외한다.
