(function () {
  "use strict";
  var PLAN = JSON.parse(document.getElementById("plan").textContent);
  var CAP = PLAN.cap, WKND_CAP = CAP * 2;
  var BOOKS = {}, PAGED = [];
  PLAN.books.forEach(function (b) { BOOKS[b.id] = b; if (b.paged) PAGED.push(b); });

  /* ── 저장: 브라우저 localStorage 단독 ────────────────────────────────────
     동기·즉시 저장이다. 디바운스를 두지 않는 이유는 localStorage 쓰기가 값싸고,
     "아직 저장 안 된 몇 초"가 존재하지 않는 편이 사용자에게 안전하기 때문이다.
     저장 자체가 막힌 환경(시크릿 창, 사이트 데이터 차단)에서는 조용히 잃는 대신
     그 사실을 화면에 표시한다. */
  var LSKEY = "voxplan.checkins.v1";
  var ST = { v: 1, ts: 0, actuals: {}, done: {}, found: {} };
  var storable = true;

  function norm(o) {
    if (!o || typeof o !== "object") return null;
    return { v: 1, ts: +o.ts || 0,
             actuals: o.actuals && typeof o.actuals === "object" ? o.actuals : {},
             done: o.done && typeof o.done === "object" ? o.done : {},
             found: o.found && typeof o.found === "object" ? o.found : {} };
  }
  function probe() {
    try {
      localStorage.setItem(LSKEY + ".probe", "1");
      localStorage.removeItem(LSKEY + ".probe");
      return true;
    } catch (e) { return false; }
  }
  function stamp(ts) {
    if (!ts) return "";
    var d = new Date(ts);
    return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }
  function status(kind) {
    var note = document.getElementById("storeNote");
    if (note) {
      note.textContent = storable
        ? "이 브라우저에 저장된다. 새로 고침·탭 닫기·브라우저 재시작 후에도 유지된다. 다른 기기·다른 사람에게는 보이지 않는다."
        : "이 브라우저가 저장을 막고 있어 기록이 남지 않는다. 시크릿 창이면 일반 창에서 열어라.";
      note.dataset.mode = storable ? "ok" : "blocked";
    }
    var el = document.getElementById("saveState");
    if (!el) return;
    el.textContent = !storable ? "저장 불가"
      : kind === "idle" ? "기록 없음"
      : "저장됨" + (ST.ts ? " · " + stamp(ST.ts) : "");
    el.dataset.kind = !storable ? "err" : kind;
  }
  function save() {
    ST.ts = Date.now();
    try { localStorage.setItem(LSKEY, JSON.stringify(ST)); storable = true; status("saved"); }
    catch (e) { storable = false; status("err"); }
  }
  function boot() {
    storable = probe();
    if (storable) { try { var o = norm(JSON.parse(localStorage.getItem(LSKEY))); if (o) ST = o; }
                    catch (e) {} }
    render();
    status(ST.ts ? "saved" : "idle");
  }

  /* ── 실적 접근자 ──────────────────────────────────────────────────────── */
  function act(date, book) { var d = ST.actuals[date]; return (d && +d[book]) || 0; }
  function setAct(date, book, v) {
    var d = ST.actuals[date] || (ST.actuals[date] = {});
    if (v > 0) d[book] = v; else delete d[book];
    if (!Object.keys(d).length) delete ST.actuals[date];
  }
  function today() {
    var d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" +
           String(d.getDate()).padStart(2, "0");
  }

  /* 그 날짜에 실적이 하나라도 입력되었는가 */
  function logged(date) {
    var d = ST.actuals[date];
    if (!d) return false;
    for (var k in d) if (+d[k] > 0) return true;
    return false;
  }
  /* 주에 실적이 하나라도 있는가 (평일 + 주말 보충) */
  function weekLogged(w) {
    for (var i = 0; i < w.days.length; i++) if (logged(w.days[i].date)) return true;
    return logged(w.weekend);
  }

  /* ── 이월 계산 ────────────────────────────────────────────────────────────
     주 단위로 정산하고 carry_in 을 순서대로 누적한다.

     정산 대상은 "지난 날" 또는 "실적이 입력된 날"이다. 날짜만으로 판정하면
     일정 시작 전에 미리 입력해도 미달이 잡히지 않아, 주말 보충 칸이 영원히
     '예정'에 머문다. 반대로 아직 오지 않았고 실적도 없는 날은 미달이 아니다. */
  function computeWeeks() {
    var t = today(), carry = {}, out = [];
    PAGED.forEach(function (b) { carry[b.id] = 0; });
    PLAN.weeks.forEach(function (w) {
      var mon = w.days[0].date, fri = w.days[w.days.length - 1].date;
      // future: 시작 전이고 실적도 없음 | current: 진행 중 | past: 금요일이 지남
      var phase = t > fri ? "past" : (t >= mon || weekLogged(w)) ? "current" : "future";
      // weekendTotal = 주말에 배정된 양, outstanding = 그중 아직 못 한 양
      var row = { n: w.n, span: w.span, weekend: w.weekend, phase: phase, books: {},
                  weekendTotal: 0, outstanding: 0, carryOutTotal: 0, carryInTotal: 0,
                  planTotal: 0, planElapsed: 0, actTotal: 0 };
      PAGED.forEach(function (b) {
        var P = 0, Pel = 0, aWd = 0;
        w.days.forEach(function (d) {
          // 지난 날이거나 실적이 입력된 날만 정산한다
          var elapsed = phase === "past" || d.date < t || logged(d.date);
          d.blocks.forEach(function (bl) {
            if (bl.book !== b.id || !bl.pages) return;
            P += bl.pages; if (elapsed) Pel += bl.pages;
          });
          aWd += act(d.date, b.id);
        });
        var cin = carry[b.id], due = Pel + cin, aWe = act(w.weekend, b.id);
        var rem = 0, cout = 0;
        if (phase !== "future") {
          rem  = Math.max(0, due - aWd);
          cout = Math.max(0, due - aWd - aWe);
        }
        // 부채는 다음에 실제로 돌아오는 한 주가 갚는다. past 만 이월을 전달하고,
        // current/future 는 받은 뒤 비운다 — 비우지 않으면 이후 모든 주에 같은 이월이 표시된다.
        carry[b.id] = phase === "past" ? cout : 0;
        row.books[b.id] = { plan: P, planElapsed: Pel, carryIn: cin, due: due,
                            actWd: aWd, actWe: aWe, weekendRem: rem, carryOut: cout,
                            ahead: Math.max(0, aWd + aWe - due) };
        row.weekendTotal += rem; row.outstanding += Math.max(0, rem - aWe);
        row.carryOutTotal += cout; row.carryInTotal += cin;
        row.planTotal += P; row.planElapsed += Pel; row.actTotal += aWd + aWe;
      });
      out.push(row);
    });
    return out;
  }

  /* ── 진행률: 절대 진행률과 계획 대비 편차를 함께 낸다 ──────────────────── */
  function progress() {
    var t = today(), o = { books: {}, recorded: 0, planToDate: 0,
                           total: PLAN.totalPages, started: false };
    PAGED.forEach(function (b) { o.books[b.id] = { rec: 0, planToDate: 0, total: b.total }; });
    PLAN.weeks.forEach(function (w) { w.days.forEach(function (d) {
      if (d.date > t) return;
      d.blocks.forEach(function (bl) {
        if (!bl.pages || !BOOKS[bl.book].paged) return;
        o.books[bl.book].planToDate += bl.pages; o.planToDate += bl.pages;
      });
    }); });
    Object.keys(ST.actuals).forEach(function (date) {
      Object.keys(ST.actuals[date]).forEach(function (bid) {
        if (!o.books[bid]) return;
        var v = +ST.actuals[date][bid] || 0;
        o.books[bid].rec += v; o.recorded += v;
        if (v) o.started = true;
      });
    });
    return o;
  }

  function verdict(weeks, pr) {
    if (!pr.started) return { k: "idle", t: "시작 전",
      d: "실적이 없다. 각 날짜 칸에 실제 녹음한 페이지를 입력하면 여기서 상태를 판정한다." };
    var done = weeks.filter(function (w) { return w.phase === "past"; });
    var over = done.filter(function (w) { return w.weekendTotal > WKND_CAP; });
    if (over.length) return { k: "bad", t: "재계획 필요",
      d: "W" + over.map(function (w) { return w.n; }).join(", W") + " 주말잔여가 주말 용량 " +
         WKND_CAP + "p를 넘었다 — 이월로 흡수할 수 없다." };
    var streak = 0, max = 0;
    done.forEach(function (w) {
      if (w.carryOutTotal > 0) { streak++; max = Math.max(max, streak); } else streak = 0; });
    if (max >= 2) return { k: "bad", t: "재계획 필요",
      d: max + "주 연속 이월 — 계획된 일부하가 실제 처리량보다 높다." };
    var live = weeks.filter(function (w) { return w.phase === "current"; });
    var liveOver = live.filter(function (w) { return w.weekendTotal > WKND_CAP; });
    if (liveOver.length) return { k: "warn", t: "주의",
      d: "이번 주 잔여가 주말 용량 " + WKND_CAP + "p를 넘는다 — 평일 중 만회하지 않으면 이월된다." };
    if (max >= 1) {
      var last = done[done.length - 1];
      return { k: "warn", t: "주의",
        d: "이월 " + (last ? last.carryOutTotal : 0) +
           "p — 다음 주 잔여에 합산되어 있다. 그 주 안에 갚으면 정상으로 돌아온다." };
    }
    if (weeks.some(function (w) { return w.phase !== "future" && w.weekendTotal > CAP; }))
      return { k: "warn", t: "주의", d: "주말잔여가 하루 상한 " + CAP + "p를 넘는다 — 주말 이틀 필요." };
    if (weeks.some(function (w) { return w.phase !== "future" && w.weekendTotal > 0; }))
      return { k: "ok", t: "흡수 가능", d: "미달분이 주말 보충 범위 안에 있다. 평일 계획 유지." };
    return { k: "ok", t: "계획대로", d: "미달 없음. 평일 계획 유지." };
  }

  /* ── 숨겨둔 쿠폰 ──────────────────────────────────────────────────────────
     체크인 마일스톤에 걸어 두었다. 발견 전에는 화면에 아무 흔적도 없고,
     발견하면 한 번 팝업으로 축하한 뒤 획득 목록에 남는다 — 나중에 다시 열어
     캡처할 수 있어야 하므로 사라지게 두지 않는다. */
  var COUPONS = [
    { id: "coffee",   code: "COFFEE",   emoji: "☕", name: "커피 쿠폰",
      lead: "첫 녹음을 기록했다",
      note: "시작이 제일 어렵다. 한 잔 하고 가자.",
      test: function (pr) { return pr.recorded > 0; } },
    { id: "icecream", code: "ICECREAM", emoji: "🍨", name: "아이스크림 쿠폰",
      lead: "전체 분량의 절반을 넘겼다",
      note: "목도 마음도 식힐 때다.",
      test: function (pr) { return pr.recorded >= Math.ceil(pr.total / 2); } },
    { id: "gopchang", code: "GOPCHANG", emoji: "🔥", name: "곱창 쿠폰",
      lead: "마지막 일정까지 전부 끝냈다",
      note: "820페이지와 전일 일정 전부. 이건 곱창이어야 한다.",
      grand: true,
      test: function (pr) { return allComplete(pr); } }
  ];

  /* 전체 완료: 페이지 도서는 전량 이상, 전일 일정(전일 녹음·편집)은 모두 완료 */
  function allComplete(pr) {
    for (var i = 0; i < PAGED.length; i++) {
      var b = PAGED[i];
      if (pr.books[b.id].rec < b.total) return false;
    }
    var ok = true;
    PLAN.weeks.forEach(function (w) { w.days.forEach(function (d) {
      if (d.type === "full_day" && !ST.done[d.date]) ok = false;
    }); });
    return ok;
  }

  function serial(c, ts) {
    var d = new Date(ts), ymd = String(d.getFullYear()).slice(2) +
      String(d.getMonth() + 1).padStart(2, "0") + String(d.getDate()).padStart(2, "0");
    var seed = c.code + ymd, n = 0;
    for (var i = 0; i < seed.length; i++) n = (n * 31 + seed.charCodeAt(i)) % 1296;
    return "VXP-" + c.code + "-" + ymd + "-" +
           n.toString(36).toUpperCase().padStart(2, "0");
  }

  var queue = [];
  function checkCoupons() {
    var pr = progress(), fresh = [];
    COUPONS.forEach(function (c) {
      if (ST.found[c.id]) return;
      if (!c.test(pr)) return;
      ST.found[c.id] = Date.now();
      fresh.push(c);
    });
    if (!fresh.length) return;
    save(); renderCoupons();
    queue = queue.concat(fresh);
    if (queue.length === fresh.length) showNext();
  }
  function showNext() {
    var c = queue[0];
    if (!c) return;
    var dlg = document.getElementById("cpDlg");
    if (!dlg) { queue.shift(); return showNext(); }
    dlg.innerHTML =
      '<div class="cp' + (c.grand ? " cp--grand" : "") + '">' +
        '<p class="cp__eyebrow">' + (c.grand ? "최종 보상" : "숨겨둔 쿠폰 발견") + '</p>' +
        '<h2 class="cp__hd">축하합니다 — ' + esc(c.lead) + '</h2>' +
        '<div class="tk">' +
          '<span class="tk__emoji" aria-hidden="true">' + c.emoji + '</span>' +
          '<span class="tk__name">' + esc(c.name) + '</span>' +
          '<span class="tk__note">' + esc(c.note) + '</span>' +
          '<span class="tk__sn">' + serial(c, ST.found[c.id]) + '</span>' +
        '</div>' +
        '<p class="cp__ask"><b>이 화면을 캡처해서 개발자에게 보내주세요.</b><br>' +
          '쿠폰 번호가 함께 찍혀야 사용할 수 있습니다.</p>' +
        '<button class="cp__close" type="button" data-cpclose>받았습니다</button>' +
      '</div>';
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
  }
  function closeCoupon() {
    var dlg = document.getElementById("cpDlg");
    if (dlg) { if (dlg.close) dlg.close(); else dlg.removeAttribute("open"); }
    queue.shift();
    if (queue.length) setTimeout(showNext, 260);
  }
  function renderCoupons() {
    var box = document.getElementById("coupons");
    if (!box) return;
    var got = COUPONS.filter(function (c) { return ST.found[c.id]; });
    if (!got.length) { box.innerHTML = ""; box.hidden = true; return; }
    box.hidden = false;
    box.innerHTML = '<span class="cpr__label">획득한 쿠폰</span>' +
      got.map(function (c) {
        return '<button class="cpr__chip" type="button" data-cpopen="' + c.id + '">' +
          '<span aria-hidden="true">' + c.emoji + '</span>' + esc(c.name) + '</button>';
      }).join("") +
      '<span class="cpr__hint">눌러서 다시 열고 캡처할 수 있습니다</span>';
  }

  /* ── 렌더 조각 ────────────────────────────────────────────────────────── */
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function md(iso) { var p = iso.split("-"); return +p[1] + "/" + +p[2]; }

  function progressHTML(weeks, pr) {
    var v = verdict(weeks, pr), diff = pr.recorded - pr.planToDate;
    var pct = pr.total ? Math.round(pr.recorded / pr.total * 100) : 0;
    var R = 42, CIRC = 2 * Math.PI * R;
    return '<div class="pg"><div class="pg__ring">' +
      '<svg viewBox="0 0 100 100" aria-hidden="true">' +
        '<circle class="pg__trk" cx="50" cy="50" r="' + R + '"></circle>' +
        '<circle class="pg__arc" cx="50" cy="50" r="' + R + '" stroke-dasharray="' +
          CIRC.toFixed(1) + '" stroke-dashoffset="' + (CIRC * (1 - pct / 100)).toFixed(1) +
        '"></circle></svg>' +
      '<div class="pg__ctr"><b>' + pct + '<i>%</i></b><span>' + pr.recorded + ' / ' +
        pr.total + 'p</span></div></div>' +
      '<div class="pg__side">' +
        '<div class="verdict verdict--' + v.k + '"><b>' + v.t + '</b><span>' + esc(v.d) +
          '</span></div>' +
        '<dl class="pg__stats">' +
          '<div><dt>오늘까지 계획</dt><dd>' + pr.planToDate + '<i>p</i></dd></div>' +
          '<div><dt>계획 대비</dt><dd class="' +
            (!pr.started ? "" : diff < 0 ? "is-neg" : diff > 0 ? "is-pos" : "") + '">' +
            (pr.started ? (diff > 0 ? "+" : "") + diff + "<i>p</i>" : "<i>실적 없음</i>") +
          '</dd></div>' +
          '<div><dt>잔여</dt><dd>' + Math.max(0, pr.total - pr.recorded) + '<i>p</i></dd></div>' +
        '</dl>' +
        '<ul class="pg__books">' + PAGED.map(function (b) {
          var o = pr.books[b.id];
          var p = o.total ? Math.min(100, o.rec / o.total * 100) : 0;
          var pl = o.total ? Math.min(100, o.planToDate / o.total * 100) : 0;
          return '<li style="--bk:var(--bk-' + b.hue + ')">' +
            '<span class="pg__nm">' + esc(b.name) + '</span>' +
            '<span class="pg__bar"><i style="width:' + p.toFixed(1) + '%"></i>' +
              '<u style="left:' + pl.toFixed(1) + '%" title="오늘까지 계획"></u></span>' +
            '<span class="pg__pg">' + o.rec + '<em>/' + o.total + 'p</em></span></li>';
        }).join("") + '</ul></div></div>';
  }

  function meterHTML(sum, planned) {
    var hi = sum > CAP ? " is-over" : sum > CAP - 2 ? " is-high" : "";
    return '<div class="meter' + hi + '"><div class="meter__track">' +
      '<div class="meter__fill" style="width:' + Math.min(100, sum / CAP * 100).toFixed(1) + '%"></div>' +
      '<span class="meter__tick" style="left:' + (PLAN.bandLo / CAP * 100).toFixed(1) + '%"></span>' +
      '<span class="meter__plan" style="left:' + (planned / CAP * 100).toFixed(1) + '%"></span>' +
      '</div><span class="meter__val">' + sum + '<i>/' + planned + 'p</i></span></div>';
  }

  function dayHTML(d) {
    if (d.type === "full_day") {
      var bl = d.blocks[0], on = !!ST.done[d.date];
      return '<div class="day day--full' + (on ? " is-done" : "") + '" data-day="' + d.date +
        '" style="--bk:var(--bk-' + BOOKS[bl.book].hue + ')">' +
        '<div class="day__hd"><span class="day__date">' + md(d.date) + '</span>' +
          '<span class="day__dow">' + d.dow + '</span></div>' +
        '<div class="day__full"><span class="day__fulltag">' + esc(bl.label) + '</span>' +
          '<span class="day__fullbook">' + esc(BOOKS[bl.book].name) + '</span></div>' +
        '<label class="chk"><input type="checkbox" data-done="' + d.date + '"' +
          (on ? " checked" : "") + '><span>완료</span></label></div>';
    }
    var sum = 0;
    d.blocks.forEach(function (bl) { sum += act(d.date, bl.book); });
    return '<div class="day" data-day="' + d.date + '">' +
      '<div class="day__hd"><span class="day__date">' + md(d.date) + '</span>' +
        '<span class="day__dow">' + d.dow + '</span>' +
        '<button class="day__fill" type="button" data-fill="' + d.date +
          '" title="계획대로 채우기">계획대로</button></div>' +
      '<ul class="day__blocks">' + d.blocks.map(function (bl) {
        var a = act(d.date, bl.book);
        return '<li class="ck' + (a === 0 ? "" : a >= bl.pages ? " is-met" : " is-short") +
          '" style="--bk:var(--bk-' + BOOKS[bl.book].hue + ')">' +
          '<span class="ck__dot"></span><span class="ck__nm">' + esc(BOOKS[bl.book].name) +
            (bl.session ? '<em>' + esc(bl.session) + '</em>' : "") + '</span>' +
          '<input class="ck__in" type="number" inputmode="numeric" min="0" max="199" placeholder="0"' +
            ' value="' + (a || "") + '" data-date="' + d.date + '" data-book="' + bl.book +
            '" aria-label="' + esc(BOOKS[bl.book].name) + ' ' + md(d.date) +
            ' 실제 녹음 페이지 (목표 ' + bl.pages + ')">' +
          '<span class="ck__tgt">/' + bl.pages + 'p</span></li>';
      }).join("") + '</ul>' +
      (d.note ? '<p class="day__note">' + esc(d.note) + '</p>' : "") +
      meterHTML(sum, d.total) + '</div>';
  }

  function totLine(wr) {
    if (wr.outstanding === 0)
      return '<p class="wknd__tot is-done">보충 완료 · ' + wr.weekendTotal + 'p</p>';
    return '<p class="wknd__tot">' + (wr.phase === "current" ? "현재 " : "") +
           '잔여 <b>' + wr.outstanding + 'p</b>' +
           (wr.weekendTotal !== wr.outstanding
             ? ' <em>· 배정 ' + wr.weekendTotal + 'p</em>' : "") + '</p>';
  }

  function weekendHTML(wr) {
    var cls = wr.phase === "future" ? "is-future"
            : wr.outstanding === 0 ? "is-clear"
            : wr.weekendTotal > WKND_CAP ? "is-over"
            : wr.weekendTotal > CAP ? "is-warn" : "";
    var body;
    if (wr.phase === "future") {
      body = '<p class="wknd__clear wknd__future">예정</p>';
    } else if (wr.weekendTotal === 0) {
      body = '<p class="wknd__clear">잔여 없음</p>';
    } else {
      body = '<ul class="day__blocks">' + PAGED.filter(function (b) {
          return wr.books[b.id].weekendRem > 0 || act(wr.weekend, b.id) > 0;
        }).map(function (b) {
          var o = wr.books[b.id], a = act(wr.weekend, b.id);
          return '<li class="ck' + (a === 0 ? "" : a >= o.weekendRem ? " is-met" : " is-short") +
            '" style="--bk:var(--bk-' + b.hue + ')">' +
            '<span class="ck__dot"></span><span class="ck__nm">' + esc(b.name) + '</span>' +
            '<input class="ck__in" type="number" inputmode="numeric" min="0" max="199" placeholder="0"' +
              ' value="' + (a || "") + '" data-date="' + wr.weekend + '" data-book="' + b.id +
              '" aria-label="' + esc(b.name) + ' 주말 보충 페이지 (잔여 ' + o.weekendRem + ')">' +
            '<span class="ck__tgt">/' + o.weekendRem + 'p</span></li>';
        }).join("") + '</ul>' +
        totLine(wr);
    }
    var cap = wr.outstanding === 0 ? ""
      : wr.weekendTotal > WKND_CAP
        ? '<p class="wknd__cap">주말 용량 ' + WKND_CAP + 'p 초과 — 재계획 검토</p>'
        : wr.weekendTotal > CAP ? '<p class="wknd__cap wknd__cap--soft">주말 이틀 필요</p>' : "";
    var carry = wr.carryOutTotal > 0 && wr.phase === "past"
      ? '<p class="wknd__carry">다음 주 이월 <b>' + wr.carryOutTotal + 'p</b></p>' : "";
    return '<div class="wknd ' + cls + '" data-wknd="' + wr.n + '">' +
      '<div class="day__hd"><span class="day__date">토·일</span>' +
        '<span class="day__dow">보충</span></div>' + body + cap + carry + '</div>';
  }

  function weekHeadHTML(wr) {
    return '<span class="wk__n">W' + wr.n + '</span><span class="wk__span">' + wr.span + '</span>' +
      (wr.carryInTotal ? '<span class="wk__carry">이월 +' + wr.carryInTotal + 'p</span>' : "") +
      '<span class="wk__sum">' + wr.actTotal + ' / ' + wr.planTotal + 'p</span>';
  }

  function render() {
    var weeks = computeWeeks(), pr = progress();
    document.getElementById("progress").innerHTML = progressHTML(weeks, pr);
    renderCoupons();
    document.getElementById("weeks").innerHTML = PLAN.weeks.map(function (w, i) {
      return '<section class="wk" data-wk="' + w.n + '">' +
        '<header class="wk__hd" data-wkhd="' + w.n + '">' + weekHeadHTML(weeks[i]) + '</header>' +
        '<div class="wk__grid">' + w.days.map(dayHTML).join("") +
          weekendHTML(weeks[i]) + '</div></section>';
    }).join("");
  }

  /* 입력 중에는 전체를 다시 그리지 않는다 — 포커스와 커서를 잃기 때문이다.
     파생 영역(진행률·주 헤더·주말 칸·해당 일자 미터)만 갱신한다. */
  function refresh(activeEl) {
    var weeks = computeWeeks(), pr = progress();
    document.getElementById("progress").innerHTML = progressHTML(weeks, pr);
    PLAN.weeks.forEach(function (w, i) {
      var wr = weeks[i];
      var hd = document.querySelector('[data-wkhd="' + w.n + '"]');
      if (hd) hd.innerHTML = weekHeadHTML(wr);
      var wk = document.querySelector('[data-wknd="' + w.n + '"]');
      if (wk && !(activeEl && wk.contains(activeEl))) {
        wk.outerHTML = weekendHTML(wr);
      } else if (wk) {
        // 이 칸에서 입력 중이다 — 입력란은 건드리지 않고 합계·경고만 갱신한다
        var tot = wk.querySelector(".wknd__tot");
        if (tot) tot.outerHTML = totLine(wr);
        wk.className = "wknd " + (wr.outstanding === 0 ? "is-clear"
          : wr.weekendTotal > WKND_CAP ? "is-over"
          : wr.weekendTotal > CAP ? "is-warn" : "");
      }
      w.days.forEach(function (d) {
        if (d.type === "full_day") return;
        var cell = document.querySelector('[data-day="' + d.date + '"]');
        if (!cell) return;
        var sum = 0;
        d.blocks.forEach(function (bl) { sum += act(d.date, bl.book); });
        var m = cell.querySelector(".meter");
        if (m) m.outerHTML = meterHTML(sum, d.total);
        cell.querySelectorAll(".ck").forEach(function (li, idx) {
          var bl = d.blocks[idx]; if (!bl) return;
          var a = act(d.date, bl.book);
          li.classList.toggle("is-met", a > 0 && a >= bl.pages);
          li.classList.toggle("is-short", a > 0 && a < bl.pages);
        });
      });
    });
  }

  var cpTimer = null;
  function laterCheck() { clearTimeout(cpTimer); cpTimer = setTimeout(checkCoupons, 900); }

  /* ── 이벤트 ───────────────────────────────────────────────────────────── */
  document.addEventListener("input", function (e) {
    var t = e.target;
    if (!t.classList || !t.classList.contains("ck__in")) return;
    setAct(t.dataset.date, t.dataset.book,
           Math.max(0, Math.min(199, parseInt(t.value, 10) || 0)));
    save(); refresh(t); laterCheck();
  });
  document.addEventListener("change", function (e) {
    var t = e.target;
    if (!t.dataset || !t.dataset.done) return;
    if (t.checked) ST.done[t.dataset.done] = true; else delete ST.done[t.dataset.done];
    save(); laterCheck();
  });
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (t.closest && t.closest("[data-cpclose]")) { closeCoupon(); return; }
    var open = t.closest && t.closest("[data-cpopen]");
    if (open) {
      var c = COUPONS.filter(function (x) { return x.id === open.dataset.cpopen; })[0];
      if (c) { queue = [c]; showNext(); }
      return;
    }
    var b = t.closest && t.closest("[data-fill]");
    if (!b) return;
    PLAN.weeks.forEach(function (w) { w.days.forEach(function (d) {
      if (d.date !== b.dataset.fill) return;
      d.blocks.forEach(function (bl) { if (bl.pages) setAct(d.date, bl.book, bl.pages); });
    }); });
    save(); render(); laterCheck();
  });

  boot();
})();
