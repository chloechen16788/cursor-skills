const params = new URLSearchParams(location.search);
const FAST = params.get("fast") === "1";
const LIFE_MS = FAST ? 4500 : 30000;
const REMNANT_MS = FAST ? 4500 : 30000;
const DISRUPT_MS = FAST ? 1600 : 6000;
const WHEEL_MS = FAST ? 1200 : 5000;
const LOAD_MS = FAST ? 350 : 2000;
const STORE_KEY = "stellar-spectrum-life-v1";

const state = load();
let token = 0;
let raf = 0;
let pendingId = null;
let spinning = false;

const massText = document.getElementById("mass-text");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const ring = document.getElementById("ring");
const redeemNote = document.getElementById("redeem-note");

function load() {
  const blank = { mass: 0, unlocks: {}, spinDate: "", spinsUsed: 0, bonusSpins: 0, credits: 0, redeemed: [] };
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return blank;
    const data = JSON.parse(raw);
    return Object.assign(blank, data, { unlocks: data.unlocks || {}, redeemed: data.redeemed || [] });
  } catch (err) {
    return blank;
  }
}

function save() {
  localStorage.setItem(STORE_KEY, JSON.stringify(state));
}

function renderMass() {
  massText.textContent = String(state.mass);
}

function show(name) {
  document.querySelectorAll(".screen").forEach((el) => {
    el.classList.toggle("active", el.id === "screen-" + name);
  });
}

function shanghaiDate() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(new Date());
}

function rollDaily() {
  const today = shanghaiDate();
  if (state.spinDate !== today) {
    state.spinDate = today;
    state.spinsUsed = 0;
    save();
  }
}

function freeRemaining() {
  rollDaily();
  return Math.max(0, 3 - state.spinsUsed) + state.bonusSpins;
}

function consumeFree() {
  rollDaily();
  if (state.spinsUsed < 3) state.spinsUsed += 1;
  else if (state.bonusSpins > 0) state.bonusSpins -= 1;
  save();
}

function goHome() {
  token += 1;
  if (raf) cancelAnimationFrame(raf);
  raf = 0;
  spinning = false;
  document.getElementById("ad").hidden = true;
  show("home");
  renderMass();
  searchInput.focus();
}

function buildWheel() {
  const wheel = document.getElementById("wheel");
  const stops = WHEEL_SECTORS.map((s, i) => `${s.color} ${i * 36}deg ${(i + 1) * 36}deg`).join(", ");
  wheel.style.background = `conic-gradient(from -18deg, ${stops})`;
  WHEEL_SECTORS.forEach((s, i) => {
    const el = document.createElement("div");
    el.className = "wheel-label";
    el.textContent = s.label + (s.delta ? " ☀️" : "");
    const ang = i * 36;
    const rad = (ang * Math.PI) / 180;
    const x = 50 + Math.sin(rad) * 36;
    const y = 50 - Math.cos(rad) * 36;
    let rot = ang;
    if (ang > 90 && ang < 270) rot += 180;
    el.style.left = x + "%";
    el.style.top = y + "%";
    el.style.transform = `translate(-50%, -50%) rotate(${rot}deg)`;
    wheel.appendChild(el);
  });
  setArrow(180);
}

function setArrow(deg) {
  document.getElementById("arrow").style.transform = `translate(-50%, -100%) rotate(${deg}deg)`;
}

function updateSpinLabel() {
  rollDaily();
  const daily = Math.max(0, 3 - state.spinsUsed);
  document.getElementById("spin-left").textContent =
    `今日免费 ${daily}/3` + (state.bonusSpins ? `，免广告 ${state.bonusSpins}` : "");
}

function openWheel() {
  updateSpinLabel();
  document.getElementById("wheel-result").textContent = "";
  show("wheel");
}

function watchAd() {
  const ad = document.getElementById("ad");
  const count = document.getElementById("ad-count");
  const skip = document.getElementById("ad-skip");
  ad.hidden = false;
  return new Promise((resolve) => {
    let left = FAST ? 0.6 : 3;
    count.textContent = String(Math.ceil(left));
    const timer = setInterval(() => {
      left -= FAST ? 0.3 : 0.5;
      count.textContent = String(Math.max(0, Math.ceil(left)));
      if (left <= 0) finish();
    }, FAST ? 200 : 500);
    skip.onclick = () => finish();
    function finish() {
      clearInterval(timer);
      skip.onclick = null;
      ad.hidden = true;
      resolve();
    }
  });
}

function applyPrize(sector) {
  if (sector.delta > 0) state.mass += sector.delta;
  else if (sector.delta < 0) state.mass = Math.max(0, state.mass + sector.delta);
  save();
  renderMass();
  const word = sector.delta === 0 ? "谢谢光临，质量不变" : `${sector.label}，当前 ${state.mass} ☀️`;
  document.getElementById("wheel-result").textContent = word;
  updateSpinLabel();
}

function spinTo(index) {
  spinning = true;
  const startBtn = document.getElementById("wheel-start");
  startBtn.disabled = true;
  const target = index * 36;
  const base = FAST ? 360 : 1200;
  let end = base;
  const mod = ((end % 360) + 360) % 360;
  let delta = target - mod;
  if (delta < 0) delta += 360;
  end += delta;
  const t0 = performance.now();
  const my = ++token;
  function frame(now) {
    if (my !== token) return;
    const u = Math.min(1, (now - t0) / WHEEL_MS);
    const p = 1 - Math.pow(1 - u, 3);
    setArrow(p * end);
    if (u < 1) raf = requestAnimationFrame(frame);
    else {
      spinning = false;
      startBtn.disabled = false;
      setArrow(target);
      applyPrize(WHEEL_SECTORS[index]);
    }
  }
  raf = requestAnimationFrame(frame);
}

async function onSpin() {
  if (spinning) return;
  if (freeRemaining() > 0) {
    consumeFree();
    updateSpinLabel();
    spinTo(Math.floor(Math.random() * WHEEL_SECTORS.length));
    return;
  }
  await watchAd();
  if (document.getElementById("screen-wheel").classList.contains("active")) {
    spinTo(Math.floor(Math.random() * WHEEL_SECTORS.length));
  }
}

function setRing(text, big) {
  const box = document.getElementById("ring-text");
  box.textContent = text;
  ring.classList.toggle("bigword", !!big);
  box.scrollTop = 0;
}

function openLecturer() {
  redeemNote.textContent = state.credits ? `讲解额度 ${state.credits}` : "";
  show("lecturer");
  document.getElementById("ask-input").focus();
}

function applyCode(raw) {
  const typed = String(raw || "").trim().replace(/!/g, "！");
  const spec = CODES[typed];
  if (!spec) {
    redeemNote.textContent = "无奖励通知";
    setRing("无奖励通知", true);
    return;
  }
  if (state.redeemed.includes(typed)) {
    redeemNote.textContent = "该兑换码已经使用过";
    setRing("该兑换码已经使用过", false);
    return;
  }
  state.redeemed.push(typed);
  if (spec.kind === "mass") state.mass += spec.amount;
  if (spec.kind === "spins") state.bonusSpins += spec.amount;
  if (spec.kind === "credits") state.credits += spec.amount;
  if (spec.kind === "unlock") spec.ids.forEach((id) => { state.unlocks[id] = true; });
  save();
  renderMass();
  redeemNote.textContent = spec.text;
  setRing(spec.text, false);
}

function onAsk(raw) {
  const text = answerLecturer(raw, state);
  setRing(text, text === "扎啤吧" || text === "你猜");
}

function openFail() {
  show("fail");
}

function openUnlock(id) {
  pendingId = id;
  const spec = CLASSES[id];
  const img = document.getElementById("unlock-star");
  img.src = ASSET + spec.stages[0].sprite;
  img.alt = spec.title;
  const owned = !!state.unlocks[id];
  document.getElementById("unlock-cost").textContent = owned ? "已解锁" : `${spec.cost} ☀️`;
  document.getElementById("unlock-line").textContent = owned
    ? "已永久解锁，可直接推演"
    : `消耗 ${spec.cost} ☀️ 永久解锁`;
  document.getElementById("unlock-msg").textContent = "";
  show("unlock");
  document.getElementById("unlock-confirm").focus();
}

function confirmUnlock() {
  if (!pendingId) return;
  const spec = CLASSES[pendingId];
  if (!state.unlocks[pendingId]) {
    if (state.mass < spec.cost) {
      document.getElementById("unlock-msg").textContent =
        `质量不足，无法解锁。当前 ${state.mass} ☀️，需要 ${spec.cost} ☀️。`;
      return;
    }
    state.mass -= spec.cost;
    state.unlocks[pendingId] = true;
    save();
    renderMass();
  }
  const id = pendingId;
  show("loading");
  const my = ++token;
  setTimeout(() => {
    if (my !== token) return;
    startEvolution(id);
  }, LOAD_MS);
}

function scheduleOf(stages) {
  const finite = stages.reduce((sum, s) => sum + (s.years || 0), 0) || 1;
  const epi = finite * 0.05;
  const weights = stages.map((s) => (s.years ? s.years : epi));
  const total = weights.reduce((a, b) => a + b, 0);
  let acc = 0;
  return stages.map((s, i) => {
    const dur = (weights[i] / total) * LIFE_MS;
    const start = acc;
    acc += dur;
    return { stage: s, index: i, start, dur, end: acc };
  });
}

function fillCells(container, names) {
  container.innerHTML = "";
  names.forEach((name) => {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.textContent = name;
    cell.title = name;
    const size = names.length >= 8 ? 11 : names.length >= 6 ? 13 : 16;
    const shrink = name.length > 10 ? Math.max(10, size - Math.ceil((name.length - 10) / 4)) : size;
    cell.style.fontSize = shrink + "px";
    container.appendChild(cell);
  });
  requestAnimationFrame(() => {
    container.querySelectorAll(".cell").forEach((cell) => {
      let size = parseInt(cell.style.fontSize, 10) || 14;
      let guard = 0;
      while (guard < 12 && size > 9 && cell.scrollHeight > cell.clientHeight + 2) {
        size -= 1;
        cell.style.fontSize = size + "px";
        guard += 1;
      }
    });
  });
}

function preparePlay(id) {
  const spec = CLASSES[id];
  const stages = spec.stages.map((s) => Object.assign({}, s));
  let remnant = spec.remnant;
  let disrupt = false;
  if (spec.branches) {
    const collapse = Math.random() < spec.branches.p;
    if (collapse) {
      stages.push(Object.assign({}, spec.branches.collapse.stage));
      remnant = spec.branches.collapse.remnant;
    } else {
      stages.push(Object.assign({}, spec.branches.disrupt.stage));
      disrupt = true;
    }
  }
  annotateStages(stages);
  return {
    id,
    stages,
    schedule: scheduleOf(stages),
    remnant,
    disrupt,
    viewKm: stages[0].diam * 3,
    shown: 0,
    stageIndex: -1
  };
}

function skyBox(id) {
  const sky = document.getElementById(id);
  return Math.max(200, Math.min(sky.clientWidth, sky.clientHeight));
}

function applySprite(which, stage, px) {
  const a = document.getElementById(which + "-a");
  const b = document.getElementById(which + "-b");
  const anchor = document.getElementById(which === "star" ? "evo-anchor" : "rem-anchor");
  const next = play && play.shown === 0 ? b : a;
  const prev = next === a ? b : a;
  next.src = ASSET + stage.sprite;
  next.style.filter = stage.filter || "none";
  next.style.width = px + "px";
  prev.style.width = px + "px";
  next.style.opacity = "1";
  prev.style.opacity = "0";
  next.classList.toggle("spinning", !!stage.spin);
  prev.classList.remove("spinning");
  anchor.classList.toggle("jets", !!stage.jets);
  anchor.classList.toggle("ringed", !!stage.ring);
  if (play) play.shown = play.shown === 0 ? 1 : 0;
}

let play = null;

function startEvolution(id) {
  play = preparePlay(id);
  play.t0 = performance.now();
  fillCells(document.getElementById("evo-cells"), play.stages.map((s) => s.name));
  document.getElementById("star-a").style.opacity = "0";
  document.getElementById("star-b").style.opacity = "0";
  document.getElementById("evo-toast").hidden = true;
  show("evolve");
  const my = ++token;
  function tick(now) {
    if (my !== token) return;
    const elapsed = now - play.t0;
    const t = Math.min(elapsed, LIFE_MS);
    paintLife(t);
    if (elapsed >= LIFE_MS) {
      startRemnant();
      return;
    }
    raf = requestAnimationFrame(tick);
  }
  raf = requestAnimationFrame(tick);
}

function paintLife(t) {
  const slot = play.schedule.find((s) => t < s.end) || play.schedule[play.schedule.length - 1];
  const local = slot.dur <= 0 ? 1 : Math.min(1, (t - slot.start) / slot.dur);
  const cells = document.querySelectorAll("#evo-cells .cell");
  cells.forEach((cell, i) => cell.classList.toggle("now", i === slot.index));
  const marker = document.getElementById("evo-marker");
  const pos = (slot.index + local) / play.stages.length;
  marker.style.left = (pos * 100) + "%";

  if (slot.index !== play.stageIndex) {
    const stage = slot.stage;
    let pops = 0;
    while (stage.diam > play.viewKm && pops < 6) {
      play.viewKm *= 10;
      pops += 1;
    }
    if (pops) {
      const toast = document.getElementById("evo-toast");
      toast.hidden = false;
      toast.textContent = "背景已扩大十倍";
      clearTimeout(paintLife._toast);
      paintLife._toast = setTimeout(() => { toast.hidden = true; }, FAST ? 700 : 2200);
    }
    play.stageIndex = slot.index;
    document.getElementById("evo-status").textContent = formatStatus(stage);
    const px = Math.max(stage.diam < 1000 ? 8 : 2, (stage.diam / play.viewKm) * skyBox("evo-sky"));
    const cap = skyBox("evo-sky") * 0.92;
    applySprite("star", stage, Math.min(px, cap));
    if (stage.sn) {
      const flash = document.getElementById("evo-flash");
      flash.classList.remove("on");
      void flash.offsetWidth;
      flash.classList.add("on");
    }
  } else {
    const stage = slot.stage;
    const px = Math.max(stage.diam < 1000 ? 8 : 2, (stage.diam / play.viewKm) * skyBox("evo-sky"));
    const cap = skyBox("evo-sky") * 0.92;
    document.getElementById("star-a").style.width = Math.min(px, cap) + "px";
    document.getElementById("star-b").style.width = Math.min(px, cap) + "px";
  }
}

function startRemnant() {
  const my = ++token;
  const remnant = play.remnant;
  const disrupt = play.disrupt;
  document.getElementById("rem-status").textContent = formatStatus(play.stages[play.stages.length - 1]);
  show("remnant");
  const anchor = document.getElementById("rem-anchor");
  anchor.classList.remove("jets", "ringed");
  document.getElementById("nebula").hidden = !disrupt;
  const a = document.getElementById("rem-a");
  const b = document.getElementById("rem-b");
  a.classList.remove("spinning");
  b.classList.remove("spinning");
  if (disrupt) {
    fillCells(document.getElementById("rem-cells"), [play.stages[play.stages.length - 1].name, "星云"]);
    a.style.opacity = "0";
    b.style.opacity = "0";
  } else if (remnant.kind === "bh") {
    fillCells(document.getElementById("rem-cells"), [remnant.left, remnant.right]);
    a.src = ASSET + remnant.bh;
    a.style.filter = "none";
    a.style.width = Math.min(skyBox("rem-sky") * 0.72, 640) + "px";
    a.style.opacity = "1";
    b.style.opacity = "0";
  } else {
    fillCells(document.getElementById("rem-cells"), [remnant.left, remnant.right]);
    a.src = ASSET + remnant.from;
    b.src = ASSET + remnant.to;
    a.style.filter = "none";
    b.style.filter = "none";
    a.style.opacity = "1";
    b.style.opacity = "0";
  }
  const t0 = performance.now();
  const total = disrupt ? DISRUPT_MS : REMNANT_MS;
  function tick(now) {
    if (my !== token) return;
    const u = Math.min(1, (now - t0) / total);
    document.getElementById("rem-marker").style.left = (u * 100) + "%";
    if (!disrupt && remnant.kind === "cool-dead") {
      const w = Math.min(skyBox("rem-sky") * (0.42 - u * 0.08), 420);
      a.style.width = w + "px";
      b.style.width = w + "px";
      a.style.opacity = String(1 - u);
      b.style.opacity = String(u);
      a.style.filter = `brightness(${1.15 - u * 0.7}) saturate(${1 - u * 0.6})`;
    } else if (!disrupt && remnant.kind === "cool-ns") {
      const w = Math.min(skyBox("rem-sky") * (0.34 - u * 0.16), 360);
      a.style.width = w + "px";
      b.style.width = Math.max(48, w * 0.55) + "px";
      a.style.opacity = String(1 - u);
      b.style.opacity = String(u);
      a.classList.toggle("spinning", u < 0.85);
      a.style.animationDuration = (0.28 + u * 1.4) + "s";
    }
    if (u < 1) {
      raf = requestAnimationFrame(tick);
      return;
    }
    if (!disrupt && remnant.kind === "bh") {
      const flash = document.getElementById("rem-flash");
      flash.classList.remove("on");
      void flash.offsetWidth;
      flash.classList.add("on");
      a.style.opacity = "0";
      setTimeout(() => { if (my === token) goHome(); }, FAST ? 280 : 700);
      return;
    }
    goHome();
  }
  raf = requestAnimationFrame(tick);
}

function onSearch(raw) {
  const parts = normQuery(raw).split(/[、,，/]/).filter(Boolean);
  const id = resolveQuery(parts.length > 1 ? parts[0] : raw);
  if (!id) {
    openFail();
    return;
  }
  openUnlock(id);
}

searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  onSearch(searchInput.value);
});

document.getElementById("spec-panel").addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-q]");
  if (!btn) return;
  searchInput.value = btn.dataset.q.split("、")[0];
  onSearch(searchInput.value);
});

document.getElementById("btn-wheel").addEventListener("click", openWheel);
document.getElementById("btn-lecturer").addEventListener("click", openLecturer);
document.getElementById("wheel-close").addEventListener("click", goHome);
document.getElementById("lecturer-close").addEventListener("click", goHome);
document.getElementById("fail-close").addEventListener("click", goHome);
document.getElementById("wheel-start").addEventListener("click", onSpin);
document.getElementById("unlock-confirm").addEventListener("click", confirmUnlock);

document.getElementById("redeem-form").addEventListener("submit", (event) => {
  event.preventDefault();
  applyCode(document.getElementById("redeem-input").value);
  document.getElementById("redeem-input").value = "";
});

document.getElementById("ask-form").addEventListener("submit", (event) => {
  event.preventDefault();
  onAsk(document.getElementById("ask-input").value);
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  const ad = document.getElementById("ad");
  if (!ad.hidden) {
    document.getElementById("ad-skip").click();
    return;
  }
  if (!document.getElementById("screen-home").classList.contains("active")) goHome();
});

buildWheel();
renderMass();
searchInput.focus();

window.__game = {
  state,
  FAST,
  LIFE_MS,
  resolveQuery,
  answerLecturer: (q) => answerLecturer(q, state),
  scheduleOf,
  CLASSES
};
