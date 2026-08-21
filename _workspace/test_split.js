/* 분할 세션일(레바논 단독 5일)에서 '계획대로'가 계획 전량을 저장하는지,
   미터가 2배로 세지 않는지, 주말 이월이 0인지 실제 코드로 확인한다. */
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
const H={};
global.document={getElementById:i=>nodes[i]||null,querySelector:()=>null,
  querySelectorAll:()=>[],addEventListener:(k,f)=>{(H[k]=H[k]||[]).push(f)}};
global.window={addEventListener:()=>{}};
let LS={"voxplan.checkins.v1":JSON.stringify({v:1,ts:1,actuals:{},done:{},found:{}})};
global.localStorage={getItem:k=>LS[k]??null,setItem:(k,v)=>{LS[k]=v},removeItem:k=>{delete LS[k]}};
const RD=Date, T=process.env.FAKE_TODAY||"2026-10-05";
global.Date=class extends RD{constructor(...a){if(!a.length)return new RD(T+"T12:00:00");return new RD(...a)}
  static now(){return new RD(T+"T12:00:00").getTime()}};
eval(fs.readFileSync("_workspace/ui_app.js","utf8"));
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  await wait(60);
  // 모든 녹음일에서 '계획대로' 클릭
  const rec=PLAN.weeks.flatMap(w=>w.days).filter(d=>d.type==="recording");
  for(const d of rec)
    H.click.forEach(f=>f({target:{closest:sel=>sel==="[data-fill]"?{dataset:{fill:d.date}}:null}}));
  await wait(80);
  const st=JSON.parse(LS["voxplan.checkins.v1"]);
  // 분할일 검증
  const split=rec.filter(d=>{const c={};d.blocks.forEach(b=>{if(b.pages)c[b.book]=(c[b.book]||0)+1});
    return Object.values(c).some(v=>v>1)});
  console.log("분할 세션일 저장값:");
  split.forEach(d=>{
    const plan=d.blocks.reduce((s,b)=>s+(b.pages||0),0);
    const saved=Object.values(st.actuals[d.date]||{}).reduce((a,b)=>a+b,0);
    console.log(`  ${d.date}  계획 ${plan}p  저장 ${saved}p  ${plan===saved?"일치":"불일치 ("+(plan-saved)+"p 누락)"}`);
  });
  // 미터 이중계산 검증
  const H2=nodes.weeks.innerHTML;
  const bad=[...H2.matchAll(/data-day="([\d-]+)"[\s\S]*?meter__val">(\d+)<i>\/(\d+)p/g)]
    .filter(m=>m[2]!==m[3]);
  console.log("\n미터 실적≠계획인 날:", bad.length?bad.map(m=>`${m[1]}(${m[2]}/${m[3]})`).join(", "):"없음");
  // 주말 잔여 검증
  const secs=H2.split('<section class="wk"').slice(1);
  console.log("\n주별 주말 잔여 (전부 계획대로 이행 후):");
  secs.forEach((s,i)=>{
    const clear=/잔여 없음/.test(s), done=/보충 완료/.test(s);
    const rem=(s.match(/잔여 <b>(\d+)p<\/b>/)||[])[1];
    console.log(`  W${i+1}: ${clear?"잔여 없음":done?"보충 완료":"잔여 "+rem+"p"}`);
  });
  const total=Object.values(st.actuals).reduce((s,o)=>s+Object.values(o).reduce((a,b)=>a+b,0),0);
  console.log(`\n총 저장 실적: ${total}p / 계획 ${PLAN.totalPages}p  ${total===PLAN.totalPages?"일치":"불일치"}`);
})();
