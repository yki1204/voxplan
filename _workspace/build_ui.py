#!/usr/bin/env python3
"""계획 JSON + 트래커 JS → index.html.

계획 수치는 전부 _workspace/*.json 에서 읽어 인라인한다.
실적은 페이지가 런타임에 data/checkins.json 으로 저장한다(이 스크립트가 만들지 않는다).
"""
import json, datetime as dt
from ui_plan import build

PLAN = build()
S = json.load(open("_workspace/02_optimizer_schedule.json"))
C = json.load(open("_workspace/01_constraint-analyst_constraints.json"))
CAP, BAND_LO = PLAN["cap"], PLAN["bandLo"]
APP = open("_workspace/ui_app.js").read()

def md(iso):
    d = dt.date.fromisoformat(iso); return f"{d.month}/{d.day}"

CSS = r"""
:root{
  --ground:#EDF1F2; --surface:#FFFFFF; --surface-2:#F6F8F8;
  --ink:#12181A; --ink-2:#3E4C50; --muted:#6B7C81; --rule:#D2DBDD;
  --accent:#12655A; --caution:#9E5A12; --bad:#A32E28; --good:#12655A;
  --bk-yt:#8C6A11; --bk-mj:#12655A; --bk-bb:#414CA0; --bk-lb:#9C3F3A;
  --shadow:0 1px 2px rgba(16,32,36,.06),0 8px 20px -14px rgba(16,32,36,.22);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#0D1214; --surface:#161D1F; --surface-2:#1C2427;
    --ink:#E7EEEF; --ink-2:#B4C3C6; --muted:#85989C; --rule:#283336;
    --accent:#4CC0AC; --caution:#D79A4A; --bad:#E8837A; --good:#4CC0AC;
    --bk-yt:#D2A73E; --bk-mj:#3FB6A2; --bk-bb:#8B95E4; --bk-lb:#DE7C74;
    --shadow:0 1px 2px rgba(0,0,0,.5),0 10px 26px -16px rgba(0,0,0,.8);
  }
}
:root[data-theme="dark"]{
  --ground:#0D1214; --surface:#161D1F; --surface-2:#1C2427;
  --ink:#E7EEEF; --ink-2:#B4C3C6; --muted:#85989C; --rule:#283336;
  --accent:#4CC0AC; --caution:#D79A4A; --bad:#E8837A; --good:#4CC0AC;
  --bk-yt:#D2A73E; --bk-mj:#3FB6A2; --bk-bb:#8B95E4; --bk-lb:#DE7C74;
  --shadow:0 1px 2px rgba(0,0,0,.5),0 10px 26px -16px rgba(0,0,0,.8);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:"IBM Plex Sans KR","IBM Plex Sans",system-ui,sans-serif;
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:clamp(24px,4vw,52px) clamp(14px,3vw,30px) 72px;
  display:flex;flex-direction:column;gap:40px}
h1,h2,h3{margin:0;text-wrap:balance;line-height:1.25}
.eyebrow{font-family:"Archivo",system-ui,sans-serif;font-weight:700;font-size:11px;
  letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
.sec{display:flex;flex-direction:column;gap:12px}
.sec__hd{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.sec__note{font-size:12.5px;color:var(--muted)}

/* ── header ── */
.hero{display:flex;flex-direction:column;gap:16px;border-bottom:1px solid var(--rule);
  padding-bottom:26px}
.hero h1{font-size:clamp(27px,4.3vw,40px);font-weight:700;letter-spacing:-.02em}
.hero p{margin:0;max-width:64ch;color:var(--ink-2)}
.hero__range{font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.stats{display:grid;gap:1px;background:var(--rule);border:1px solid var(--rule);
  border-radius:10px;overflow:hidden;grid-template-columns:repeat(auto-fit,minmax(142px,1fr))}
.stat{background:var(--surface);padding:13px 15px;display:flex;flex-direction:column;gap:2px}
.stat dt{font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);
  font-family:"Archivo",sans-serif;font-weight:600}
.stat dd{margin:0;font-family:"IBM Plex Mono",monospace;font-size:21px;font-weight:500;
  font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.stat dd i{font-style:normal;font-size:12px;color:var(--muted);margin-left:2px}

/* ── save chip ── */
.chip{margin-left:auto;display:inline-flex;align-items:center;gap:9px}
#saveState{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--muted);
  padding:3px 9px;border:1px solid var(--rule);border-radius:20px;background:var(--surface)}
#saveState[data-kind="saved"]{color:var(--good);border-color:color-mix(in srgb,var(--good) 40%,var(--rule))}
#saveState[data-kind="err"]{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 45%,var(--rule))}
.storenote{margin:-4px 0 0;font-size:12px;color:var(--muted)}
.storenote[data-mode="blocked"]{color:var(--bad);font-weight:600}
input:focus-visible,button:focus-visible{outline:2px solid var(--accent);
  outline-offset:2px}

/* ── progress ── */
.pg{display:grid;grid-template-columns:auto 1fr;gap:26px;align-items:center;
  background:var(--surface);border:1px solid var(--rule);border-radius:12px;
  padding:20px 22px;box-shadow:var(--shadow)}
.pg__ring{position:relative;width:132px;height:132px;flex:none}
.pg__ring svg{width:100%;height:100%;transform:rotate(-90deg)}
.pg__trk{fill:none;stroke:var(--surface-2);stroke-width:9}
.pg__arc{fill:none;stroke:var(--accent);stroke-width:9;stroke-linecap:round;
  transition:stroke-dashoffset .45s cubic-bezier(.4,0,.2,1)}
.pg__ctr{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:1px}
.pg__ctr b{font-family:"IBM Plex Mono",monospace;font-size:31px;font-weight:600;
  font-variant-numeric:tabular-nums;letter-spacing:-.03em}
.pg__ctr b i{font-style:normal;font-size:15px;color:var(--muted)}
.pg__ctr span{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.pg__side{display:flex;flex-direction:column;gap:13px;min-width:0}
.verdict{display:flex;flex-direction:column;gap:2px;padding:9px 13px;border-radius:8px;
  border-left:3px solid var(--accent);background:var(--surface-2)}
.verdict b{font-size:13.5px;font-weight:600;color:var(--accent)}
.verdict span{font-size:12.5px;color:var(--ink-2)}
.verdict--ok{border-left-color:var(--good)} .verdict--ok b{color:var(--good)}
.verdict--idle{border-left-color:var(--muted)} .verdict--idle b{color:var(--muted)}
.verdict--warn{border-left-color:var(--caution)} .verdict--warn b{color:var(--caution)}
.verdict--bad{border-left-color:var(--bad)} .verdict--bad b{color:var(--bad)}
.pg__stats{display:flex;gap:22px;margin:0;flex-wrap:wrap}
.pg__stats dt{font-family:"Archivo",sans-serif;font-size:10px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--muted);font-weight:600}
.pg__stats dd{margin:0;font-family:"IBM Plex Mono",monospace;font-size:17px;font-weight:500;
  font-variant-numeric:tabular-nums}
.pg__stats dd i{font-style:normal;font-size:11.5px;color:var(--muted)}
.pg__stats dd.is-neg{color:var(--bad)} .pg__stats dd.is-pos{color:var(--good)}
.pg__books{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
.pg__books li{display:grid;grid-template-columns:6.6em 1fr 5.4em;align-items:center;gap:10px;
  font-size:12.5px}
.pg__nm{color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pg__bar{position:relative;height:7px;border-radius:4px;background:var(--surface-2);
  border:1px solid var(--rule);overflow:visible}
.pg__bar i{display:block;height:100%;background:var(--bk);border-radius:3px;
  transition:width .35s ease}
.pg__bar u{position:absolute;top:-3px;bottom:-3px;width:1.5px;background:var(--ink-2);
  opacity:.55;text-decoration:none}
.pg__pg{font-family:"IBM Plex Mono",monospace;font-size:12px;text-align:right;
  font-variant-numeric:tabular-nums;color:var(--bk);font-weight:600}
.pg__pg em{font-style:normal;font-weight:400;color:var(--muted)}

/* ── rails ── */
.rails{list-style:none;margin:0;padding:0;display:grid;gap:12px;
  grid-template-columns:repeat(auto-fit,minmax(252px,1fr))}
.rail{background:var(--surface);border:1px solid var(--rule);border-radius:10px;
  padding:14px 15px 13px;display:flex;flex-direction:column;gap:8px;box-shadow:var(--shadow)}
.rail__top{display:flex;align-items:center;gap:8px}
.rail__top h3{font-size:14px;font-weight:600;flex:1}
.rail__dot{width:9px;height:9px;border-radius:2px;background:var(--bk);flex:none}
.rail__amt{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.rail__bar{height:5px;border-radius:3px;background:var(--surface-2);border:1px solid var(--rule);
  overflow:hidden}
.rail__fill{height:100%;width:100%;background:var(--bk)}
.rail__bar--cadence{display:flex;gap:3px;background:none;border:0;overflow:visible;height:5px}
.rail__bar--cadence i{flex:1;border-radius:2px;background:var(--bk)}
.rail__meta{margin:0;font-size:11.5px;color:var(--muted)}
.rail__meta b{color:var(--ink-2);font-weight:600;font-family:"IBM Plex Mono",monospace}
.rail__ok{color:var(--accent);font-weight:600}

/* ── weeks ── */
#weeks{display:flex;flex-direction:column;gap:18px}
.wk{display:flex;flex-direction:column;gap:8px;min-width:0}
.wk__hd{display:flex;align-items:baseline;gap:10px;padding-left:2px}
.wk__n{font-family:"Archivo",sans-serif;font-weight:700;font-size:12px;letter-spacing:.1em;
  color:var(--accent)}
.wk__span,.wk__sum{font-family:"IBM Plex Mono",monospace;font-size:12.5px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.wk__sum{margin-left:auto}
.wk__carry{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--bad);
  font-variant-numeric:tabular-nums}
.wk__grid{display:grid;grid-template-columns:repeat(5,minmax(176px,1fr)) minmax(168px,.92fr);
  gap:9px;overflow-x:auto;padding-bottom:4px}
.day,.wknd{background:var(--surface);border:1px solid var(--rule);border-radius:10px;
  padding:11px 12px 10px;display:flex;flex-direction:column;gap:9px;box-shadow:var(--shadow)}
.day__hd{display:flex;align-items:center;gap:6px;border-bottom:1px solid var(--rule);
  padding-bottom:6px}
.day__date{font-family:"IBM Plex Mono",monospace;font-size:13.5px;font-weight:600;
  font-variant-numeric:tabular-nums}
.day__dow{font-size:11px;color:var(--muted)}
.day__fill{margin-left:auto;font-family:"Archivo",sans-serif;font-size:9.5px;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase;color:var(--muted);background:none;
  border:1px solid var(--rule);border-radius:4px;padding:2px 6px;cursor:pointer}
.day__fill:hover{color:var(--accent);border-color:var(--accent)}
.day__blocks{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:5px;flex:1}

/* check-in row */
.ck{display:grid;grid-template-columns:8px 1fr 3.5em 2.7em;align-items:center;gap:6px;
  font-size:12px}
.ck__dot{width:7px;height:7px;border-radius:2px;background:var(--bk)}
.ck__nm{color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  min-width:0}
.ck__nm em{font-style:normal;font-size:9.5px;color:var(--muted);margin-left:3px;
  padding:0 3px;border:1px solid var(--rule);border-radius:3px}
.ck__in{width:100%;font-family:"IBM Plex Mono",monospace;font-size:12.5px;font-weight:600;
  font-variant-numeric:tabular-nums;text-align:right;color:var(--ink);
  background:var(--surface-2);border:1px solid var(--rule);border-radius:5px;
  padding:3px 5px;-moz-appearance:textfield}
.ck__in::-webkit-outer-spin-button,.ck__in::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
.ck__in::placeholder{color:var(--muted);font-weight:400}
.ck.is-met .ck__in{border-color:var(--bk);color:var(--bk)}
.ck.is-short .ck__in{border-color:var(--caution);color:var(--caution)}
.ck__tgt{font-family:"IBM Plex Mono",monospace;font-size:10.5px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.day__note{margin:0;font-size:10px;line-height:1.45;color:var(--muted);padding-left:12px;
  border-left:2px solid var(--rule)}

/* meter */
.meter{display:flex;align-items:center;gap:7px}
.meter__track{position:relative;flex:1;height:7px;border-radius:4px;background:var(--surface-2);
  border:1px solid var(--rule);overflow:visible}
.meter__fill{height:100%;background:var(--accent);border-radius:3px;transition:width .3s ease}
.meter.is-high .meter__fill{background:var(--caution)}
.meter.is-over .meter__fill{background:var(--bad)}
.meter__tick{position:absolute;top:-2px;bottom:-2px;width:1px;background:var(--rule)}
.meter__plan{position:absolute;top:-3px;bottom:-3px;width:1.5px;background:var(--ink-2);opacity:.5}
.meter__val{font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:600;
  font-variant-numeric:tabular-nums;color:var(--ink-2)}
.meter__val i{font-style:normal;font-weight:400;color:var(--muted)}
.meter.is-high .meter__val{color:var(--caution)} .meter.is-over .meter__val{color:var(--bad)}

/* full-day cell */
.day--full{background:var(--surface-2);border-style:dashed}
.day--full .day__full{flex:1;display:flex;flex-direction:column;gap:4px;justify-content:center;
  border-left:3px solid var(--bk);padding-left:9px}
.day__fulltag{font-family:"Archivo",sans-serif;font-size:9.5px;font-weight:700;
  letter-spacing:.11em;text-transform:uppercase;color:var(--bk)}
.day__fullbook{font-size:12.5px;font-weight:600;color:var(--ink-2)}
.day--full.is-done{border-style:solid;border-color:color-mix(in srgb,var(--bk) 45%,var(--rule))}
.chk{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--muted);cursor:pointer}
.chk input{accent-color:var(--bk);width:14px;height:14px;cursor:pointer}
.day--full.is-done .chk{color:var(--bk);font-weight:600}

/* weekend cell */
.wknd{background:linear-gradient(180deg,var(--surface-2),var(--surface));
  border-style:solid;border-color:var(--rule)}
.wknd.is-clear{border-color:color-mix(in srgb,var(--good) 35%,var(--rule))}
.wknd.is-future{background:var(--surface);border-style:dashed;opacity:.62}
.wknd__future{color:var(--muted);font-weight:400}
.wknd.is-warn{border-color:color-mix(in srgb,var(--caution) 50%,var(--rule))}
.wknd.is-over{border-color:color-mix(in srgb,var(--bad) 55%,var(--rule))}
.wknd .day__date{color:var(--muted)}
.wknd__clear{margin:0;flex:1;display:flex;align-items:center;font-size:12px;color:var(--good);
  font-weight:600}
.wknd__tot{margin:0;font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink-2);
  font-variant-numeric:tabular-nums;border-top:1px solid var(--rule);padding-top:7px}
.wknd__tot b{font-weight:600}
.wknd__tot em{font-style:normal;font-size:10.5px;color:var(--muted)}
.wknd__tot.is-done{color:var(--good);font-weight:600}
.wknd__cap{margin:0;font-size:10.5px;line-height:1.4;color:var(--bad);font-weight:600}
.wknd__cap--soft{color:var(--caution)}
.wknd__carry{margin:0;font-size:10.5px;color:var(--bad)}
.wknd__carry b{font-family:"IBM Plex Mono",monospace}

/* ── notes / table ── */
.notes{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(290px,1fr))}
.note{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:16px 17px;
  display:flex;flex-direction:column;gap:7px;box-shadow:var(--shadow)}
.note h3{font-size:14px;font-weight:600}
.note p,.note li{margin:0;font-size:12.5px;color:var(--ink-2);line-height:1.62}
.note ul{margin:0;padding-left:16px;display:flex;flex-direction:column;gap:4px}
.note code{font-family:"IBM Plex Mono",monospace;font-size:11.5px;background:var(--surface-2);
  padding:1px 5px;border-radius:3px;border:1px solid var(--rule)}
.scroll{overflow-x:auto;border:1px solid var(--rule);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;min-width:620px;font-size:12.5px}
th,td{text-align:left;padding:9px 13px;border-bottom:1px solid var(--rule)}
th{font-family:"Archivo",sans-serif;font-size:10px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--muted);font-weight:700;background:var(--surface-2)}
tr:last-child td{border-bottom:0}
td.num{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
tr.is-pick td{background:color-mix(in srgb,var(--accent) 9%,transparent);font-weight:500}
.pill{display:inline-block;font-family:"Archivo",sans-serif;font-size:9px;font-weight:700;
  letter-spacing:.09em;text-transform:uppercase;color:var(--surface);background:var(--accent);
  padding:2px 6px;border-radius:3px;margin-left:5px;vertical-align:1px}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;font-size:12px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:9px;height:9px;border-radius:2px;background:var(--bk);display:inline-block}
footer{border-top:1px solid var(--rule);padding-top:18px;font-size:11.5px;color:var(--muted);
  display:flex;flex-wrap:wrap;gap:5px 16px}
@media (max-width:760px){
  .pg{grid-template-columns:1fr;justify-items:center;text-align:center}
  .pg__books li{grid-template-columns:5.6em 1fr 5em}
  .pg__stats{justify-content:center}
}

/* ── 쿠폰 ── */
.cpr{display:flex;align-items:center;flex-wrap:wrap;gap:8px 12px;padding:11px 14px;
  border:1px dashed var(--rule);border-radius:10px;background:var(--surface-2)}
.cpr__label{font-family:"Archivo",sans-serif;font-size:10px;font-weight:700;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.cpr__chip{display:inline-flex;align-items:center;gap:6px;font-family:inherit;font-size:12.5px;
  font-weight:600;color:var(--ink);background:var(--surface);border:1px solid var(--rule);
  border-radius:20px;padding:4px 12px 4px 9px;cursor:pointer}
.cpr__chip:hover{border-color:var(--accent);color:var(--accent)}
.cpr__hint{font-size:11.5px;color:var(--muted);margin-left:auto}

.cpdlg{border:0;padding:0;background:none;max-width:min(430px,92vw)}
.cpdlg::backdrop{background:rgba(8,14,16,.62)}
.cp{display:flex;flex-direction:column;gap:13px;padding:26px 26px 22px;border-radius:16px;
  background:var(--surface);border:1px solid var(--rule);box-shadow:var(--shadow);
  animation:cpIn .34s cubic-bezier(.2,.9,.3,1)}
@keyframes cpIn{from{opacity:0;transform:scale(.94) translateY(8px)}to{opacity:1;transform:none}}
.cp__eyebrow{margin:0;font-family:"Archivo",sans-serif;font-size:10px;font-weight:700;
  letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.cp__hd{font-size:19px;font-weight:700;letter-spacing:-.01em}
.cp__ask{margin:0;font-size:12.5px;line-height:1.6;color:var(--ink-2)}
.cp__ask b{color:var(--ink)}
.cp__close{margin-top:2px;font-family:"Archivo",sans-serif;font-size:11.5px;font-weight:700;
  letter-spacing:.08em;text-transform:uppercase;color:var(--surface);background:var(--accent);
  border:0;padding:9px 14px;border-radius:7px;cursor:pointer;align-self:flex-start}
.cp__close:hover{filter:brightness(1.1)}

/* 티켓: 양옆에 절취 노치 */
.tk{position:relative;display:flex;flex-direction:column;align-items:center;gap:5px;
  padding:20px 22px;border:2px dashed var(--accent);border-radius:12px;
  background:var(--surface-2);overflow:hidden}
.tk::before,.tk::after{content:"";position:absolute;top:50%;width:16px;height:16px;
  border-radius:50%;background:var(--surface);border:2px dashed var(--accent);
  transform:translateY(-50%)}
.tk::before{left:-9px;clip-path:inset(0 0 0 50%)}
.tk::after{right:-9px;clip-path:inset(0 50% 0 0)}
.tk__emoji{font-size:38px;line-height:1}
.tk__name{font-size:17px;font-weight:700;letter-spacing:-.01em}
.tk__note{font-size:12px;color:var(--ink-2);text-align:center;max-width:26ch}
.tk__sn{margin-top:6px;font-family:"IBM Plex Mono",monospace;font-size:11.5px;font-weight:500;
  letter-spacing:.05em;color:var(--muted);border-top:1px dashed var(--rule);
  padding-top:8px;width:100%;text-align:center}
.cp--grand .tk{border-color:var(--bk-lb);background:color-mix(in srgb,var(--bk-lb) 8%,var(--surface-2))}
.cp--grand .tk::before,.cp--grand .tk::after{border-color:var(--bk-lb)}
.cp--grand .cp__eyebrow{color:var(--bk-lb)}
.cp--grand .cp__close{background:var(--bk-lb)}
.cp--grand .tk__emoji{font-size:44px}

@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

# ── 도서별 진도 레일 (계획 기준, 정적) ─────────────────────────────────────
cbk = {b["id"]: b for b in C["books"]}
rails = []
for b in PLAN["books"]:
    cb = cbk[b["id"]]
    if not b["paged"]:
        n = sum(1 for w in PLAN["weeks"] for d in w["days"]
                if d["type"] == "full_day" and d["blocks"][0]["book"] == b["id"])
        rails.append(f'''<li class="rail" style="--bk:var(--bk-{b['hue']})">
  <div class="rail__top"><span class="rail__dot"></span><h3>{b['name']}</h3>
    <span class="rail__amt">주 1일 · {n}회</span></div>
  <div class="rail__bar rail__bar--cadence">{''.join('<i></i>' for _ in range(n))}</div>
  <p class="rail__meta">전일 녹음 · 매주 월요일 고정 · 페이지 예산 비소비</p></li>''')
        continue
    fin = max(r["date"] for r in S["days"] for x in r["blocks"] if x["book"] == b["id"])
    dl = cb["deadline"]
    slack = sum(1 for i in range(1, (dt.date.fromisoformat(dl) - dt.date.fromisoformat(fin)).days + 1)
                if (dt.date.fromisoformat(fin) + dt.timedelta(days=i)).weekday() < 5)
    rails.append(f'''<li class="rail" style="--bk:var(--bk-{b['hue']})">
  <div class="rail__top"><span class="rail__dot"></span><h3>{b['name']}</h3>
    <span class="rail__amt">{b['total']}p</span></div>
  <div class="rail__bar"><div class="rail__fill"></div></div>
  <p class="rail__meta">계획 완료 <b>{md(fin)}</b> · 마감 {md(dl)}
    <span class="rail__ok">{'여유 평일 ' + str(slack) + '일' if slack else '마감일 종료'}</span></p></li>''')

alts = [("2026-10-02", 22, 37.3, 5, 15, True, "상한 40p 대비 완충 유지, 단조 구간 최소"),
        ("2026-10-09", 26, 31.5, 9, 10, False, "부하는 더 가볍지만 단조 구간 2배"),
        ("2026-10-23", 34, 24.1, 17, 0, False, "일평균이 목표 밴드 하한(30p) 미달")]
alt_rows = "".join(
    f'''<tr{' class="is-pick"' if pick else ''}><td>{md(d)}{'<span class="pill">채택</span>' if pick else ''}</td>
  <td class="num">{rec}일</td><td class="num">{avg}p</td><td class="num">{sb}일</td>
  <td class="num">{buf or '—'}</td><td>{why}</td></tr>''' for d, rec, avg, sb, buf, pick, why in alts)

legend = "".join(f'<span style="--bk:var(--bk-{b["hue"]})"><i></i>{b["name"]}</span>'
                 for b in PLAN["books"])

HTML = f'''<title>녹음 일정 스케줄</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<style>{CSS}</style>
<script id="plan" type="application/json">{json.dumps(PLAN, ensure_ascii=False, separators=(',', ':'))}</script>

<div class="wrap">
  <header class="hero">
    <span class="eyebrow">Voxplan · Recording Schedule</span>
    <h1>녹음 일정 스케줄</h1>
    <p>도서 4종을 성대 부하 상한 <b>{CAP}p/일</b> 안에서 배분한 {len(PLAN['weeks'])}주 계획.
       각 칸에 <b>실제 녹음한 페이지</b>를 입력하면 미달분이 그 주 <b>주말 보충 칸</b>으로 모이고,
       평일 계획은 그대로 유지된다.</p>
    <span class="hero__range">{PLAN['start']} → {PLAN['end']} · 평일 {PLAN['weekdays']}일 · 녹음 {PLAN['recDays']}일</span>
    <dl class="stats">
      <div class="stat"><dt>총 녹음량</dt><dd>{PLAN['totalPages']}<i>p</i></dd></div>
      <div class="stat"><dt>녹음일</dt><dd>{PLAN['recDays']}<i>일</i></dd></div>
      <div class="stat"><dt>일평균 계획</dt><dd>{PLAN['avg']}<i>p</i></dd></div>
      <div class="stat"><dt>일일 상한</dt><dd>{CAP}<i>p</i></dd></div>
      <div class="stat"><dt>주말 완충</dt><dd>{CAP*2}<i>p</i></dd></div>
      <div class="stat"><dt>마감 버퍼</dt><dd>15<i>평일</i></dd></div>
    </dl>
  </header>

  <section class="sec">
    <div class="sec__hd">
      <h2 class="eyebrow">진행 현황</h2>
      <span class="sec__note">막대 위 세로선 = 오늘까지의 계획 위치</span>
      <span class="chip"><span id="saveState" data-kind="idle">불러오는 중…</span></span>
    </div>
    <p id="storeNote" class="storenote"></p>
    <div id="progress"></div>
    <div id="coupons" class="cpr" hidden></div>
  </section>

  <section class="sec">
    <h2 class="eyebrow">도서별 계획</h2>
    <ul class="rails">{''.join(rails)}</ul>
  </section>

  <section class="sec">
    <div class="sec__hd">
      <h2 class="eyebrow">주간 일정 · 실적 체크인</h2>
      <span class="sec__note">숫자칸에 실제 녹음 페이지를 입력 · <b>/n p</b> 는 그날 목표</span>
    </div>
    <div class="legend">{legend}
      <span><i style="border:1px dashed var(--muted);background:none"></i>전일 점유(녹음·편집)</span>
    </div>
    <div id="weeks"></div>
  </section>

  <section class="sec">
    <h2 class="eyebrow">종료일 대안 비교</h2>
    <div class="scroll"><table>
      <thead><tr><th>종료일</th><th>녹음일</th><th>일평균</th><th>단일도서 구간</th>
        <th>마감 버퍼(평일)</th><th>판단</th></tr></thead>
      <tbody>{alt_rows}</tbody></table></div>
  </section>

  <section class="notes">
    <div class="note">
      <h3>미달분을 왜 재배분하지 않는가</h3>
      <p>하루 미달마다 전체를 다시 짜면 셋이 깨진다. 매주 월요일 전일 녹음이라는 <b>리듬</b>,
         도서별 <b>마감 구간</b>, 그리고 <b>일부하 평준화</b>. 그래서 미달분은 평일 계획을 건드리지 않고
         그 주 <b>주말 칸</b>으로 격리한다. 주말은 원래 비어 있어 완충으로 쓸 수 있고,
         한 주 안에서 정산되므로 부채가 무한히 쌓이지 않는다.</p>
    </div>
    <div class="note">
      <h3>정산은 일 단위가 아니라 주 단위</h3>
      <p>화요일에 목표보다 많이 녹음하면 그 주의 남은 분량이 그만큼 줄어야 한다.
         일 단위 정산은 이것을 표현하지 못하므로 주 단위로 계산한다.</p>
      <p><code>주말잔여 = max(0, 계획+이월 − 평일실적)</code><br>
         <code>이월 = max(0, 계획+이월 − 평일 − 주말실적)</code></p>
      <p>주말에도 못 채운 분량은 <b>0으로 처리하지 않고 다음 주로 이월</b>해 붉게 표시한다.
         선행분은 전체 진행률에만 반영하고 다음 주 계획을 줄이지 않는다 — 줄이면 그게 재배분이다.</p>
    </div>
    <div class="note">
      <h3>주말 용량 가드레일</h3>
      <p>주말 보충도 성대 상한을 받는다. 주말 2일 × {CAP}p = <b>{CAP*2}p</b>가 물리적 한계다.</p>
      <ul>
        <li>{CAP}p 이하 — 하루로 소화</li>
        <li>{CAP}~{CAP*2}p — <b>주말 이틀 필요</b> (주의)</li>
        <li>{CAP*2}p 초과 — <b>흡수 불가, 재계획 검토</b></li>
      </ul>
      <p>이 선이 없으면 이월이 조용히 쌓여 마감 직전에 터진다. 2주 연속 이월도 경고로 올린다.</p>
    </div>
    <div class="note">
      <h3>어디에 저장되는가</h3>
      <p>입력한 실적은 <b>이 브라우저</b>에 저장된다. 입력하는 즉시 기록되므로
         "아직 저장 안 된 몇 초"가 없다.</p>
      <ul>
        <li><b>유지된다</b> — 새로 고침, 탭 닫기, 브라우저 재시작, 페이지 재배포 후에도 남는다.</li>
        <li><b>유지되지 않는다</b> — 다른 기기·다른 브라우저, 시크릿 창을 닫은 뒤,
            브라우저에서 사이트 데이터를 지운 뒤.</li>
      </ul>
      <p>저장이 막힌 환경(시크릿 창, 사이트 데이터 차단)이면 상태 문구가 <b>저장 불가</b>로
         바뀐다. 조용히 잃는 것보다 알고 쓰는 편이 낫기 때문이다.</p>
      <p>진행률·주말잔여·이월은 저장하지 않고 매번 다시 계산한다. 계획이 바뀌면 옛 파생값은
         틀리기 때문이다.</p>
    </div>
    <div class="note">
      <h3>해결하지 못한 지점</h3>
      <p>9/25 이후 <b>5일</b>은 도서 혼합이 불가능하다. 자율 전공책(9/4)·성경 스토리텔링(9/24)이
         마감으로 끝나면 레바논의 시내만 남기 때문이며, 배분으로 풀 수 있는 문제가 아니다.
         해당 5일은 오전·오후 2세션으로 나눠 서로 다른 장을 배정해 완화만 해뒀다.</p>
    </div>
  </section>

  <dialog id="cpDlg" class="cpdlg"></dialog>

  <footer>
    <span>계획 검증: 하드 제약 <b>FAIL 0</b> (마감·상한·총량·상주 배치·주간 케이던스·근무일)</span>
    <span class="mono">voxplan · {PLAN['start']}→{PLAN['end']}</span>
  </footer>
</div>
<script>{APP}</script>'''

open("index.html", "w").write(HTML)
print(f"index.html written: {len(HTML):,} bytes")
