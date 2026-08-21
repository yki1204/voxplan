/* 3개 동시 해금 시 '받았습니다' 를 누를 때마다 다음 쿠폰이 뜨는지 (비동기) */
const fs=require("fs");
const PLAN=JSON.parse(fs.readFileSync("_workspace/ui_plan.json","utf8"));
const mk=t=>({tag:t,innerHTML:"",textContent:"",hidden:false,dataset:{},
  classList:{toggle(){},contains(){return false}},querySelector:()=>null,
  querySelectorAll:()=>[],contains:()=>false,closest:()=>null,
  showModal(){this._open=true},close(){this._open=false},
  setAttribute(){this._open=true},removeAttribute(){this._open=false}});
const nodes={plan:mk("s"),progress:mk("d"),weeks:mk("d"),saveState:mk("s"),
  storeNote:mk("p"),coupons:mk("d"),cpDlg:mk("dialog")};
nodes.plan.textContent=JSON.stringify(PLAN);
const handlers={};
global.document={getElementById:i=>nodes[i]||null,querySelector:()=>null,
  querySelectorAll:()=>[],addEventListener:(k,f)=>{(handlers[k]=handlers[k]||[]).push(f)}};
global.window={addEventListener:()=>{}};
let LS={}; global.localStorage={getItem:k=>LS[k]??null,setItem:(k,v)=>{LS[k]=v},
  removeItem:k=>{delete LS[k]}};
const RD=Date;
global.Date=class extends RD{constructor(...a){if(!a.length)return new RD("2026-10-02T12:00:00");return new RD(...a)}
  static now(){return new RD("2026-10-02T12:00:00").getTime()}};

const A={},D={};
PLAN.weeks.flatMap(w=>w.days).forEach(d=>{
  if(d.type==="full_day"){ D[d.date]=true; return; }
  const o={}; d.blocks.forEach(b=>{ if(b.pages) o[b.book]=(o[b.book]||0)+b.pages; });
  if(Object.keys(o).length) A[d.date]=o;
});
LS["voxplan.checkins.v1"]=JSON.stringify({v:1,ts:1,actuals:A,done:D,found:{}});
eval(fs.readFileSync("_workspace/ui_app.js","utf8"));

const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  await wait(60);
  // 실제 사용자 흐름: 입력 이벤트 → 900ms 후 판정
  handlers.input.forEach(f=>f({target:{classList:{contains:c=>c==="ck__in"},
    dataset:{date:"2026-08-25",book:"lebanon"},value:"15"}}));
  await wait(1000);
  const seq=[];
  for(let i=0;i<5;i++){
    const h=nodes.cpDlg.innerHTML;
    const nm=(h.match(/tk__name">([^<]*)/)||[])[1];
    if(!nm||!nodes.cpDlg._open) break;
    seq.push(nm+(/cp--grand/.test(h)?" [최종]":"")+" / "+(h.match(/tk__sn">([^<]*)/)||[])[1]);
    handlers.click.forEach(f=>f({target:{closest:s=>s==="[data-cpclose]"?{}:null}}));
    await wait(320);
  }
  console.log("팝업 순차:");
  seq.forEach((x,i)=>console.log(`  ${i+1}. ${x}`));
  console.log("마지막 닫은 뒤 열림 상태:", nodes.cpDlg._open===false?"닫힘 (정상)":"열린 채 (문제)");
  // 재열기: 획득 칩 클릭
  handlers.click.forEach(f=>f({target:{closest:s=>s==="[data-cpopen]"?{dataset:{cpopen:"gopchang"}}:null}}));
  await wait(50);
  const re=(nodes.cpDlg.innerHTML.match(/tk__name">([^<]*)/)||[])[1];
  console.log("칩으로 재열기:", re||"(실패)", nodes.cpDlg._open?"(열림)":"(닫힘)");
  console.log("획득 칩:", [...nodes.coupons.innerHTML.matchAll(/data-cpopen="(\w+)"/g)].map(m=>m[1]).join(", "));
})();
