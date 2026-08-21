# voxplan

여러 도서의 낭독/녹음 일정을 성대 부하 상한과 도서별 마감에 맞춰 최적 배분하고, 검증 후 UI로 발행하는 프로젝트.

## 하네스: 낭독 녹음 일정 스케줄링

**목표:** 하루 페이지 상한(성대 보호)과 도서별 마감을 동시에 만족하면서, 하루에 여러 도서를 섞어 단조로움을 줄인 실행 가능한 녹음 일정을 만들고, 실제 실적을 추적해 미달분을 주말 완충으로 흡수한다.

**트리거:** 녹음/낭독 일정 배분·검증·실적 추적·UI 관련 작업 요청 시 `recording-schedule-orchestrator` 스킬을 사용하라. 단순 질문(요일 확인, 특정 날짜 조회 등)은 직접 응답 가능.

**배포:** 두 곳을 함께 유지한다 — 변경 시 양쪽 모두 반영할 것.
- GitHub Pages: https://yki1204.github.io/voxplan/ (`main` 브랜치 루트, push 시 자동 배포)
- Claude 아티팩트: https://claude.ai/code/artifact/af7bf90c-9247-4d33-8678-acce3a3d8c5d
  (새 대화에서 갱신할 때는 이 URL을 `Artifact` 도구의 `url` 로 넘겨야 같은 링크가 유지된다)

**실적 데이터:** 브라우저 `localStorage` 키 `voxplan.checkins.v1`. 레포·서버에 없고
읽을 수 없으므로, 진도 분석이 필요하면 사용자에게 값을 요청한다.

**변경 이력:** (위에서 아래로 시간순)
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-08-21 | 초기 구성 (에이전트 4 / 스킬 5) | 전체 | - |
| 2026-08-21 | 레바논의 시내 470p·2달로 변경, 종료일 10/02 재산정 | _workspace/*, index.html | 사용자 범위 변경 요청 |
| 2026-08-21 | 일별 실적 체크인 + 주말 이월 + 진행률 기능 추가 (에이전트 5 / 스킬 6) | skills/daily-progress-tracking, agents/progress-analyst, skills/recording-schedule-orchestrator(Phase 6 신설), index.html | 실적 대비 진도 추적 요청 — 미달 시 전체 재배분 대신 주말 잔여로 흡수 |
| 2026-08-21 | 저장을 localStorage 단독으로 단순화 (아티팩트 런타임·내보내기/가져오기 제거, 즉시 저장) | index.html, skills/daily-progress-tracking, README.md | GitHub Pages 정적 배포 전제 |
| 2026-08-21 | 제목 변경: 낭독 녹음 배차표 → 녹음 일정 스케줄 | index.html, README.md | 사용자 요청 |
| 2026-08-21 | 주말 보충 칸 버그 수정: 정산 대상 판정에 실적 유무 반영, 배정/잔여 분리 | index.html, skills/daily-progress-tracking | 시작일 전 입력 시 주말 칸이 '예정'에 머물고, 보충 입력이 잔여에 반영되지 않음 |
| 2026-08-21 | GitHub 공개 레포 초기 push + Pages 배포 | 전체 | 정적 호스팅 공개 |
| 2026-08-21 | 숨겨둔 쿠폰 3종(커피/아이스크림/곱창) 추가 | index.html, skills/daily-progress-tracking | 마일스톤 보상 |
| 2026-08-21 | 쿠폰 임계값을 주차 계획 누적으로 변경 (커피 2주차·아이스크림 4주차) | index.html, skills/daily-progress-tracking | 1p 문턱이 테스트 중 즉시 소진됨 |
| 2026-08-21 | 분할 세션일 실적 유실 버그 수정 (입력란을 도서 단위로 통합) | index.html, skills/daily-progress-tracking | 같은 도서 입력란이 2개여서 뒤 값이 앞을 덮음 — 9/25 19p·W6 각 18p가 주말로 오이월 |
| 2026-08-21 | 문서 drift 정정: 실적 입력원을 localStorage 로 통일, 변경 이력 시간순 정렬 | agents/progress-analyst, skills/recording-schedule-orchestrator, CLAUDE.md, README.md | 존재하지 않는 data/checkins.json 을 가리키고 있었음 |
