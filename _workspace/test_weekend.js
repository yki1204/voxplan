/* 주말 보충 칸의 입력란 렌더와 입력 반영을 실제 코드로 확인한다. */
const fs=require("fs");
const PLAN=JSON.parse(fs.readFileSync("_workspace/ui_plan.json","utf8"));
const El=t=>({tag:t,innerHTML:"",outerHTML:"",textContent:"",dataset:{},
  classList:{toggle(){},contains(){return false}},querySelector:()=>null,
  querySelectorAll:()=>[],contains:()=>false,closest:()=>null});
const nodes={plan:El("s"),progress:El("d"),weeks:El("d"),saveState:El("s"),storeNote:El("p")};
nodes.plan.textContent=JSON.stringify(PLAN);
global.document={getElementById:i=>nodes[i]||null,querySelector:()=>null,
  querySelectorAll:()=>[],addEventListener:()=>{}};
global.window={addEventListener:()=>{}};
let LS={}; global.localStorage={getItem:k=>LS[k]??null,setItem:(k,v)=>{LS[k]=v},
  removeItem:k=>{delete LS[k]}};
const RD=Date, T=process.env.FAKE_TODAY;
global.Date=class extends RD{constructor(...a){if(!a.length)return new RD(T+"T12:00:00");return new RD(...a)}
  static now(){return new RD(T+"T12:00:00").getTime()}};
LS["voxplan.checkins.v1"]=JSON.stringify({v:1,ts:1,done:{},actuals:JSON.parse(process.env.ACTUALS)});
eval(fs.readFileSync("_workspace/ui_app.js","utf8"));
setTimeout(()=>{
  const H=nodes.weeks.innerHTML;
  const w1=H.split('<section class="wk"')[1]||"";
  const wk=w1.slice(w1.indexOf('class="wknd'));
  console.log("주말 칸 클래스 :", (wk.match(/class="wknd ([^"]*)"/)||[])[1] || "(없음)");
  const ins=[...wk.matchAll(/data-date="([\d-]+)" data-book="([\w-]+)"[^>]*aria-label="([^"]*)"/g)];
  const vals=[...wk.matchAll(/value="(\d*)" data-date="([\d-]+)" data-book="([\w-]+)"/g)];
  console.log("입력란 개수    :", vals.length);
  vals.forEach(m=>console.log(`  · ${m[3]}  날짜=${m[2]}  현재값="${m[1]}"`));
  console.log("합계 문구      :", (wk.match(/wknd__tot[^>]*>(.*?)<\/p>/)||["","(없음)"])[1]
    .replace(/<[^>]+>/g,""));
  console.log("경고           :", (wk.match(/wknd__cap[^>]*>([^<]*)</)||["","(없음)"])[1]);
  console.log("목표 표시      :", [...wk.matchAll(/ck__tgt">\/(\d+)p/g)].map(m=>m[1]+"p").join(", ")||"(없음)");
},60);
