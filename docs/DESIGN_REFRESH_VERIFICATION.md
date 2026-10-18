# M0 디자인 시스템 교체 검증

2026-10-17. 사용자가 기존 컴포넌트와 디자인 시스템 자체의 교체를 요청해 M0 브랜치에서 분리 작업했다. 기능·원장/실행 경계·기존 데이터는 보존한다.

## 변경과 검증 범위

- 어두운 탐색 rail + 중립색 작업 영역 + 단일 파란 행동색. 토큰·버튼/입력/상태/메뉴/SVG 규칙을 공통화.
- 큰 집중 카드 3개를 순서가 있는 집중 행으로 변경. 작업 목록은 우선순위·작업명·상태·담당 AI·마감의 일정한 열 구조, 모바일에서는 읽는 순서대로 재배치.
- 진행 링과 장식·중복 문구를 줄이고 AI 미연결/초안 저장과 실제 실행을 구분. 숫자와 상태색에는 읽을 수 있는 레이블이 함께 있다.
- 원본 Python backend/schema 변경 없음. 기존 record/task/run/approval 의미를 디자인으로 승격하지 않았다.
- Python HTTP/저장소 테스트 14/14, UI 상태 회귀 6/6, JavaScript 구문과 git diff 공백 검증 통과.
- 로컬 가상 DB의 실제 Chromium에서 새 입력·마감·집중 3개 상한·결과 등록·최신 버전 검토·인계·미저장 초안 보존 확인. 클립보드는 사용자 작업을 덮어쓰지 않도록 클릭하지 않았고 기존 동작 코드/새 복사 SVG만 확인.
- Today/전체/검토/AI 네 화면 × 320/390/768/1440px = 16조합에서 document-wide overflow 없음.
- 실제 계산된 텍스트색과 배경 기준 Today desktop 검사에서 최종 대비 미달 0. 전체 WCAG/VoiceOver/실기 iPhone 감사는 아님.
- Impeccable 기계 detector 1회 실행 후 실제 저해상도 텍스트는 보완. 어두운 rail의 배경을 흰색으로 가정한 정적 검사 오탐과 실제 계산 대비를 구분했다.
- 별도 Impeccable finish reviewer가 desktop 1440px와 mobile 390px full-page 및 상세 결과/인계 캡처를 열어 검토했다. 유일한 수정 요구는 상세 폼의 문자 아이콘을 공통 SVG로 교체하는 것. 반영 후 verdict pass에서 **resolved / disposition: ship**. 이 판정은 지정 수정 항목에 대한 판정이며 전체 제품 품질/보안 보장은 아니다.

설치·자동 인식·공식 source/commit은 [디자인 스킬 기록](DESIGN_SKILLS.md)에, 구현 규칙은 [DESIGN.md](../DESIGN.md)에 둔다. 캡처는 `.impeccable/review/` 로컬에만 보관하고 공개 GitHub에는 넣지 않는다. 새 인증/외부 공개/AI 실행 연결은 이번 수정 범위가 아니다.

## 실제 VPS 반영

- 배포 코드 release `92140ca`, archive SHA-256 `8f9b37f8f2c4fd4659a5ca908574a8006f0454a90bf279aa782a0d0ab92ee19f`; 전송 전후 일치.
- 원래 서비스 `haar-workspace-mvp`와 `/opt/haar-workspace-mvp-20261017/current`만 갱신했다. 원래 `11ce4e0` release는 남겨 롤백 가능하게 보존했다.
- 배포 전에 새 release와 기존 release의 `app/server.py` byte 동일성을 검사했다. 기존 DB를 보존하고 비공개 경로에 SQLite 일관된 백업·integrity_check를 수행했다.
- 서비스 재시작 경계에서 records/focus/commands/events 전체 정렬 내용 digest를 전후 비교해 동일했다. 초안 3개·집중 날짜 1개·명령 4개·이벤트 4개 유지. 실제 상품/고객/기존 대화 이관이나 seed 재실행 없음. 실제 브라우저 최종 검증은 조회만 수행했다.
- health `ok`, mode `intake_only`, dispatch=false. 새 release에서 service active/running, NRestarts=0, listen은 기존 `127.0.0.1:3310`만. OpenClaw active와 Buzz exited 상태 유지.
- 기존 SSH 경로 `http://127.0.0.1:3311`로 실제 VPS를 headless 검증: 네 화면 × 네 viewport 가로 넘침 없음, Today 실측 대비 미달 0, console error/warning 0. `output/playwright/vps-redesign-desktop.png`, `vps-redesign-mobile.png`를 로컬에서 직접 열어 내용 확인했다.
- 새 도메인·프록시·방화벽·인증/OAuth·공개 노출 변경 없음. 자동 실행·Buzz 채팅·Paperclip 원장과 iPhone 원격 인증 경로는 여전히 미연결이다.
