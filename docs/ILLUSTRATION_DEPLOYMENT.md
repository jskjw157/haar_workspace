# 일러스트 실제 배포·데이터 보존 기록

2026-10-18 UTC. 사용자가 HAAR Workspace 배포와 해당 서비스 재시작을 명시 승인한 뒤 실행했다. 이전의 ‘로컬 검증·배포 준비만 완료’ 상태를 갱신하는 기록이다.

## 반영 범위

- 배포 코드: `b9253134b4abf6c7ac8a2cf23f13378f81e05312`.
- archive SHA-256: `75179236df93c2cf10384894ea76f3a12d8c808a42a9625ea669d5a42236f4fa`, 전송 전후 일치.
- 자체 서비스 `haar-workspace-mvp`만 정지·시작했다. current는 `/opt/haar-workspace-mvp-20261017/releases/b925313`을 가리킨다.
- 이전 release `92140ca`는 그대로 보존했다. 다른 봇/서비스, VPS 전원, 권한·계정·키, 방화벽·도메인·공개 ingress는 변경하지 않았다.
- 원래 service unit 파일의 전후 SHA가 동일하다. DynamicUser, ProtectSystem=strict, ProtectHome, StateDirectory, MemoryMax=128MiB, TasksMax=32와 WorkingDirectory를 유지했다. 최종 active/running, NRestarts=0.

## 배포 전 안전 검사

기존 배포 도우미의 ‘backend가 완전히 동일해야 한다’ 조건은 이번 정적 경로 추가와 맞지 않으므로 그대로 실행하지 않았다. 대신 새 archive를 서비스 정지 전에 열어 다음 조건을 검증했다. 안전 검사를 끄거나 무조건 통과시키지 않았다.

- server.py의 **검토된 정적 이미지 등록 2줄만 정확히 한 번** 존재한다. 이 두 줄을 제외하면 이전 server.py와 전체 바이트가 동일하다.
- 나머지 app Python 파일 집합과 각 파일, `scripts/backup.py`는 이전 release와 바이트 동일하다. DB/schema/작업·승인·실행 로직 변경이 없다.
- archive는 안전한 상대 경로의 일반 파일·디렉터리만 포함하며 DB/runtime output을 포함하지 않는다.
- 네 WebP의 SHA-256 및 RIFF/WEBP 헤더가 검토한 파일과 일치한다.
- VPS의 새 release에서 Python HTTP/저장소 테스트 14/14가 통과한 후에만 서비스를 정지했다.

## 백업·DB 보존·롤백

HAAR 서비스 정지 후 기존 SQLite를 읽기 모드로 열어 integrity_check, foreign_key_check, 전체 schema/user_version과 records/focus/commands/events의 정렬 내용 digest를 확인했다. 비공개 새 파일 `/var/lib/private/haar-workspace-mvp/illustrations-backup-b925313.sqlite3`에 SQLite backup API로 백업했고 백업의 무결성과 내용 digest가 원본과 일치했다. 운영 중 DB 파일만 단순 복사하지 않았다.

새 current symlink를 원자 교체하고 HAAR를 시작한 뒤 같은 검사를 반복했다. 전후 schema·논리 데이터 digest가 동일하며 records 3 / focus 1 / commands 4 / events 4가 보존됐다. seed, migration, 삭제, 실제 UI mutation은 수행하지 않았다. 백업은 36,864 bytes이며 공개 저장소나 Library로 복사하지 않았다.

사전 준비한 실패 경로는 HAAR 정지 → 이전 current 복구 → HAAR 시작이며, DB를 오래된 백업으로 자동 덮어쓰지 않는다. 이번 배포는 성공해 롤백을 실행하지 않았다.

## 서버 응답 확인

- health `status=ok`, `mode=intake_only`, `dispatch_enabled=false`.
- focus/empty/review/connection의 `/illustrations/*.webp` 네 경로는 200, `image/webp`, 검토한 파일과 SHA-256 일치. 전송 크기 합계 38,604 bytes.
- listen은 기존 **127.0.0.1:3310만** 유지한다. 기존 Mac SSH 터널 `http://127.0.0.1:3311`에서도 health 응답을 확인했다. 이 터널은 새로 만들거나 재시작하지 않았다.

## 실제 3311 화면 검증

2026-10-18 03:06 UTC, 격리된 실제 Chrome에서 기존 `http://127.0.0.1:3311`을 열었다. 브라우저 요청은 같은 origin의 GET만 허용했으며 실제 데이터 쓰기를 하지 않았다.

- Today/전체/검토/AI 4화면 × 320/390/768/1440px, **16조합 통과**. document-wide overflow 0, 표시 이미지 로드 실패 0, 장식 alt 누락 0.
- 3311 경로의 health 및 네 이미지 200/MIME/RIFF/WEBP/SHA를 별도 확인했다. AI 실행 미연결 문구와 초안 모드를 유지한다.
- page error / console warning·error / HTTP error / 차단된 비GET·외부 요청 **모두 0**.
- 실제 desktop 1440px, mobile 390px, AI 경로 mobile 캡처를 직접 열어 그림 표시·텍스트 가독성·기존 행 구조를 확인했다.
- 캡처·상세 영수증은 로컬 `output/illustrations/live/`, `live-browser-checks.json`, `deployment-live-result.jsonl`에 보관하며 공개 Git에 올리지 않는다. 백업 DB도 공개하지 않는다.

반응형 검증은 실제 iPhone 원격 인증 경로 제공 또는 VoiceOver 실기 감사와는 별개다.
