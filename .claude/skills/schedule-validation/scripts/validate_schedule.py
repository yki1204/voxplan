#!/usr/bin/env python3
"""스케줄 산출물을 제약 파일과 교차 검증한다.

사용: validate_schedule.py <constraints.json> <schedule.json>
종료코드 0 = 전부 통과, 1 = 위반 존재.

'존재 확인'이 아니라 '경계면 교차 비교'가 목적이다. 즉 스케줄 안에서만
자기일관성을 보는 게 아니라, 제약 파일이 선언한 페이지 총량·마감일·
일일 상한·주간 케이던스와 스케줄의 실제 배치를 항목별로 대조한다.
"""
import json, sys, datetime as dt
from collections import defaultdict

def main(cpath, spath):
    C, S = json.load(open(cpath)), json.load(open(spath))
    fail, warn = [], []
    cap = C["meta"]["daily_page_cap"]
    allowed = {"MON":0,"TUE":1,"WED":2,"THU":3,"FRI":4}
    wd_ok = {allowed[d] for d in C["meta"]["working_days"]}
    books = {b["id"]: b for b in C["books"]}

    recorded = defaultdict(int)
    edit_days = defaultdict(int)
    weekly_full = defaultdict(int)
    last_page_day = {}
    rec_days = 0

    for r in S["days"]:
        d = dt.date.fromisoformat(r["date"])

        # 1) 근무일 제약
        if d.weekday() not in wd_ok:
            fail.append(f"{r['date']}: 근무일이 아닌 날에 일정 배치 (weekday={d.weekday()})")

        # 2) 일일 페이지 상한
        total = sum(b["pages"] or 0 for b in r["blocks"])
        if total > cap:
            fail.append(f"{r['date']}: 일일 {total}p > 상한 {cap}p")
        if r.get("total_pages") is not None and r["total_pages"] != total:
            fail.append(f"{r['date']}: total_pages={r['total_pages']} 이나 블록 합은 {total}p")

        # 3) 도서 혼합 (전일 점유일은 면제)
        if r["type"] == "recording":
            rec_days += 1
            distinct = {b["book"] for b in r["blocks"]}
            if len(distinct) < C["meta"]["min_books_per_recording_day"]:
                warn.append(f"{r['date']}: 단일 도서({','.join(distinct)}) — 세션 분할 여부 확인 필요")

        for b in r["blocks"]:
            if b["book"] not in books:
                fail.append(f"{r['date']}: 미정의 도서 id '{b['book']}'")
                continue
            if b["kind"] == "edit":
                edit_days[b["book"]] += 1
            if b["pages"]:
                recorded[b["book"]] += b["pages"]
                last_page_day[b["book"]] = max(last_page_day.get(b["book"], d), d)
            if r["type"] == "full_day":
                weekly_full[(b["book"], d.isocalendar()[1])] += 1

    # 4) 도서별 총 페이지 / 마감 / 편집일 / 케이던스
    for bid, b in books.items():
        if b["kind"] == "paged":
            if recorded[bid] != b["pages"]:
                fail.append(f"{b['name']}: 녹음 {recorded[bid]}p != 전체 {b['pages']}p")
            need_edit = b.get("edit_full_days", 0)
            if edit_days[bid] != need_edit:
                fail.append(f"{b['name']}: 편집 전일 {edit_days[bid]}일 != 요구 {need_edit}일")
            if b.get("deadline"):
                dl = dt.date.fromisoformat(b["deadline"])
                # 녹음 완료 + 편집일이 모두 마감 이내여야 한다
                milestone = last_page_day.get(bid)
                if milestone and milestone > dl:
                    fail.append(f"{b['name']}: 녹음 종료 {milestone} > 마감 {dl}")
                for r in S["days"]:
                    for blk in r["blocks"]:
                        if blk["book"] == bid and blk["kind"] == "edit":
                            if dt.date.fromisoformat(r["date"]) > dl:
                                fail.append(f"{b['name']}: 편집일 {r['date']} > 마감 {dl}")
            if b.get("continuous"):
                missing = [r["date"] for r in S["days"] if r["type"] == "recording"
                           and bid not in {x["book"] for x in r["blocks"]}]
                if missing:
                    fail.append(f"{b['name']}: 상주 도서인데 미배치 녹음일 {len(missing)}건 "
                                f"(예: {', '.join(missing[:3])})")
        elif b["kind"] == "full_day_weekly":
            weeks = {w for (x, w) in weekly_full if x == bid}
            all_weeks = {dt.date.fromisoformat(r["date"]).isocalendar()[1] for r in S["days"]}
            gap = sorted(all_weeks - weeks)
            if gap:
                fail.append(f"{b['name']}: 전일 녹음이 없는 주 {gap}")
            dup = [(w, n) for (x, w), n in weekly_full.items() if x == bid and n > 1]
            if dup:
                warn.append(f"{b['name']}: 한 주에 2회 이상 배치된 주 {dup}")

    # 5) 용량 회귀 검사
    declared = C["capacity"]["recording_days"]
    if rec_days != declared:
        fail.append(f"녹음일 수 {rec_days} != 제약 선언 {declared}")

    for m in fail: print(f"FAIL  {m}")
    for m in warn: print(f"WARN  {m}")
    print(f"\n검증 결과: FAIL {len(fail)} / WARN {len(warn)} "
          f"| 녹음일 {rec_days}일 | 총 {sum(recorded.values())}p")
    return 1 if fail else 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
