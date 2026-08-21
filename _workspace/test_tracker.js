/* 실제 ui_app.js 를 최소 DOM 스텁 위에서 실행해 이월/진행률 산출을 검증한다. */
const fs = require("fs");
const PLAN = JSON.parse(fs.readFileSync("_workspace/ui_plan.json", "utf8"));

function El(tag) {
  return { tag, innerHTML: "", outerHTML: "", textContent: "", dataset: {},
    classList: { toggle(){}, contains(c){ return (this._c||[]).includes(c); }, _c: [] },
    querySelector(){ return null; }, querySelectorAll(){ return []; },
    contains(){ return false; }, closest(){ return null; }, appendChild(){}, };
}
const nodes = { plan: El("script"), progress: El("div"), weeks: El("div"), saveState: El("span") };
nodes.plan.textContent = JSON.stringify(PLAN);
global.document = {
  getElementById: id => nodes[id] || null,
  querySelector: () => null, querySelectorAll: () => [],
  addEventListener: () => {},
};
global.window = { addEventListener: () => {} };            // claude 없음 → 로컬 저장 경로
let LS = {};
global.localStorage = { getItem: k => LS[k] ?? null, setItem: (k,v)=>{LS[k]=v},
  removeItem: k => { delete LS[k]; }, };
global.fetch = () => Promise.reject(new Error("no file"));  // data/checkins.json 없음

// 시뮬레이션 날짜를 고정한다 (주 phase 판정이 today() 에 의존)
const FAKE = process.env.FAKE_TODAY;
const RealDate = Date;
global.Date = class extends RealDate {
  constructor(...a){ if(!a.length) return new RealDate(FAKE + "T12:00:00"); return new RealDate(...a); }
  static now(){ return new RealDate(FAKE + "T12:00:00").getTime(); }
};

// 실적 주입
LS["voxplan.checkins.v1"] = JSON.stringify({ v:1, ts:1, done:{},
  actuals: JSON.parse(process.env.ACTUALS || "{}") });

const src = fs.readFileSync("_workspace/ui_app.js", "utf8");
eval(src);

setTimeout(() => {
  const H = nodes.weeks.innerHTML, P = nodes.progress.innerHTML;
  const grab = (re, s) => { const m = s.match(re); return m ? m.slice(1) : null; };
  console.log("today =", FAKE);
  console.log("판정  =", (grab(/verdict verdict--(\w+)"><b>([^<]+)<\/b><span>([^<]*)/, P) || []).join(" | "));
  console.log("절대  =", (grab(/<b>(\d+)<i>%<\/i><\/b><span>([^<]+)</, P) || []).join(" | "));
  console.log("편차  =", (grab(/계획 대비<\/dt><dd class="([^"]*)">([^<]*(?:<i>[^<]*<\/i>)?)/, P) || []).join(" | "));
  // 주별 주말잔여 / 이월
  const secs = H.split('<section class="wk"').slice(1);
  secs.forEach((s, i) => {
    const rem   = grab(/잔여 <b>(\d+)p<\/b>/, s);
    const fut   = /wknd__future/.test(s);
    const clear = /잔여 없음/.test(s);
    const carry = grab(/다음 주 이월 <b>(\d+)p<\/b>/, s);
    const cin   = grab(/이월 \+(\d+)p/, s);
    const sum   = grab(/wk__sum">(\d+) \/ (\d+)p/, s);
    const capw  = /wknd__cap(?!--soft)/.test(s) ? " [용량초과]" : /wknd__cap--soft/.test(s) ? " [이틀필요]" : "";
    console.log(` W${i+1}: 실적 ${sum?sum.join("/"):"?"}p` +
      (fut ? " | 주말=예정" : clear ? " | 주말=잔여없음" : ` | 주말잔여 ${rem?rem[0]:"?"}p`) +
      (cin ? ` | carry_in +${cin[0]}p` : "") + (carry ? ` | carry_out ${carry[0]}p` : "") + capw);
  });
}, 60);
