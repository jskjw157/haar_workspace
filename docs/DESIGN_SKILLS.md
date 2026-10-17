# 디자인 스킬 조사·설치 기록

2026-10-17 UTC. 사용자 요청으로 공식 소스만 읽고 두 스킬을 설치했다. 별 수는 조회 시점 값이며 품질/보안 보장이 아니다. 스킬 저장소 자체 수치이며 관련 서비스·본체 저장소와 합산하지 않는다.

| 후보 | 별 수 | 라이선스·실제 구성 | 이 작업에서의 선택 |
| --- | ---: | --- | --- |
| [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 136,585 | MIT. SKILL.md + 로컬 CSV와 Python BM25 검색/디자인 시스템 생성. Python 검색은 표준 라이브러리, 외부 모델 로그인 불필요. `--persist`는 지정 출력 경로에 문서를 쓰고 기존 MASTER는 기본 보존 | 설치. 색·규칙 후보 검색과 접근성/밀도 점검에 사용 |
| [Impeccable](https://github.com/pbakaus/impeccable) | 82,020 | Apache-2.0 + NOTICE. SKILL/references, 네이티브 엔진 런처. 첫 실행 시 공식 GitHub release에서 버전 고정 binary와 sha256 sidecar를 받고 일치해야 실행. 특정 concept roll 명령은 외부 API 사용, installer는 자동 hook 기능도 제공 | 설치. Operate·craft floor·재설계·렌더 리뷰에 사용. 자동 hook/외부 concept roll/로그인은 사용하지 않음 |
| [Superdesign skill](https://github.com/superdesigndev/superdesign-skill) | 815 | MIT. 로컬 플러그인 SKILL과 init/생성 가이드 실제 읽음. 캔버스 생성은 별도 CLI와 외부 서비스 로그인에 의존 | 플러그인 문서는 있었지만 CLI는 없었음. 이번에 새 설치/로그인/캔버스 생성하지 않음 |

## 설치 범위·버전

먼저 현재 Mac 작업 폴더 상위 `.agents/skills/`에 프로젝트 범위로 설치했다. 파일·명령은 동작했지만 새 검토 세션의 자동 스킬 카탈로그에서도 두 이름이 잡히지 않아, 사용자 설치 요청의 인식 조건을 위해 표준 개인 경로 `~/.codex/skills/ui-ux-pro-max`와 `~/.codex/skills/impeccable`로 이동·등록했다. 기존 동일 이름 경로가 없음을 확인했고 프로젝트 경로는 같은 설치를 가리키는 호환 symlink로 유지했다. 두 위치 모두 Git 저장소 밖이며 앱 archive에 포함되지 않는다. 기존 전역 skill, 프로젝트 파일, provider hook/config를 덮어쓰지 않았다. Codex 기본 skill-installer의 `--dest`, `--method git`, 고정 `--ref`를 사용했으며 installer의 기존 경로 충돌/심볼릭 링크/경로 검사를 유지했다.

- `ui-ux-pro-max`: `nextlevelbuilder/ui-ux-pro-max-skill` 커밋 `56ea9cf174ed86786187daa9de0e6247cb0747e4`, source path `.claude/skills/ui-ux-pro-max`. 75 files(추가 LICENSE/설치 manifest 포함).
- `impeccable`: `pbakaus/impeccable` 커밋 `6af45ac9a5eb8792f033d3242f52e99812fd91fa`, source path `.agents/skills/impeccable`. skill 4.6.0, engine 0.1.15. 65 files(추가 LICENSE/NOTICE/설치 manifest 포함).
- 각 설치 폴더에 `HAAR_INSTALL.json`, 원본 LICENSE와 존재하는 NOTICE를 보관했다. upstream 파일 내용은 수정하지 않았다.
- 엔진은 작업 폴더 `.cache/impeccable/bin/0.1.15/impeccable`에만 보관. SHA-256 `c7914209b4490dc81b7ab17c20f1f76415d1f0b8bb5de6f7e86e9aa111d1c1a5`. 공식 런처의 sidecar 검증을 통과했고 `engine-probe`가 `impeccable-engine 0.1.15`를 반환했다.
- `DO_NOT_TRACK=1`, `IMPECCABLE_NO_TELEMETRY=1`과 프로젝트 `telemetry:false`를 사용했다. 새로운 인증/OAuth, 모델 키, provider hook을 만들지 않았다.

## 인식·실행 확인과 사용법

두 SKILL.md의 name/description과 실제 참조 파일·검색 데이터·실행기가 존재함을 확인했다. 현재 AI가 두 지침을 직접 읽고 명령을 실행했다. Pro Max 검색과 Impeccable `context`/`engine-probe`/`detect`가 동작했다. 설치한 턴의 사전 로드 카탈로그는 즉시 갱신되지 않았지만, 다음 턴의 `skills.list`에서 `ui-ux-pro-max`와 `impeccable`이 모두 표준 개인 경로 package로 자동 인식되는 것을 확인했다. `$ui-ux-pro-max`, `$impeccable` 또는 `/skills`로 사용할 수 있다. 파일 설치·명령 동작·다음 턴 자동 목록 반영을 각각 확인했다.

이 저장소 작업 디렉터리에서(상위 task 폴더에 설치된 현재 구조):

```sh
python3 ../.agents/skills/ui-ux-pro-max/scripts/search.py 'internal SaaS operations dashboard' --design-system --variance 3 --density 8 -p 'HAAR Workspace'
DO_NOT_TRACK=1 IMPECCABLE_NO_TELEMETRY=1 IMPECCABLE_HOME=../.cache/impeccable ../.agents/skills/impeccable/scripts/impeccable context --target app/static/index.html
```

다른 clone에는 자동 설치되지 않는다. 별도 환경에 설치할 때는 위 공식 repo/commit과 path를 사용하고 대상의 기존 skill/hook부터 확인한다. 자동 hook을 원한다면 Codex의 별도 hook 승인 경계가 있으므로 이 설치와 혼동하지 않는다.

## 적용 결과와 제외한 추천

Pro Max 디자인 시스템 검색을 실행하고 첫 `task management dashboard`의 교육용 palette·학술 serif·홍보 페이지 패턴이 맞지 않아 `internal SaaS operations dashboard`로 한 번 좁혀 재검색했다. 재검색의 고대비 중립색/파랑·명확한 위계·동작 제한·밀도 기준을 채택했다. 남은 마케팅 hero/CTA 반복·영문 display font는 업무 콘솔과 한국어에 맞지 않아 채택하지 않았다. 검색 출력을 통째로 제품 디자인 시스템으로 저장하지 않았다.

Impeccable은 current context를 실제 로드한 뒤 기존 PRD/사용자 합의를 PRODUCT.md에 정리했다. 사용자 지시대로 추가 스타일 인터뷰와 외부 서비스/decision page 없이 code-led 운영 화면으로 진행했다. 따라서 외부 concept roll이나 Superdesign canvas workflow를 완료했다고 주장하지 않는다. `reference/operate.md`, `new-work.md`, `craft-floor.md`와 문서화 가이드를 읽고 평면 작업 행·동일한 SVG/버튼/상태·읽기 순서·대비·반응형을 구현했다. 기계 detector 1회와 독립 렌더 리뷰는 미학 보장이나 전체 접근성 감사가 아니다.

앱의 실제 기준은 `DESIGN.md`, `PRODUCT.md`, `.impeccable/surfaces/workspace.md`에 둔다. 설치된 스킬 코드 자체를 앱 런타임이나 서버 데이터 처리에 넣지 않는다.
