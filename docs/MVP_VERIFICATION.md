# M0 체험판 검증 기록

2026-10-17 UTC. 코드 release `11ce4e0` 기준. 전체 PRD 수용 완료가 아닌 현재 M0 기능 범위의 검증이다.

## 구현·테스트

| 검증 | 결과·범위 |
| --- | --- |
| Python 저장소/HTTP | `python3 -m unittest discover -s tests -v`: 14/14 통과. 임시 DB·loopback에서 지속성·동시 멱등 요청·키 충돌·revision 충돌·집중 3개·날짜·버전 검토·https 링크·가짜 실행 상태 거부·CSRF/Host/static 접근·body 상한 확인 |
| UI 상태 회귀 | `node --test tests/test_ui_state.cjs`: 6/6 통과. 성공 영수증 뒤 조회 실패와 보조 폼 저장 시 미저장 텍스트/최신 서버 상태 보존. 실제 UI 함수 + DOM/network doubles, 전체 브라우저 테스트를 대체하지 않음 |
| 구문/공백 | `node --check app/static/app.js`, Python compile, `git diff --check` 통과 |
| 독립 리뷰 | 별도 reviewer가 코드·저장소 테스트·보안 경계를 검토. 중복 생성 위험과 미저장 텍스트 유실/상태 덮어쓰기 발견 후 수정. 최종 Critical/Important 잔여 없음. 전체 보안 감사 아님 |
| 실제 브라우저 | 별도 headless Chromium: 새 입력/마감 저장 → 집중 상한 3개/4개째 거부 → 결과 링크 등록 → 최신 버전 검토 → 인계 → 본문 수정 저장 확인. 미저장 brief 보존과 stage=review 실제 DOM 확인 |
| 반응형 | 320/390/768/1440px에서 document.scrollWidth=viewport, 전체 가로 넘침 없음. 390px와 desktop 화면 직접 확인. iPhone 실기/VoiceOver 검증은 아님 |
| 브라우저 오류 | 최종 새로고침 후 console error/warning 0. 상한 실패 시 예상 422는 오류 UI로 표시됨 |
| 백업 | 표준 SQLite online backup과 integrity_check 로컬/VPS 모두 통과. 사용자 데이터 이관은 없음 |

화면 캡처는 로컬 `output/playwright/desktop.png`, `mobile.png`, `vps-desktop.png`, `vps-mobile.png`에 있으며 git ignore한다. 가상 예시/시험 데이터만 포함한다.

## 실제 VPS 검증

- 코드 archive SHA-256: `101f222f353c18baa4b827c27999d39b07c32b763d4eea3d1bf31ba80dfc4659`. 전송 전후 일치.
- 새 경로와 포트·unit 미존재 확인 후 `/opt/haar-workspace-mvp-20261017/releases/11ce4e0`에만 설치했다.
- `systemd-analyze verify` 통과, `haar-workspace-mvp.service` active/running, enabled. `NRestarts=0` 관측(검증용 명시적 restart와 별개).
- listen `127.0.0.1:3310`만 확인. health `status=ok`, `mode=intake_only`, `dispatch_enabled=false`.
- 초기 빈 DB를 확인한 뒤 검증자가 명시적으로 가상 예시 3개와 2026-10-17 집중 목록을 추가했다. 모두 sample=true, task_id/run_id=null이다. 실제 상품·고객·작업을 가져오지 않았다. 다음 날짜의 집중 목록은 별도 선택한다.
- 새 서비스만 재시작한 뒤 예시 3개/집중 3개 유지 확인. 전용 private state directory mode 0700. 기존 Buzz volume 읽기/이관 없음.
- cgroup MemoryCurrent 약 10.8~13.6 MiB, MemoryPeak 약 11.3~14.1 MiB 구간 관측. 일반적인 입력/가상 예시 확인 시점이며 동시 부하·장기 peak/p95 측정 아님. 서비스 상한 128MiB와 구분한다.
- 기존 app/social/searchad 컨테이너 및 OpenClaw active, Buzz 일괄 stopped 상태 유지. 공유 프록시·도메인·방화벽·인증 키 변경 없음.
- 기존 SSH 인증으로 Mac `127.0.0.1:3311` → VPS `127.0.0.1:3310` 터널 연결. 실제 페이지가 집중 카드 3개를 렌더링하고 390px overflow=false, console 오류 0 확인. 터널을 통한 집중 해제/다시 선택도 저장 성공했다.

## 남은 차단 사항

| 대상 행동 | 상태·이유 | 이미 완료한 것 / 다음 조건 |
| --- | --- | --- |
| Paperclip 원장 접수·로직 재사용 | **미연결**. 확인 범위에서 서버를 찾지 못함. 새 인증·설치 환경을 임의 구성하지 않음 | 현 상태 관측과 명시적 intake 경계를 구현. 실제 서버 위치 확인 또는 격리 설치·설정 영향 검토 후 canonical binding/checkout 검증 필요 |
| Buzz 채팅/채널 | **미연결**. 기존 relay 및 의존 서비스 중지 | 소스/이미지 revision·volume 존재만 확인. 기존 서비스 재기동·데이터 변경 안 함. 별도 격리 통합 시험 필요 |
| 다섯 AI 자동 실행 | **미연결**. adapter 실행·조회·취소·unknown hold 계약 미검증 | UI는 모두 미연결·실행 불가, 수동 인계만 제공. 실제 dispatch/실행 권한 없음 |
| iPhone 원격 접근 | **제공 전**. 인증된 모바일 접근 경로 없음 | 반응형 화면 검증과 SSH Mac 접속 완료. 인증/VPN 또는 공개 인증 게이트는 영향 보고·승인 후 구성 필요 |

차단 행동은 실행하지 않았으며 자동 승인 심사에서 거절된 작업은 없다. 승인/연결 대기와 성공을 혼동하지 않는다. 이 결과는 실제 업무 상태/실행 원장 통합을 완료한 MVP가 아닌, 사용자 피드백을 받을 수 있는 운영 중 M0 체험판이다.
