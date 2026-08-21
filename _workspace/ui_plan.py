"""계획 JSON → UI가 소비할 PLAN 객체 (주말 날짜·도서 메타 포함)."""
import json, datetime as dt
from collections import OrderedDict

def build():
    S = json.load(open("_workspace/02_optimizer_schedule.json"))
    C = json.load(open("_workspace/01_constraint-analyst_constraints.json"))
    cb = {b["id"]: b for b in C["books"]}
    order = ["classics-youtube","major-book","bible-storytelling","lebanon"]
    hue   = {"classics-youtube":"yt","major-book":"mj","bible-storytelling":"bb","lebanon":"lb"}

    books = []
    for bid in order:
        b = cb[bid]
        books.append({"id":bid,"name":b["name"],"hue":hue[bid],
                      "paged":b["kind"]=="paged",
                      "total":S["totals"].get(bid,0),
                      "deadline":b.get("deadline")})

    weeks = OrderedDict()
    for r in S["days"]:
        weeks.setdefault(r["week"],[]).append(r)

    wk_out = []
    for wk, rows in weeks.items():
        fri = dt.date.fromisoformat(rows[-1]["date"])
        sat = fri + dt.timedelta(days=1)
        days = []
        for r in rows:
            days.append({
                "date": r["date"], "dow": r["dow"], "type": r["type"],
                "total": r["total_pages"],
                "note": r.get("split_note",""),
                "blocks":[{"book":b["book"],"pages":b["pages"],
                           "kind":b["kind"],"label":b["label"],
                           "session":b.get("session","")} for b in r["blocks"]],
            })
        wk_out.append({"n":wk,"days":days,"weekend":sat.isoformat(),
                       "span":f'{dt.date.fromisoformat(rows[0]["date"]).strftime("%-m/%-d")}'
                              f' – {fri.strftime("%-m/%-d")}'})
    return {"start":S["meta"]["start"],"end":S["meta"]["end"],
            "cap":S["meta"]["daily_page_cap"],"bandLo":S["meta"]["daily_page_band"][0],
            "totalPages":S["meta"]["total_pages"],"recDays":S["meta"]["recording_days"],
            "avg":C["capacity"]["avg_per_recording_day"],
            "weekdays":C["capacity"]["weekdays"],
            "books":books,"weeks":wk_out}

if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False)[:400])
