# voxplan

**→ https://yki1204.github.io/voxplan/**

여러 도서의 낭독/녹음 일정을 **성대 부하 상한**과 **도서별 마감**에 맞춰 최적 배분하고,
검증한 뒤 **실적 추적 UI**로 발행하는 스케줄링 하네스.

계획은 고정하고, 일별 미달분은 그 주 **주말 보충 칸**으로 격리한다 — 하루 미달마다 전체를
다시 짜면 주간 리듬·마감 구간·부하 평준화가 모두 깨지기 때문이다.

## 현재 계획

| 도서 | 분량 | 마감 | 계획 완료 |
|------|------|------|-----------|
| 고전 유튜브 | 주 1일 전일 녹음 | — | 매주 월요일 (6회) |
| 자율 전공책 | 150p | 2026-09-04 (2주) | 09-03 녹음 완료 · 09-04 편집 |
| 성경 스토리텔링 | 200p | 2026-09-24 (1달) | 09-23 녹음 완료 · 09-24 편집 |
| 레바논의 시내 | 470p | 2026-10-23 (2달) | 10-02 (평일 15일 버퍼) |

기간 **2026-08-24 → 10-02** · 평일 30일 · 녹음 22일 · 총 820p · 일평균 37.3p · 상한 40p

## 구조

```
index.html                       발행 UI (주간 일정 + 실적 체크인 + 진행률)
CLAUDE.md                        하네스 포인터 + 변경 이력
_workspace/
  01_constraint-analyst_constraints.json   정규화된 제약 (검증의 정답지)
  02_optimizer_schedule.json               일자별 배분
  03_validator_report.md                   검증 리포트
  build_ui.py                              JSON → index.html
  ui_plan.py                               계획 JSON → UI 소비용 PLAN
  ui_app.js                                트래커 런타임 (체크인·이월·진행률·localStorage)
  test_tracker.js                          이월/진행률 산출 시나리오 테스트
.claude/agents/                  constraint-analyst · schedule-optimizer
                                 schedule-validator · schedule-ui-builder
                                 progress-analyst
.claude/skills/                  recording-schedule-orchestrator (오케스트레이터)
                                 recording-constraint-modeling · vocal-load-scheduling
                                 schedule-validation (+ scripts/) · schedule-ui-rendering
                                 daily-progress-tracking
```

## 사용

일정 변경은 대화로 요청하면 오케스트레이터가 제약 재계산 → 재배분 → 재검증 → 같은 URL 재발행까지 처리한다.
수동 실행:

```bash
python3 .claude/skills/schedule-validation/scripts/validate_schedule.py \
  _workspace/01_constraint-analyst_constraints.json \
  _workspace/02_optimizer_schedule.json      # 종료코드 0 = 전부 통과

python3 _workspace/build_ui.py               # index.html 재생성

# 이월/진행률 계산 검증 (실제 ui_app.js 를 가짜 DOM 위에서 실행)
FAKE_TODAY=2026-08-29 ACTUALS='{"2026-08-25":{"major-book":15,"lebanon":15}}' \
  node _workspace/test_tracker.js
```

## 저장

실적은 브라우저 **localStorage** 에만 저장된다. 입력하는 즉시 동기 기록되므로
"아직 저장 안 된 몇 초"가 없다. 서버·백엔드가 없으므로 GitHub Pages 정적 호스팅에
그대로 올려도 동작한다.

| 상황 | 데이터 |
|------|--------|
| 새로 고침 / 탭 닫기 / 브라우저 재시작 | 유지 |
| `index.html` 재배포 (같은 도메인·경로) | 유지 |
| 다른 기기 · 다른 브라우저 | 각자 별도 (공유 안 됨) |
| 시크릿 창을 닫은 뒤 | 삭제 |
| 브라우저에서 사이트 데이터 삭제 | 삭제 |

저장 키는 `voxplan.checkins.v1` 이고 origin 단위로 격리된다. 저장이 막힌 환경에서는
상태칩이 **저장 불가** 로 바뀐다 — 조용히 잃는 것보다 알고 쓰는 편이 낫다.

파생값(진행률·주말잔여·이월)은 저장하지 않고 매번 다시 계산한다. 계획이 바뀌면
옛 파생값은 틀리기 때문이다.

## 실적 추적 규칙

| 개념 | 계산 |
|------|------|
| 주말잔여 | `max(0, 경과평일계획 + 이월 − 평일실적)` |
| 다음 주 이월 | `max(0, 경과평일계획 + 이월 − 평일실적 − 주말실적)` |
| 계획 대비 편차 | `누적실적 − 오늘까지 누적계획` |

- 정산은 **주 단위**. 화요일 초과분이 그 주 남은 분량을 자연히 줄인다.
- 진행 중인 주는 **오늘 이전 평일만** 정산한다. 아직 오지 않은 날은 미달이 아니다.
- 선행분은 진행률에만 반영하고 다음 주 계획을 줄이지 않는다 — 줄이면 그게 재배분이다.
- 주말잔여가 **주말 2일 × 일일 상한(80p)** 을 넘거나 **2주 연속 이월**이면 `재계획 필요`.

`index.html` 을 직접 손으로 고치지 않는다. 숫자는 `_workspace/*.json` 이 단일 출처이고,
UI는 항상 그것으로부터 생성된다.
