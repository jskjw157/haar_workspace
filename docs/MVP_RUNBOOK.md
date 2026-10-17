# M0 체험판 실행·운영

2026-10-17. 사용자 승인 문서 PR #1을 보존한 별도 구현 브랜치의 **첫 실행 가능한 체험판**이다. 제품 전체 MVP(M1~M4)를 완료했다는 뜻은 아니다. SELLAYER와 분리한다.

## 지금 가능한 것과 경계

- 모바일·데스크톱 Today 보드, 날짜별 집중 최대 3개, P0~P3·마감일·업무 영역·SKU·지시 초안·다음 행동 저장/수정.
- 수동 결과 링크/버전 메모, 최신 버전별 내용 확인·수정 요청, 직접 인계 기록·복사. 실제 게시/발송/광고비 변경은 수행하지 않는다.
- 다섯 AI 경로를 표시한다. 모든 실행 adapter는 미연결이다. 설치 관측은 2026-10-17의 점검 결과이며 실시간 연결 상태가 아니다.
- SQLite는 **Paperclip 등록 전 intake/초안의 저장소**다. Paperclip task 상태·checkout·run을 복제하지 않는다. `task_id`, `paperclip_issue_id`, `run_id`, `action_id`는 null이며 실제 원장 접수나 실행은 발생하지 않는다.
- `planned/blocked/review/archived`는 초안 정리 상태다. `in_progress`나 가짜 실행 진행률을 받지 않는다. 그래프는 최신 결과 링크에 대한 사람의 검토 비율이며 AI 실행 진행률이 아니다.
- 결과 URL은 가변 참조일 수 있다. 로컬 `version_id`는 등록 기록의 ID이며 파일 불변성/digest 검증이 아니다. ‘내용 확인’은 외부 행동 승인이 아니다.
- 초기 DB는 비어 있다. 사용자가 누른 경우에만 가상 예시 3개를 추가하고 각각 ‘가상 예시’를 표시한다. 사용자 입력은 예시가 아니다. 예시는 보관할 수 있지만 현재 hard delete UI는 없다.

## 실제 VPS 점검

2026-10-17 00:14~00:17 UTC, 기존 SSH alias `vps`를 통해 읽기 전용 점검했다.

| 항목 | 확인 결과 |
| --- | --- |
| OS / RAM | Ubuntu kernel 6.8, RAM 7,940 MiB, 가용 2,820 MiB, swap 0. 해당 시점 관측치이며 보장 예산 아님 |
| 디스크 | `/` 96GB 중 사용 70GB, 가용 27GB |
| Paperclip | 확인한 systemd 서비스·Docker 이미지/컨테이너·프로세스·일반 설치 경로에서 서버를 찾지 못함. 운영 관련 skill 문서는 존재. 설치 부재의 완전한 증명은 아님 |
| Buzz | `buzz-prod-relay-1`과 postgres/redis/minio는 기존 중지 상태. relay 이미지 revision `e17cdd9d5c7e2b836b4670ae88bb87a79f94337a`, 작업 소스 HEAD `78618804ec86a014524ad7d1fb55928e8f5c3edf` |
| Hermes | 기존 프로세스 관측. API/실행·취소 계약 미검증 |
| OpenClaw | 기존 `openclaw-gateway.service` active, `127.0.0.1:18789`. 호출·승인·취소 계약 미검증 |
| 기존 데이터 | Buzz volume 존재. 읽기/이관/재기동하지 않음. 기존 서비스·도메인·프록시·방화벽 그대로 유지 |

Paperclip 실제 원장을 연결하지 못했으므로 Task Core 재사용·Buzz 채팅 재사용은 **차단/후속 작업**이다. 본 체험판은 upstream 런타임 코드를 가져오지 않았고 MIT/Apache 모듈을 재사용했다고 주장하지 않는다. 원래 재사용 설계는 [TDD](TDD.md)를 유지한다. 독립 scheduler를 새로 구현하지 않는다.

## 로컬 실행

Python 3.12 이상, 표준 라이브러리만 사용한다. npm install/build·외부 CDN·모델 키가 필요 없다.

```sh
python3 -m app.server --port 3310
```

`http://127.0.0.1:3310` 접속. 기본 저장은 `.data/workspace.sqlite3`; git ignore 대상이다. 다른 DB 경로는 `--data /private/path/workspace.sqlite3`로 지정한다. 초기화·자동 seed는 없다. DB 기록과 로그를 공개 저장소에 커밋하지 않는다.

```sh
python3 -m unittest discover -s tests -v
node --check app/static/app.js
node tests/test_ui_state.cjs
```

HTTP 테스트는 임시 loopback 포트/DB를 사용한다. 실행 환경이 bind를 막는 경우 해당 환경 권한이 필요하다. 브라우저 화면 검증은 사용자 화면을 건드리지 않는 별도 headless 세션을 사용했다.

## VPS 격리 실행과 접속

- 새 서비스: `haar-workspace-mvp.service`.
- 코드: `/opt/haar-workspace-mvp-20261017/releases/<commit>/`, `current` symlink.
- DB: `/var/lib/haar-workspace-mvp/workspace.sqlite3` (DynamicUser의 private backing directory, mode 0700).
- listen: **127.0.0.1:3310만**. 신규 도메인·공개 ingress·방화벽 변경 없음.
- Python systemd `DynamicUser`, `ProtectSystem=strict`, `ProtectHome`, no capabilities, `MemoryMax=128M`, `CPUQuota=50%`, `TasksMax=32`. 이 수치는 방어 상한이며 측정 peak 예산이나 성능 보장이 아니다.

Mac에서 기존 인증된 SSH 경로로:

```sh
ssh -N -L 127.0.0.1:3311:127.0.0.1:3310 vps
```

그 후 `http://127.0.0.1:3311` 접속. 테스트 Mac 서버(3310)와 혼동하지 않도록 터널은 3311을 사용한다. 이 명령이 살아 있는 동안만 접속된다. 키·계정·OAuth를 새로 만들지 않는다.

**iPhone 원격 접속은 아직 제공하지 않는다.** 반응형 화면을 390px headless viewport에서 검증하는 것과 실제 iPhone에서 접근할 수 있다는 것은 다르다. iPhone에는 별도의 인증된 VPN/사설 접근 또는 인증 게이트가 필요하다. 무인증 공개 노출은 하지 않으며 접근/인증 변경 영향과 승인을 먼저 확인한다. Mac 터널을 LAN의 0.0.0.0으로 열지 않는다.

```sh
ssh vps 'systemctl status haar-workspace-mvp --no-pager'
ssh vps 'curl --fail http://127.0.0.1:3310/api/health'
```

새 서비스만 정지/재시작할 때 `systemctl stop/restart haar-workspace-mvp`를 사용한다. 기존 Buzz/OpenClaw/Hermes 등은 대상이 아니다. service enable은 부팅 시 이 격리 체험판만 재개한다. 롤백은 서비스 정지 → 기존 release로 `current` 변경 → 시작. 현재 스키마는 v1 최초 생성이며 파괴적 migration이 없다. DB 파일은 서비스 종료 후 별도 보존한 뒤 작업한다.

## 데이터 일관성·복구

- 명령별 `idempotency_key` + payload digest + 저장 receipt가 하나의 SQLite `BEGIN IMMEDIATE` 트랜잭션이다. 같은 키/내용은 같은 영수증, 다른 내용은 409.
- 편집·검토·인계는 `expected_revision` 충돌 검사. 한 날짜 집중은 서로 다른 항목 ≤3, 별도 revision 검사.
- 브라우저는 불명 응답의 요청을 sessionStorage에 보존하고 ‘같은 요청 재확인’으로 재조회/멱등 재전송한다. 명확한 4xx는 수정 후 새 요청, 5xx/네트워크 불명은 같은 요청 유지. 새 창/다른 기기의 sessionStorage 복구는 지원하지 않으므로 불명일 때 먼저 기존 목록을 확인한다.
- 성공 영수증을 받은 뒤 목록 조회 실패는 저장 실패로 처리하지 않는다. 보조 폼 저장이 다른 폼의 미저장 텍스트를 지우지 않는다.
- 재시작은 원본 DB에서 불러오며 재실행할 scheduler가 없다. 결과 검토는 최신 등록 버전에만 1회 기록하고 새 버전은 다시 pending이다.
- 최대 1,000개 intake, 항목당 결과 50개·인계 50개, HTTP body 16KB, 유한 문자열 길이. 중앙에 원본 파일/바이너리를 업로드하지 않는다.
- SQLite WAL 운영 중 단순 DB 파일 복사는 사용하지 않는다. 일관된 백업:

```sh
python3 scripts/backup.py /private/path/workspace.sqlite3 /private/backup/new-backup.sqlite3
```

`backup.py`는 새 파일만 생성하고 `integrity_check`를 확인한다. 복원 시 해당 서비스 중지, 현재 DB/WAL을 함께 보존한 뒤 검증한 백업으로 교체한다. 백업은 사용자 데이터이므로 비공개 경로에 보관한다. 주기 백업 자동화는 아직 없다.

## 보안 경계와 제한

애플리케이션 자체 인증은 없다. 기존 SSH 인증·loopback이 경계이며 동일 호스트의 다른 로컬 사용자는 접근할 수 있다. 여러 운영자/공개 운영용 서버가 아니다. Host allowlist, 동일 Origin JSON mutation, cross-site 차단, CSP/no-store/no-referrer, static allowlist, SQL parameter binding과 HTML escaping을 적용한다. 본문·URL·헤더를 access log에 남기지 않는다. 비밀정보를 자동 탐지·정화하는 시스템은 아니다. 비밀번호·토큰·고객 개인정보를 입력하지 않는다. 실제 credential helper/API key 설정은 이번 구현에 없다.

다음 단계는 실제 Paperclip 서버 위치/버전 확인 또는 별도 설치 영향 승인, single-source binding/원자 checkout·unknown hold contract spike, Buzz 재사용 격리 시험, 사용자 승인된 adapter 한 경로 연결이다. 그때 intake를 원장으로 ‘복사’해 이중 상태를 만들지 않고 기록 ID↔권위 있는 issue ID를 매핑하고 이관 receipt를 남기는 방식을 검증해야 한다.
