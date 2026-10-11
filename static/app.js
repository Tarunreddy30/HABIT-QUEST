// =========================================================
// HabitQuest front-end
// Talks to the Flask API (/api/...) and renders every page.
// =========================================================

const RING_CIRCUMFERENCE = 2 * Math.PI * 86; // matches r=86 in the SVG

let STATE = null;          // last full state from the server
let CURRENT_CAL = { year: null, month: null };

// ---------------------------------------------------------
// Helpers
// ---------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $all = (sel) => document.querySelectorAll(sel);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function showToast(title, sub = "") {
  const stack = $("#toast-stack");
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<div class="toast-title">${title}</div>${sub ? `<div class="toast-sub">${sub}</div>` : ""}`;
  stack.appendChild(el);
  setTimeout(() => el.remove(), 3600);
}

function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

// ---------------------------------------------------------
// Navigation
// ---------------------------------------------------------
function initNav() {
  $all(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => goToPage(btn.dataset.page));
  });
  $all("[data-nav]").forEach((btn) => {
    btn.addEventListener("click", () => goToPage(btn.dataset.nav));
  });
  $("#hamburger").addEventListener("click", () => {
    $("#sidebar").classList.add("open");
    $("#scrim").classList.add("show");
  });
  $("#scrim").addEventListener("click", closeSidebar);
}

function closeSidebar() {
  $("#sidebar").classList.remove("open");
  $("#scrim").classList.remove("show");
}

function goToPage(page) {
  $all(".page").forEach((p) => p.classList.remove("active"));
  $all(".nav-item").forEach((n) => n.classList.remove("active"));
  const target = document.getElementById(`page-${page}`);
  const nav = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (target) target.classList.add("active");
  if (nav) nav.classList.add("active");
  $("#page-title").textContent = nav ? nav.textContent.trim() : capitalize(page);
  closeSidebar();
  if (page === "calendar") loadCalendar();
}

// ---------------------------------------------------------
// Load full state and render everything
// ---------------------------------------------------------
async function loadState() {
  const data = await api("/api/state");
  STATE = data;
  renderTopStats(data.user);
  renderHero(data.user);
  renderTodayProgress(data.today_progress);
  renderDailyChallenge(data.daily_challenge);
  renderWeeklyChallenge(data.weekly_challenge);
  renderQuests(data.quests);
  renderAchievements(data.achievements);
  renderBadges(data.badges);
  renderShop(data.shop, data.redeemed);
  renderStats(data);
  renderProfile(data);
  CURRENT_CAL = { year: data.calendar.year, month: data.calendar.month };
  renderCalendar(data.calendar);
  populateTaskFormOptions(data.categories, data.difficulties);
}

// ---------------------------------------------------------
// Renderers
// ---------------------------------------------------------
function renderTopStats(u) {
  $("#top-streak").textContent = u.current_streak;
  $("#top-coins").textContent = u.coins;
  $("#top-level").textContent = u.level;
  $("#side-streak").textContent = u.current_streak;
  $("#side-coins").textContent = u.coins;
  $("#shop-coins").textContent = u.coins;
}

function renderHero(u) {
  $("#hero-level").textContent = `Level ${u.level}`;
  $("#hero-title").textContent = `— ${u.title}`;
  $("#xp-current").textContent = u.xp_into_level;
  $("#xp-target").textContent = u.xp_needed_for_level;
  const pct = Math.min(100, (u.xp_into_level / Math.max(1, u.xp_needed_for_level)) * 100);
  $("#xp-bar-fill").style.width = pct + "%";
  $("#hs-streak").textContent = u.current_streak;
  $("#hs-coins").textContent = u.coins;
  $("#hs-badges").textContent = u.badge_count;
  $("#hs-xp").textContent = u.total_xp;
  $("#ring-level").textContent = u.level;
  const offset = RING_CIRCUMFERENCE - (pct / 100) * RING_CIRCUMFERENCE;
  $("#ring-fill").style.strokeDasharray = RING_CIRCUMFERENCE;
  $("#ring-fill").style.strokeDashoffset = offset;
}

function renderTodayProgress(p) {
  $("#prog-completed").textContent = p.completed;
  $("#prog-total").textContent = p.total;
  const pct = p.total ? Math.round((p.completed / p.total) * 100) : 0;
  $("#prog-pct").textContent = pct + "%";
  $("#prog-fill").style.width = pct + "%";
  $("#prog-msg").textContent = p.perfect
    ? "\uD83C\uDF89 PERFECT DAY! All missions completed!"
    : p.completed === 0
      ? "Let's get started!"
      : "You're doing great — keep going!";
}

function renderDailyChallenge(c) {
  $("#daily-challenge-text").textContent = c.text;
  $("#dc-xp").textContent = c.xp;
  $("#dc-coins").textContent = c.coins;
  const statusEl = $("#dc-status");
  statusEl.textContent = c.completed ? "\u2705 Complete" : "In Progress";
  statusEl.classList.toggle("done", c.completed);
}

function renderWeeklyChallenge(w) {
  $("#wc-current").textContent = w.current;
  $("#wc-target").textContent = w.target;
  $("#wc-target2").textContent = w.target;
  const pct = Math.min(100, (w.current / w.target) * 100);
  $("#wc-fill").style.width = pct + "%";
}

function questCardHTML(q) {
  return `
    <div class="quest-card difficulty-${q.difficulty} ${q.completed_today ? "completed" : ""}" data-quest-id="${q.id}">
      <div class="quest-top">
        <span class="quest-icon">${q.icon}</span>
        <span class="quest-diff-tag">${q.difficulty_icon} ${q.difficulty_label}</span>
      </div>
      <div class="quest-name">${q.name}</div>
      <div class="quest-cat">${q.category_icon} ${q.category_label}</div>
      <div class="quest-reward-row">
        <span class="chip chip-xp">+${q.xp} XP</span>
        <span class="chip chip-coin">+${q.coins} 🪙</span>
      </div>
      <div class="quest-footer">
        <span class="quest-status ${q.completed_today ? "done" : ""}">${q.completed_today ? "✅ Completed" : "🔒 Not Completed"}</span>
        <button class="quest-complete-btn" data-quest-id="${q.id}" ${q.completed_today ? "disabled" : ""}>
          ${q.completed_today ? "Done" : "Complete"}
        </button>
      </div>
    </div>`;
}

function renderQuests(quests) {
  const previewEl = $("#dashboard-quest-preview");
  const fullEl = $("#quest-full-list");
  const emptyEl = $("#quests-empty");

  if (!quests.length) {
    previewEl.innerHTML = "";
    fullEl.innerHTML = "";
    emptyEl.hidden = false;
    return;
  }
  emptyEl.hidden = true;
  previewEl.innerHTML = quests.slice(0, 4).map(questCardHTML).join("");
  fullEl.innerHTML = quests.map(questCardHTML).join("");
  attachQuestHandlers();
}

function attachQuestHandlers() {
  $all(".quest-complete-btn").forEach((btn) => {
    btn.addEventListener("click", () => completeQuest(btn.dataset.questId));
  });
}

function renderAchievements(list) {
  $("#achv-grid").innerHTML = list.map((a) => {
    const pct = Math.min(100, (a.current / a.target) * 100);
    const complete = a.current >= a.target;
    return `
      <div class="achv-card ${complete ? "complete" : ""}">
        <div class="achv-top"><span class="achv-icon">${complete ? "🏆" : a.icon}</span><span class="achv-name">${a.name}</span></div>
        <div class="achv-desc">${a.desc}</div>
        <div class="achv-progress-row"><span>${a.current} / ${a.target}</span><span>${Math.round(pct)}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
      </div>`;
  }).join("");
}

function renderBadges(list) {
  $("#badge-grid").innerHTML = list.map((b) => `
    <div class="badge-card ${b.unlocked ? "" : "locked"}">
      <div class="badge-icon">${b.icon}</div>
      <div class="badge-name">${b.name}</div>
      <div class="badge-desc">${b.desc}</div>
      <span class="rarity-tag rarity-${b.rarity}">${b.rarity}</span>
    </div>`).join("");
}

function renderShop(shop, redeemed) {
  $("#shop-grid").innerHTML = shop.map((r) => `
    <div class="shop-card">
      <div class="shop-icon">${r.icon}</div>
      <div class="shop-name">${r.name}</div>
      <div class="shop-cost">🪙 ${r.cost}</div>
      <button class="btn btn-primary" data-reward-id="${r.id}" ${r.affordable ? "" : "disabled"}>
        ${r.affordable ? "Redeem" : "Not enough coins"}
      </button>
    </div>`).join("");
  $all("[data-reward-id]").forEach((btn) => {
    btn.addEventListener("click", () => redeemReward(btn.dataset.rewardId));
  });

  const redeemedEl = $("#redeemed-list");
  redeemedEl.innerHTML = redeemed.length
    ? redeemed.slice().reverse().map((r) => `<li>🎁 ${r.name} — redeemed on ${r.date}</li>`).join("")
    : `<li class="muted">No rewards redeemed yet.</li>`;
}

function renderStats(data) {
  const u = data.user;
  const stats = [
    ["Total XP", u.total_xp],
    ["Total Missions", u.total_missions_completed],
    ["Current Streak", u.current_streak + " days"],
    ["Longest Streak", u.longest_streak + " days"],
    ["Perfect Days", u.perfect_days],
    ["Completion Today", `${data.today_progress.completed}/${data.today_progress.total}`],
    ["Weekly Progress", `${data.weekly_challenge.current}/${data.weekly_challenge.target}`],
    ["Badges Unlocked", u.badge_count + " / " + data.badges.length],
  ];
  $("#stats-grid").innerHTML = stats.map(([label, value]) => `
    <div class="stat-card">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
    </div>`).join("");
}

function renderProfile(data) {
  const u = data.user;
  $("#profile-username").textContent = u.username;
  $("#profile-title").textContent = `⚔️ ${u.title} — Level ${u.level}`;
  const stats = [
    ["🔥 Current Streak", u.current_streak],
    ["🏔️ Longest Streak", u.longest_streak],
    ["🏆 Badges", u.badge_count],
    ["⚡ Total XP", u.total_xp],
    ["🪙 Coins", u.coins],
    ["✅ Missions Done", u.total_missions_completed],
  ];
  $("#profile-stats-grid").innerHTML = stats.map(([label, value]) => `
    <div class="stat-card">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
    </div>`).join("");
}

// ---------------------------------------------------------
// Calendar
// ---------------------------------------------------------
function renderCalendar(cal) {
  $("#cal-month-label").textContent = `${cal.month_name} ${cal.year}`;
  const grid = $("#cal-grid");
  // figure out the weekday (Mon=0) of the 1st, to pad the grid
  const firstDate = new Date(cal.days[0].date + "T00:00:00");
  const leadingBlanks = (firstDate.getDay() + 6) % 7; // convert Sun=0 -> Mon=0 based

  let html = "";
  for (let i = 0; i < leadingBlanks; i++) html += `<div class="cal-day empty"></div>`;
  cal.days.forEach((d) => {
    html += `<div class="cal-day status-${d.status}" data-date="${d.date}" data-completed='${JSON.stringify(d.completed)}'>
        <span>${d.day}</span>
        <span class="dot dot-${d.status === "none" || d.status === "future" ? "future" : d.status}"></span>
      </div>`;
  });
  grid.innerHTML = html;

  $all(".cal-day:not(.empty)").forEach((el) => {
    el.addEventListener("click", () => showDayDetail(el.dataset.date, JSON.parse(el.dataset.completed)));
  });
}

function showDayDetail(dateStr, completedIds) {
  const detail = $("#cal-day-detail");
  detail.hidden = false;
  $("#cal-day-title").textContent = `Missions on ${dateStr}`;
  const list = $("#cal-day-list");
  if (!completedIds.length) {
    list.innerHTML = `<li class="muted">No missions completed this day.</li>`;
    return;
  }
  const allQuests = STATE.quests;
  list.innerHTML = completedIds.map((id) => {
    const q = allQuests.find((qq) => qq.id === id);
    return `<li>${q ? `${q.icon} ${q.name}` : id}</li>`;
  }).join("");
}

async function loadCalendar() {
  let { year, month } = CURRENT_CAL;
  const cal = await api(`/api/calendar/${year}/${month}`);
  renderCalendar(cal);
}

function shiftCalendar(delta) {
  let { year, month } = CURRENT_CAL;
  month += delta;
  if (month < 1) { month = 12; year -= 1; }
  if (month > 12) { month = 1; year += 1; }
  CURRENT_CAL = { year, month };
  loadCalendar();
}

// ---------------------------------------------------------
// Actions
// ---------------------------------------------------------
async function completeQuest(questId) {
  try {
    const result = await api("/api/complete_task", {
      method: "POST",
      body: JSON.stringify({ quest_id: questId }),
    });
    showToast("✨ QUEST COMPLETE!", `+${result.xp_gained} XP · +${result.coins_gained} 🪙`);
    (result.bonuses || []).forEach((b) => showToast(`🎉 ${b.label}`, `+${b.xp} XP · +${b.coins} 🪙`));
    (result.newly_unlocked_badges || []).forEach((b) => showToast("🏆 BADGE UNLOCKED!", `${b.icon} ${b.name}`));

    await loadState();

    const card = document.querySelector(`.quest-card[data-quest-id="${questId}"]`);
    if (card) {
      card.classList.add("just-completed");
      setTimeout(() => card.classList.remove("just-completed"), 700);
    }

    if (result.leveled_up) {
      showLevelUp(result.new_level, result.new_title);
    }
  } catch (e) {
    showToast("Couldn't complete quest", e.message);
  }
}

function showLevelUp(level, title) {
  $("#levelup-level").textContent = `Level ${level}`;
  $("#levelup-title").textContent = title;
  $("#levelup-overlay").hidden = false;
}

async function redeemReward(rewardId) {
  try {
    await api("/api/redeem_reward", { method: "POST", body: JSON.stringify({ reward_id: rewardId }) });
    showToast("🎁 Reward Redeemed!", "Enjoy — you earned it.");
    await loadState();
  } catch (e) {
    showToast("Couldn't redeem", e.message);
  }
}

// ---------------------------------------------------------
// Create Task modal
// ---------------------------------------------------------
function populateTaskFormOptions(categories, difficulties) {
  const catSel = $("#ct-category");
  const diffSel = $("#ct-difficulty");
  if (!catSel.dataset.filled) {
    catSel.innerHTML = Object.entries(categories).map(([k, v]) => `<option value="${k}">${v.icon} ${v.label}</option>`).join("");
    catSel.dataset.filled = "1";
  }
  if (!diffSel.dataset.filled) {
    diffSel.innerHTML = Object.entries(difficulties).map(([k, v]) => `<option value="${k}">${v.icon} ${v.label}</option>`).join("");
    diffSel.dataset.filled = "1";
  }
}

function openTaskModal() { $("#modal-backdrop").hidden = false; $("#ct-name").focus(); }
function closeTaskModal() {
  $("#modal-backdrop").hidden = true;
  $("#ct-name").value = "";
  $("#ct-icon").value = "";
}

async function submitTask() {
  const name = $("#ct-name").value.trim();
  if (!name) { showToast("Give your quest a name"); return; }
  try {
    await api("/api/create_task", {
      method: "POST",
      body: JSON.stringify({
        name,
        icon: $("#ct-icon").value.trim() || "⭐",
        category: $("#ct-category").value,
        difficulty: $("#ct-difficulty").value,
      }),
    });
    closeTaskModal();
    showToast("⚔️ New Quest Created!", name);
    await loadState();
  } catch (e) {
    showToast("Couldn't create quest", e.message);
  }
}

// ---------------------------------------------------------
// Init
// ---------------------------------------------------------
function initModal() {
  $("#btn-open-create-task").addEventListener("click", openTaskModal);
  $("#btn-empty-create").addEventListener("click", openTaskModal);
  $("#ct-cancel").addEventListener("click", closeTaskModal);
  $("#ct-submit").addEventListener("click", submitTask);
  $("#modal-backdrop").addEventListener("click", (e) => { if (e.target.id === "modal-backdrop") closeTaskModal(); });
}

function initLevelUp() {
  $("#levelup-close").addEventListener("click", () => { $("#levelup-overlay").hidden = true; });
}

function initCalendarNav() {
  $("#cal-prev").addEventListener("click", () => shiftCalendar(-1));
  $("#cal-next").addEventListener("click", () => shiftCalendar(1));
}

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  initModal();
  initLevelUp();
  initCalendarNav();
  loadState().catch((e) => showToast("Couldn't load HabitQuest", e.message));
});
