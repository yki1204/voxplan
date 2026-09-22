#!/usr/bin/env python3
"""스케줄 산출물을 제약 파일과 교차 검증한다.

사용: validate_schedule.py <constraints.json> <schedule.json>
종료코드 0 = 전부 통과, 1 = 위반 존재.

'존재 확인'이 아니라 '경계면 교차 비교'가 목적이다. 즉 스케줄 안에서만
자기일관성을 보는 게 아니라, 제약 파일이 선언한 페이지 총량·마감일·
일일 상한·주간 케이던스와 스케줄의 실제 배치를 항목별로 대조한다.

plan_revision 2 스키마 대응 (2026-09-22 개정):
  - meta.excluded_dates: 해당 평일은 days[] 에 없는 것이 정상이며,
    반대로 days[] 에 존재하면 FAIL. 제외되지 않은 평일이 빠져도 FAIL(신규).
  - 편집 블록은 더 이상 항상 전일 점유가 아니다. type=="full_day" 인 날의
    edit 블록만 edit_full_days 로 센다. 같은 날 녹음이 붙는 동반 편집은
    edit_window / bound_to 로 따로 검증한다(신규).
  - full_day_weekly 도서는 "모든 주에 1회"가 아니라 제약의 occupied_dates
    집합과 완전 일치하는지, 그리고 전부 cadence_weekday 요일인지 본다(강화).
  - min_books_per_recording_day 는 제약 파일 값을 읽는다. 값이 1로 내려가
    혼합 FAIL/WARN 이 사라지는 구간을 놓치지 않도록, 발성 도서(kind=="record")
    가 1종뿐인 날은 항상 WARN 으로 남긴다(강화).
"""
import json, sys, datetime as dt
from collections import defaultdict

WD = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}


def main(cpath, spath):
    C, S = json.load(open(cpath)), json.load(open(spath))
    fail, warn = [], []
    meta = C["meta"]
    cap = meta["daily_page_cap"]
    wd_ok = {WD[d] for d in meta["working_days"]}
    books = {b["id"]: b for b in C["books"]}
    excluded = {dt.date.fromisoformat(d) for d in meta.get("excluded_dates", [])}
    start = dt.date.fromisoformat(meta["start"])
    end = dt.date.fromisoformat(meta["end"])

    recorded = defaultdict(int)          # 도서별 녹음 페이지 합
    rec_dates = defaultdict(list)        # 도서별 녹음(페이지 배정) 날짜
    edit_full = defaultdict(list)        # 전일 점유 편집일
    edit_conc = defaultdict(list)        # 동반(비전일) 편집일
    fullday_dates = defaultdict(list)    # full_day 점유 도서별 날짜
    seen = {}
    rec_days = 0

    # ---------- 1) 달력 커버리지: 제외일 / 평일 누락 / 중복 ----------
    for r in S["days"]:
        d = dt.date.fromisoformat(r["date"])
        if d in seen:
            fail.append(f"{r['date']}: 중복 날짜 항목")
        seen[d] = r
        if d.weekday() not in wd_ok:
            fail.append(f"{r['date']}: 근무일이 아닌 날에 일정 배치 (weekday={d.weekday()})")
        if d in excluded:
            fail.append(f"{r['date']}: 제외일인데 일정이 배치됨 (blocks={len(r['blocks'])})")
        if not (start <= d <= end):
            fail.append(f"{r['date']}: 계획 기간 {start}~{end} 밖")

    cur, expected = start, []
    while cur <= end:
        if cur.weekday() in wd_ok and cur not in excluded:
            expected.append(cur)
        cur += dt.timedelta(days=1)
    missing_days = [str(d) for d in expected if d not in seen]
    if missing_days:
        fail.append(f"제외일이 아닌 근무일 누락 {len(missing_days)}건: {', '.join(missing_days)}")

    # ---------- 2) 일별 상한 / 합계 / 블록 ----------
    for r in S["days"]:
        d = dt.date.fromisoformat(r["date"])
        total = sum(b["pages"] or 0 for b in r["blocks"])
        if total > cap:
            fail.append(f"{r['date']}: 일일 {total}p > 상한 {cap}p")
        if r.get("total_pages") is not None and r["total_pages"] != total:
            fail.append(f"{r['date']}: total_pages={r['total_pages']} 이나 블록 합은 {total}p")

        if r["type"] == "recording":
            rec_days += 1
            voiced = {b["book"] for b in r["blocks"] if b["kind"] == "record"}
            distinct = {b["book"] for b in r["blocks"]}
            if len(distinct) < meta["min_books_per_recording_day"]:
                fail.append(f"{r['date']}: 도서 {len(distinct)}종 < 최소 "
                            f"{meta['min_books_per_recording_day']}종")
            if len(voiced) < 2:
                warn.append(f"{r['date']}: 발성 도서 1종({','.join(voiced)}) "
                            f"— 혼합 불가 사유·완화 확인 필요")
        elif r["type"] == "full_day":
            if total != 0:
                fail.append(f"{r['date']}: 전일 점유일에 페이지 {total}p 배정")

        for b in r["blocks"]:
            if b["book"] not in books:
                fail.append(f"{r['date']}: 미정의 도서 id '{b['book']}'")
                continue
            if b["kind"] == "edit":
                (edit_full if r["type"] == "full_day" else edit_conc)[b["book"]].append(d)
            if r["type"] == "full_day":
                fullday_dates[b["book"]].append(d)
            if b["pages"]:
                recorded[b["book"]] += b["pages"]
                rec_dates[b["book"]].append(d)

    # ---------- 3) 도서별 교차 대조 ----------
    for bid, b in books.items():
        nm = b["name"]
        if b["kind"] == "paged":
            if recorded[bid] != b["pages"]:
                fail.append(f"{nm}: 녹음 {recorded[bid]}p != 전체 {b['pages']}p")
            need = b.get("recording_days_required")
            if need is not None and len(rec_dates[bid]) != need:
                fail.append(f"{nm}: 녹음일 {len(rec_dates[bid])}일 != 요구 {need}일")
            seq = b.get("daily_sequence")
            if seq:
                got = [blk["pages"] for d in sorted(rec_dates[bid])
                       for blk in seen[d]["blocks"]
                       if blk["book"] == bid and blk["pages"]]
                if got != seq:
                    fail.append(f"{nm}: 일별 배분 {got} != 선언 {seq}")

            need_edit = b.get("edit_full_days", 0)
            if len(edit_full[bid]) != need_edit:
                fail.append(f"{nm}: 편집 전일 {len(edit_full[bid])}일 != 요구 {need_edit}일")
            if b.get("edit_dates"):
                want = sorted(b["edit_dates"])
                got = sorted(str(d) for d in edit_full[bid])
                if want != got:
                    fail.append(f"{nm}: 편집 전일 날짜 {got} != 선언 {want}")

            ew = b.get("edit_window")
            if ew:
                got = sorted(edit_conc[bid])
                ws, we = dt.date.fromisoformat(ew["start"]), dt.date.fromisoformat(ew["end"])
                if len(got) != ew["days"]:
                    fail.append(f"{nm}: 편집 창 일수 {len(got)}일 != 선언 {ew['days']}일")
                out = [str(d) for d in got if not (ws <= d <= we)]
                if out:
                    fail.append(f"{nm}: 편집일이 창 {ws}~{we} 밖 — {', '.join(out)}")
                if got and got[0] != ws:
                    fail.append(f"{nm}: 편집 시작 {got[0]} != 선언 {ws}")
                if got and got[-1] != we:
                    fail.append(f"{nm}: 편집 종료 {got[-1]} != 선언 {we}")

            if b.get("deadline"):
                dl = dt.date.fromisoformat(b["deadline"])
                if rec_dates[bid] and max(rec_dates[bid]) > dl:
                    fail.append(f"{nm}: 녹음 종료 {max(rec_dates[bid])} > 마감 {dl}")
                for d in edit_full[bid] + edit_conc[bid]:
                    if d > dl:
                        fail.append(f"{nm}: 편집일 {d} > 마감 {dl}")

            if b.get("continuous"):
                missing = [r["date"] for r in S["days"] if r["type"] == "recording"
                           and bid not in {x["book"] for x in r["blocks"]}]
                if missing:
                    fail.append(f"{nm}: 상주 도서인데 미배치 녹음일 {len(missing)}건 "
                                f"(예: {', '.join(missing[:3])})")

            # 다른 도서의 편집 창에 묶인 도서: 날짜 집합이 완전히 일치해야 한다
            bt = b.get("bound_to")
            if bt and bt.endswith(".edit_window"):
                host = bt.split(".")[0]
                a, e = sorted(rec_dates[bid]), sorted(edit_conc[host])
                if a != e:
                    only_a = [str(x) for x in a if x not in e]
                    only_e = [str(x) for x in e if x not in a]
                    fail.append(f"{nm}: 녹음일 집합 != {host} 편집일 집합 "
                                f"(사도행전 단독 {only_a} / {host} 단독 {only_e})")

        elif b["kind"] == "full_day_weekly":
            got = sorted(fullday_dates[bid])
            want = sorted(dt.date.fromisoformat(x) for x in b.get("occupied_dates", []))
            if got != want:
                fail.append(f"{nm}: 전일 녹음일 {[str(x) for x in got]} "
                            f"!= 선언 {[str(x) for x in want]}")
            cw = b.get("cadence_weekday")
            if cw:
                bad = [str(d) for d in got if d.weekday() != WD[cw]]
                if bad:
                    fail.append(f"{nm}: 케이던스 요일 {cw} 위반 — {', '.join(bad)}")
            perweek = defaultdict(int)
            for d in got:
                perweek[d.isocalendar()[1]] += 1
            dup = sorted(w for w, n in perweek.items() if n > 1)
            if dup:
                warn.append(f"{nm}: 한 주에 2회 이상 배치된 주 {dup}")

    # ---------- 4) 총량 / 용량 회귀 ----------
    declared = C["capacity"]["recording_days"]
    if rec_days != declared:
        fail.append(f"녹음일 수 {rec_days} != 제약 선언 {declared}")
    req = C["capacity"].get("required_pages")
    if req is not None and sum(recorded.values()) != req:
        fail.append(f"총 페이지 {sum(recorded.values())}p != 제약 선언 {req}p")
    for bid, tot in (S.get("totals") or {}).items():
        if recorded[bid] != tot:
            fail.append(f"{bid}: 스케줄 totals {tot}p != 실제 블록 합 {recorded[bid]}p")

    # ---------- 5) weeks[] <-> days[] 정합 / cumulative 단조 ----------
    flat = {r["date"]: r for r in S["days"]}
    wdays = [d for w in S.get("weeks", []) for d in w.get("days", [])]
    if len(wdays) != len(S["days"]):
        fail.append(f"weeks[].days 수 {len(wdays)} != days[] 수 {len(S['days'])}")
    for d in wdays:
        f = flat.get(d["date"])
        if f is None:
            fail.append(f"{d['date']}: weeks[] 에만 있고 days[] 에 없음")
        elif f != d:
            fail.append(f"{d['date']}: weeks[].days 항목이 days[] 와 불일치")
    for w in S.get("weeks", []):
        pp = w.get("planned_pages")
        if pp is not None:
            s = sum(x["total_pages"] for x in w.get("days", []))
            if pp != s:
                fail.append(f"week {w['n']}: planned_pages {pp} != 일별 합 {s}")

    prev = defaultdict(int)
    for r in S["days"]:
        cum = r.get("cumulative") or {}
        for bid, v in cum.items():
            if v < prev[bid]:
                fail.append(f"{r['date']}: cumulative[{bid}] 감소 {prev[bid]} -> {v}")
            prev[bid] = v
    for bid, v in prev.items():
        if v != recorded[bid]:
            fail.append(f"{bid}: 최종 cumulative {v}p != 녹음 합 {recorded[bid]}p")

    for m in fail: print(f"FAIL  {m}")
    for m in warn: print(f"WARN  {m}")
    print(f"\n검증 결과: FAIL {len(fail)} / WARN {len(warn)} "
          f"| 녹음일 {rec_days}일 | 총 {sum(recorded.values())}p")
    return 1 if fail else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
