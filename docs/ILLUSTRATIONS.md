# 작업실 일러스트 적용·검증

2026-10-18. 사용자가 개선된 디자인을 보존하면서 화면 곳곳에 그림을 추가하도록 요청했다. 기존 작업 콘솔에 작은 종이 문구류 일러스트 4종을 연결했다. 도구는 내장 `image_gen.imagegen`; 각 이미지를 별도 호출로 생성했다. 외부 이미지 주소나 새 런타임 의존성은 없다.

## 화면과 파일

| 파일 (`app/static/illustrations/`) | 역할 | 표시 크기 desktop / mobile | 전송 크기 |
| --- | --- | --- | --- |
| `focus.webp` | 오늘 집중 제목 옆, 빈 계획 카드 세 장과 연필 | 80 / 64px | 11,642 bytes |
| `empty.webp` | 작업 목록이 비었을 때, 종이 inbox | 112 / 96px | 8,294 bytes |
| `review.webp` | 결과 검토 현황 제목과 검토 목록 빈 상태, 서류와 돋보기 | 52px 또는 112 / 96px | 9,950 bytes |
| `connection.webp` | AI 작업실 실행 경로 제목, 서로 떨어진 케이블 | 88 / 72px | 8,718 bytes |

합계 **38,604 bytes**. 원본 PNG의 alpha를 유지해 `cwebp -q 80 -alpha_q 100 -resize 320 320`으로 WebP를 만들었다. 원본을 변경하지 않고 별도 보관했다. `output/illustrations/*-original.png`, manifest와 화면 캡처는 로컬 검토용이며 Git에서 제외한다. 저장소에는 4개 WebP만 포함한다. 아래 프롬프트는 생성 재현의 근거이며 같은 픽셀 출력을 보장하지 않는다.

공통 스타일은 ivory/graphite/소량 cobalt의 무광 종이, 투명 배경, 간단한 한 개 오브젝트 그룹이다. 작업 행·메타데이터·버튼 밀도를 유지하고 이미지에 상태 의미를 맡기지 않는다. 모든 삽입 이미지는 `alt=""`, `aria-hidden="true"`, 명시적 width/height, 비상호작용이다. 첫 집중 이미지 외에는 lazy loading, 모두 async decoding을 사용한다. 이미지가 없어도 행동·상태·설명은 텍스트로 읽힌다.

## 실제 생성 프롬프트

각 호출은 다음 공통 프롬프트 뒤에 해당 Subject를 붙였다. `transparent_background=true`, 신규 이미지 생성이며 참조 이미지 없음.

```text
Use case: stylized-concept. Asset type: small decorative illustration for an operational shopping-work dashboard, displayed at 64–132 CSS pixels. Style: premium editorial stationery illustration, tactile matte folded paper, slight natural grain and precise dark graphite contours, subtly dimensional, restrained and calm, not a generic 3D clay emoji. Color palette: warm white/ivory, pale cool grey, graphite, a small cobalt blue #2855d9 accent only. Composition: one centered simple object group, fill about 70% of a square canvas, generous clear space, all objects fully inside frame, transparent alpha background, no backdrop or ground plane. Soft neutral diffuse light, tiny soft contact shadows only. No text, lettering, numbers, logo, watermark, people, robots, faces, stars, sparkles, arrows, checkmarks, green status lights or confetti.
```

**Focus**

```text
Subject: a small folded-paper desktop organizer with exactly three blank upright planning cards staggered in height, one cobalt divider tab, and a short graphite pencil resting beside the tray. It conveys choosing three priorities, not completing tasks.
```

**Empty**

```text
Subject: a beautifully folded low ivory paper inbox tray with a single blank loose card leaning gently against its rim, a small cobalt paper corner. The tray is mostly empty, inviting a new piece of work.
```

**Review**

```text
Subject: two blank ivory document sheets, one folded corner and subtle grey layout lines without readable writing, with a small graphite and cobalt magnifying glass above one sheet. It conveys looking carefully at a result, not approved or completed work.
```

**Connection**

```text
Subject: two ends of a simple short graphite cable, an ivory plug and a cobalt-edged socket hovering opposite each other with a clearly visible small gap. They are disconnected and waiting, with no electricity, motion, network waves or glowing indicator. Elegant physical worktool metaphor.
```

## 검증과 현재 반영 상태

- Python HTTP/저장소 테스트 14/14, UI 상태 회귀 6/6 통과. HTTP 테스트에서 4개 이미지의 200 응답·`image/webp`·RIFF 헤더와 미허용 파일/경로의 404를 확인했다.
- JavaScript 구문·diff 공백 검증 통과. WebP 네 파일의 alpha chunk를 확인했다.
- 격리된 가상 SQLite DB와 `127.0.0.1:3312`에서 실제 headless Chrome으로 Today/전체/검토/AI 네 화면 × 320/390/768/1440px 16조합 확인: 가로 넘침 0, 표시 이미지 로드 실패 0, 장식 alt 누락 0, 페이지 오류 0, HTTP 오류 0. 모든 조합에서 AI 실행 미연결 문구가 유지됐다.
- desktop/mobile 및 빈 목록·검토·AI 화면 캡처를 직접 열어 작은 크기의 조화·내용 가독성·기존 표 밀도를 검토했다. 실기 iPhone/VoiceOver 감사는 수행하지 않았다.
- 브라우저 harness의 offscreen lazy image decode 대기는 검사 시에만 eager로 전환하고 제한 시간을 두어 해결했다. 제품의 lazy loading 정책은 유지했다.
- 서버 변경은 네 파일의 정적 경로 허용 목록 추가뿐이다. DB/schema·작업/승인/실행 로직은 변경하지 않았다. 신규 release 반영 시 **HAAR 자체 서비스 재시작이 필요**하다. 예전 디자인 배포의 backend 동일성 주장을 이번 변경에 적용하면 안 된다.
- **이번 변경은 로컬 구현·검증 및 배포 준비까지다. 기존 VPS/3311의 실반영을 확인한 기록은 없다.** 배포한다면 기존 HAAR 경로·서비스만 사용하고 DB 보존·백업·health·이미지 MIME·모바일 확인 후 코드만 교체한다. 다른 봇/전원/방화벽/로그인 설정 변경은 범위가 아니다.

검토 자료: `output/illustrations/desktop.png`, `mobile.png`, `empty-desktop.png`, `review-desktop.png`, `agents-desktop.png`, `agents-mobile.png`, `browser-checks.json`, `assets-manifest.json`. 모두 가상 예시 데이터다. Library 전달용 파일은 별도 manifest로 준비하며 저장·업로드 성공과 구분한다.
