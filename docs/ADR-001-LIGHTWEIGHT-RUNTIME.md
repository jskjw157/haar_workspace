# ADR-001: 경량 중앙 VPS와 Rust 적용 판단

날짜: 2026-10-16 / 상태: 제안·측정 대기. 구현·배포·벤치마크를 실행한 기록이 아니다.

## 확정된 제약

중앙 VPS는 화면·기록·지시 전달을 맡고 이미지·영상·브라우저 연산은 실행 노드가 처리한다. Paperclip의 실제 배정·상태·실행기록 로직은 분석해 재사용하고, Buzz는 우리 화면에서 선택한 AI와 지시·결과를 주고받는 대화 계층으로 활용한다. 다섯 경로 adapter 개발은 제품 범위다. 전체 구현 언어는 미확정이다.

## Rust에 대한 판단

Rust는 소유권을 컴파일 시 검사하는 메모리 관리 방식을 사용하므로 경량 상주 adapter의 후보가 될 수 있다. 그러나 이것만으로 HAAR 전체의 메모리 사용량이 적다고 확정할 수 없다. DB·relay·큐·캐시와 자식 런타임·브라우저까지 포함한 측정이 필요하다. [Rust 공식 소유권 설명](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)을 근거로 한 기술 판단이며 현재의 성능 실측 결과가 아니다.

Paperclip은 Node.js·TypeScript/React 계열이고 Buzz는 Rust workspace와 웹 클라이언트 등으로 구성된다. [Paperclip README](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/README.md), [package.json](https://github.com/PaperclipAI/paperclip/blob/b294abb9eb96c33048b4f53a2a037e04886b7407/package.json), [Buzz Cargo.toml](https://github.com/block/buzz/blob/93ffc37cbdb7ced6a07eca11744931cdffb82e20/Cargo.toml)에서 재사용할 코드·런타임을 확인한다. Rust를 선택해도 Paperclip의 Node 프로세스나 저장소 의존성이 자동으로 사라지는 것은 아니다.

| 대안 [제안] | 재사용·운영 비용 | 결정할 증거 |
| --- | --- | --- |
| 기존 언어·런타임을 유지하고 bridge 최소화 | Paperclip/Buzz 원래 로직을 보존하기 쉬움; 두 런타임·서비스의 상주 비용 존재 | 최소 구성의 idle/일상/최대 동시 부하와 총 메모리 |
| 큐 수신·heartbeat·journal 담당 경량 adapter만 Rust로 작성 | 중앙 로직 재작성 없이 상주 프로세스 최적화 후보; 빌드·배포·프로토콜·OS 통합 비용 추가 | 동일 계약의 기존 언어 adapter 대비 peak·안정성·개발/유지 비용 |
| 중앙까지 Rust로 재작성 | 배정·상태·승인·복구 로직 재구현과 upstream 호환·회귀 부담이 큼 | 기존 재사용 구성이 예산을 충족하지 못하고 재작성 이득이 비용을 상회한다는 근거 |

권고는 기존 로직 재사용과 무거운 연산 분리를 먼저 검증하고, adapter에서 실익이 확인될 때 Rust를 선택하는 것이다. 전체 Rust 재작성은 현재 채택 결정이 아니다.

## 측정·예산·동시성 관문 [제안]

- 같은 하드웨어/OS·데이터·작업·시간 구간에서 idle, 일상 부하, 전역 1개·노드별 1개 무거운 작업, 재연결 burst를 비교한다. 실행 슬롯과 중앙의 전달·heartbeat 경로는 분리한다.
- 중앙/DB/relay/캐시와 기존 서비스, 각 adapter·자식 프로세스를 빠짐없이 집계한다. RSS/PSS(환경이 지원하는 항목), peak·CPU·swap/OOM·큐 대기·p95 응답을 기록하고 공유 메모리 중복 집계 방식을 명시한다.
- `상주 중앙·의존성 peak + 같은 호스트 실행기 peak 합계 + OS·기존 서비스 예약 + 안전 여유 ≤ 실제 RAM`을 만족하는 예산표를 만든다. 실제 용량·각 항목 MiB·안전 여유·유한한 연결/DB pool/로그 버퍼 상한은 아직 미측정이며 운영 전 확정한다.
- 예산이 부족하면 큐에 대기시키고 무거운 작업을 중앙에서 대신 실행하지 않는다. 재연결 후에도 슬롯/메모리 예약을 확인해 시작한다. 기존 VPS의 Hermes·OpenCode가 중앙과 같은 호스트라면 합산한다.
- 중앙의 이미지 생성·변환/영상 인코딩/headless 브라우저 실행 수는 0, 동일 호스트 포함 전체 구성은 합의 예산 이내, 큐 적체 중에도 지시 접수·취소·결과 수신이 가능해야 한다. 실제 검증은 [AC-23~24](ACCEPTANCE_CRITERIA.md)에 남긴다.

결정 책임은 구현·운영 담당과 운영자에게 있다. M0에서 실제 코드 재사용 경계와 측정 결과·예산·유지보수 비용을 비교한 뒤 선택/보류 사유를 이 ADR에 추가한다. 이번 문서 보강은 측정 환경 설치나 운영 서버 변경을 승인·실행하는 것이 아니다.
