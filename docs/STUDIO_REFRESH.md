# 스튜디오 팔레트·메뉴 배너 변경

2026-10-18. 사용자가 기존 작은 그림은 보존하고 각 메뉴의 메인 배너에 적절한 그림을 추가하며, 관리자 페이지 같은 색상을 더 예쁜 패션·주얼리 작업공간으로 바꾸도록 요청했다.

## 디자인과 실제 제작

- 기존 네 메뉴 Today/모든 항목/결과 검토/AI 작업실의 화면 구조·작업 행 밀도를 보존하고 메뉴 제목·설명·새 작업 CTA 바로 아래에 전체 폭의 큰 독립 이미지 배너를 넣었다. 제목 옆 작은 삽화로 대체하지 않고 이미지 영역을 별도로 둔다.
- 아이보리 canvas, warm white card, pale rose sidebar, deep mulberry action/selection/focus를 공통 semantic token으로 쓴다. sidebar/card/button/badge/hover/focus/field/overlay까지 같은 토큰을 적용한다. 상태색은 오류·기한·검토 의미와 텍스트를 유지한다.
- 오늘은 계획 카드·주얼리 트레이, 전체는 폴더·소재 보관함, 검토는 돋보기·디자인 초안, AI는 분리된 두 작업 공간과 떨어진 케이블이다. 실제 판매 상품 사진이나 자동 실행 상태를 뜻하지 않는 장식 일러스트다.
- 내장 `image_gen.imagegen`을 서로 다른 프롬프트로 **총 4회(메뉴당 1회)** 호출했다. 투명 PNG 원본을 별도로 보존하고 `cwebp -q 80 -alpha_q 95 -resize 720 0`으로 720×480 WebP를 만들었다. 기존 작은 그림 네 파일은 SHA-256까지 그대로다.
- 신규 배너는 한 번에 현재 메뉴 한 개를 참조한다. 명시적 width/height, async decode, 장식용 빈 alt와 aria-hidden을 쓴다. 다른 메뉴 배너를 미리 전부 불러오지 않는다. 작은 보조 이미지의 lazy loading도 유지한다.

| 메뉴 | 배포 파일 | bytes |
| --- | --- | --- |
| today | `app/static/banners/today.webp` | 50,142 |
| all | `app/static/banners/all.webp` | 65,058 |
| review | `app/static/banners/review.webp` | 46,874 |
| agents | `app/static/banners/agents.webp` | 46,548 |

신규 네 배너 합계 **208,622 bytes**. 실제 생성 프롬프트는 각 WebP 옆 `.webp.json`에 원문으로 보관한다. Impeccable embed-prompt의 WebP sidecar fallback이며 생성 프롬프트 검사에서 4 rasters / 0 missing을 확인했다. 원본 PNG·generation-record·캡처는 로컬 `output/studio-refresh/`로 보존하며 공개 Git에 넣지 않는다.

## 실제 읽고 적용한 스킬

UIUX Pro Max SKILL.md와 Impeccable SKILL.md/colorize/craft-floor/완료 리뷰 지침을 읽었다. UIUX Pro Max의 design-system 검색 후 색상 범위를 좁힌 `fashion jewelry light --domain color`에서 Wardrobe & Outfit Planner / Fashion rose + gold를 확인했다. 패션 색상 방향·semantic roles·대비/44px 가이드를 참고하되, 마케팅 landing 패턴·sticky 전환 CTA·Fira 기술 폰트는 작업실에 맞지 않아 적용하지 않았다. 색상값은 위 사용 맥락에 맞춰 직접 조정하고 실제 계산 대비로 검증했다.

기존 세션의 Impeccable context는 반복 실행하지 않았다. code-led 배너 확장·사용자 승인된 공통 팔레트 변경이며 외부 디자인 서비스 로그인, roll/decision page, 승인된 comp를 사용했다고 주장하지 않는다.

## 구현 경계와 검증

backend 변경은 네 `/banners/{today,all,review,agents}.webp` 정적 허용 경로를 등록하는 2줄뿐이다. DB/schema·명령·승인·실행 로직은 변경하지 않았다. 경로 전체를 임의로 공개하는 directory serving을 추가하지 않았다.

- Python HTTP/저장소 14/14, Node UI 상태 회귀 6/6, JavaScript 구문·diff 공백 검사 통과. 8개 이미지의 MIME/RIFF 및 banner 경로 이탈·미허용 파일 404 확인.
- 이전 분할 헤더 초안은 격리 가상 DB Chrome에서 네 메뉴 × 320/375/390/768/1024/1280/1440px = **28조합**을 확인했다. 이 수치를 최신 독립 배너 검증으로 재사용하지 않는다. 최신 배치는 지원 Orca CLI를 우선 시도한 후 비활성 탭 캡처 한계 때문에 격리 Chrome 한 개에서 직렬 검증했으며 아래 최종 기록을 기준으로 한다. 이전 초안 검사 결과: 가로 넘침·배너/CTA 또는 copy/image 영역 겹침·이미지 로드·장식 alt·page/HTTP 오류 0. 모든 메뉴에서 미연결 문구 유지.
- 화면·모달의 실제 계산 foreground/background 및 placeholder 대비 검사에서 미달 0. 전체 WCAG/VoiceOver 실기 감사는 아니다.
- 최신 요청에 맞춘 독립 배너 높이는 PC 240–340px, 모바일 210px다. 기존 720×480 이미지를 전체 폭 배너 가운데 contain으로 크게 배치하고 투명 여백만 1.08배 확장한다. 제목·CTA는 배너 위 별도 영역이므로 가리지 않는다. 새 이미지 생성이나 동시 빌드를 반복하지 않았다. 메뉴 선택은 텍스트/배경색의 역전 transition 중 순간 대비가 낮아지지 않도록 즉시 전환한다. 다른 hover와 focus 토큰은 유지한다.
- 실제 키보드 Tab의 3px solid mulberry focus, 844×390 landscape의 가로 넘침 없음, 모바일 모달의 스크롤·저장 CTA·Escape 닫힘을 확인했다. 모달 하단의 엄격한 위치 검사는 94dvh의 소수점과 정수 scroll 차이 0.390625 CSS px를 실패로 봤으며, viewport 캡처와 실제 저장으로 사용 가능함을 확인했다. 이 측정 오탐 때문에 제품 CSS를 바꾸지 않았다.
- 새 초안을 가상 DB에서 실제 UI로 저장해 동작을 확인했다. production DB에는 테스트 쓰기를 하지 않았다. 독립 디자인 리뷰·배포 상태는 완료 후 별도 기록한다.

## 현재 반영 상태

사용자의 실제 3311 배포·HAAR 전용 재시작 명시 승인으로 **2026-10-18 05:29 UTC 기준 코드 `24181b3bd83e4ad6f394f54bd5e0883082908835`가 실제 반영**되어 있다. 이전 `b925313`은 코드 롤백용으로 보존했다. 이 문서의 후속 영수증 커밋과 실행 중 코드 커밋을 구분한다.

## 재개한 독립 배너 검증

Mac 성능 회복을 위한 중단 후 사용자가 전체 메뉴의 큰 배너·팔레트·실제3311 반영을 다시 명시 요청해 재개했다. 지원 Orca CLI 전용 탭 하나와 가상 서버 한 개만 사용하며 직렬로 확인했다. 비활성 탭의 compositor 캡처에서 일부 그림이 비어 보여 해당 캡처를 증거로 쓰지 않았다. 격리 Chrome 하나에서 이미지 decode + 두 paint frame 뒤 직렬 재캡처하고 브라우저를 즉시 닫았다. 1440/390/320/768px × 네 메뉴 = 16조합, 캡처 9장(메뉴별 PC/모바일 8장과 모달 1장), 가로 넘침·이미지/CTA 겹침·검사 대비 미달·page/HTTP 오류 모두 0이다. 원본/제품 이미지를 편집해 가짜 화면을 만들지 않았다.

최종 PC/모바일 캡처와 검사 영수증은 `output/studio-refresh/resumed/`에 보관한다. 데이터 입력이나 실제 작업 상태 변경 없이 화면 전환만 확인한다. 최종 독립 리뷰와 실제 배포 상태는 아래에 이어 기록한다.

## 독립 검토 후 보정

신규 전체 검토에서 배너 크기·메뉴별 그림·팔레트·기존 작은 이미지와 초안/미연결 표시는 요구에 맞는 것으로 확인했다. 두 지적은 헤더 CTA의 데스크톱 40px/설계 44px 차이와 구 디자인 문서 잔존이었다. 헤더 버튼만 모든 크기에서 최소 44px로 맞추고 동일 16조합·9캡처를 직렬 재검증했다. 실제 CTA 높이 44px, 겹침·넘침·검사 대비 미달·브라우저 오류 0이며 사용한 격리 브라우저는 종료했다. 새 디자인 문서와 최종 판정은 아래 기록을 따른다.

최종 독립 판정은 `ship`이다. 이는 최초 전체 검토 후 위 두 수정 항목을 다시 채점한 범위이며, 두 항목 모두 resolved로 확인했다. `DESIGN.md`와 `.impeccable/design.json`은 실제 CSS 35개 색상값·메뉴 배너·반응형·hover/focus·초안/미연결 사실과 일치하도록 갱신했다. 리뷰·검사 로그는 로컬 output에 보존한다.

## 실제 배포·데이터 보존 영수증

- 배포 archive: 377,340 bytes, SHA-256 `99ed0653b1e92569d16ff2a7d30275d69b02f3c90f10bb529d290e679d2ca77b`. 전송 전후 해시 일치. 안전한 상대 경로의 일반 파일/디렉터리만 포함하며 DB·runtime output·비밀정보는 포함하지 않았다.
- HAAR 중지 전 archive의 server.py에서 검토한 배너 정적 등록 2줄을 정확히 한 번 제거하면 이전 코드와 바이트 일치. 나머지 app Python 파일과 backup.py도 동일하다. 서버에서 14개 테스트를 먼저 통과했다.
- 재시작 대상은 `haar-workspace-mvp` 하나다. 중지 상태에서 일관 백업 `studio-backup-24181b3.sqlite3`을 새 파일로 만들었고 integrity/foreign-key 검사 및 원본과 백업의 schema/user_version/네 테이블 데이터 digest가 일치했다. 재시작 전후 digest도 동일했다. 행 수는 records=3, focus=1, commands=4, events=4로 보존됐다.
- unit 파일과 자원 제한·격리 설정을 유지했다. DynamicUser=yes, ProtectSystem=strict, ProtectHome=yes, MemoryMax=128MiB, TasksMax=32, NRestarts=0. 기존 127.0.0.1:3310 listen과 Mac 3311 SSH 터널은 유지했다. 타서비스·서버 전원·권한·방화벽·인증 설정 변경은 없다.
- health는 `status=ok`, `mode=intake_only`, `dispatch_enabled=false`. 다섯 adapter는 미연결이며 새 자동 실행이나 외부 게시를 하지 않는다.
- 기존 3311 경로에서 이미지 8개의 MIME·해시가 로컬 파일과 일치했다. 같은 origin GET만 허용한 브라우저 하나로 네 메뉴 × 1440/390/320/768px = 16조합을 확인했다. 모두 CTA44px, 큰 배너가 헤더 아래 표시, 가로 넘침·겹침·검사 대비 미달·page/HTTP 오류 0. 실제 메뉴별 PC/모바일 8장과 모달 1장을 열어 확인했다. 물리 iPhone 실기는 아니다.
- 검증 브라우저는 즉시 종료했고, 작업용 로컬 3313 서버와 이번에 만든 Orca 미리보기 탭만 닫았다. 기존 사용자 탭·Orca 앱·3311 터널은 유지했다. 새 이미지 생성/빌드 반복 없이 기존 네 배너를 재사용했다.
- 원본·실제 화면 캡처와 상세 배포/검증 JSONL은 공개 Git에 넣지 않고 로컬 `output/studio-refresh/`에 보존했다.

## Library 전달 상태

실제 3311 PC/모바일 캡처 8장과 새 배너 원본 묶음을 한 배치로 저장하려 했지만, 저장 준비 기능을 사용할 수 없다는 오류로 시작 단계에서 중단됐다. 새 파일 생성·Library ID 발급은 없으며 저장 성공을 주장하지 않는다. 파일은 로컬에 보존했고, 시작한 저장 경로를 임의로 우회하거나 중복 생성하지 않았다. 이 전달 단계만 미완료다.
