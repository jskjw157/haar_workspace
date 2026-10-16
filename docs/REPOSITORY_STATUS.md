# 저장소 초기 상태·문서 검증 기록

기준일: 2026-10-16 UTC. 대상: [jskjw157/haar_workspace](https://github.com/jskjw157/haar_workspace).

## 1. 변경 전 확인

| 항목 | 확인 결과 | 근거 |
| --- | --- | --- |
| visibility | Public | GitHub repository metadata와 `gh repo view`에서 일치 |
| 기존 커밋·브랜치 | 빈 저장소, 기존 브랜치 없음 | `isEmpty=true`, `defaultBranchRef.name` 빈 값, branch 검색 결과 없음 |
| API 기본 브랜치 이름 | `main` 메타데이터는 있으나 실제 ref 없음 | repository metadata와 실제 branch 목록 구별 |
| 기존 파일 | 없음 | contents API가 `This repository is empty` 404 반환 |
| repo의 AGENTS.md / .agents/skills / PR 템플릿 | 빈 저장소이므로 없음 | 파일·브랜치 부재 확인. 외부 소스 지침과 구분 |
| 읽기·쓰기 권한 | 조회·push 가능 권한 확인 | 인증된 GitHub connector repository permissions |

기존 자료는 없었으며 삭제·덮어쓰기·visibility 변경·force push를 하지 않았다. 새 저장소에 라이선스를 임의 지정하지 않았다. 공개 저장소에 적합한 설계·가상 예시만 작성했다.

## 2. 초기화와 PR 비교 기준

빈 저장소에서는 비교 기준 브랜치가 없어 일반 PR을 만들 수 없으므로 다음 방식을 선택했다.

1. `main`에 저장소 목적·문서화 단계·SELLAYER 별도 프로젝트만 담은 최소 README 초기 커밋을 생성했다.
2. 초기 커밋 [`49aa848b32a0e9caf4610262b3ec71bc800d4f96`](https://github.com/jskjw157/haar_workspace/commit/49aa848b32a0e9caf4610262b3ec71bc800d4f96)을 로컬로 가져왔다.
3. `docs/haar-ai-platform-prd-20261016` 브랜치에서 README를 확장하고 `docs/` 문서를 추가했다.
4. 상세 문서는 위 기준 커밋을 대상으로 Draft PR에서 검토한다. 자동 병합·merge·운영 배포는 수행하지 않는다.

초기 `main` 커밋은 PR 기준 마련을 위한 문서 초기화다. 상세 PRD가 이미 기본 브랜치에 승인·반영되었다는 뜻이 아니다.

## 3. 문서 검증 범위

문서 검증은 UTF-8 파일·상대 링크·로컬 제목 앵커·JSON 예시·Markdown fence·공백 오류·변경 파일 범위·비밀 패턴과 요구사항 정합성을 확인한다. Mermaid는 소스 구조와 상태·책임 경계를 점검한다. 브라우저 렌더링과 실제 앱 동작 시험은 별도이며 실행하지 않은 결과를 통과로 기록하지 않는다.

2026-10-16 핵심 6종 설계 문서 보강 후 다시 수행한 문서 검증 결과:

| 점검 | 결과 |
| --- | --- |
| 문서 파일 범위 | README 1개와 docs 문서 11개, 핵심 6종과 상세 계약/근거 5종으로 연결, Markdown 파일만 변경 |
| 링크·문법 구조 | 링크 96개를 분류·점검하고 상대 파일/제목 앵커 모두 해소, JSON 예시 4개 파싱 성공, fence 짝 일치 |
| 공식 출처 재현성 | Paperclip/Buzz 고정 커밋의 서로 다른 출처 파일 22개를 GitHub tree와 대조, 모두 존재. CR-01~07 코드 경로 일부를 읽기 전용 조사 |
| Git 공백·충돌 | staged diff의 `git diff --cached --check` 통과, 충돌 표식 없음 |
| 비밀·공개 적합성 | 주요 token/private key/실제 Drive 링크/IP 패턴 검사에서 발견 없음; 가상 예시·범위 문구 확인 |
| 요구사항 정합성 | R-01~12 모두 설계/화면·계약과 AC-01~25에 연결, 모든 AC가 최소 한 요구에 추적됨. 권한·상태·VPS 자원 경계·미확인 API와 사용자 선택지 교차 검토 |
| 미실행 검증 | 앱·실서비스·배포·외부 쓰기 테스트 및 Mermaid 브라우저 렌더링은 수행하지 않음 |

보강은 기존 PR의 추가 문서 커밋으로 진행한다. DIR 봇·Orca·GPT 호출 계약과 OpenClaw 사용 여부는 미확인이며, VPS 메모리 예산·동시성·언어 선택은 측정 전 제안이다. 실제 코드 일부의 정적 조사만 수행했고 adapter 구현·벤치마크·서버 변경은 시작하지 않았다. 화면/주요 기술 선택지는 사용자가 확정할 제안으로 남겼다.

최종 전달 시 원격 브랜치 HEAD와 로컬 커밋 일치, PR base/head·Draft 상태·변경 파일을 다시 조회한다. 커밋·PR의 실제 링크와 최종 검증 결과는 PR 설명과 전달 메시지에서 확인할 수 있다.

## 4. 범위 밖·미검증

- 구현 코드·서비스 실행·CI 앱 테스트·배포 작업 없음.
- 기존 VPS의 Paperclip 설치·실행 여부·포트·DB·backup 상태 미검증.
- VPS Hermes·OpenCode, Mac의 이름 미확인 DIR 봇·Orca, GPT의 실제 연결·호출 방식 미검증. 이전 초안의 OpenClaw 사용 단정은 정정했으며 실제 사용 여부는 확인 필요.
- Apple Passwords 접근·Mac Keychain helper 구현·비밀 CSV 읽기/이관 없음.
- 실게시·댓글 답글·CS 발송·광고 예산 변경·메시지 발송 없음.

제품 시험은 [수용기준](ACCEPTANCE_CRITERIA.md)에 향후 검증 계획으로 정의했다. 구현 전 확인할 선택과 책임은 [PRD 미결정 사항](PRD.md#14-미결정-사항과-확인-책임)에 남겨두었다.
