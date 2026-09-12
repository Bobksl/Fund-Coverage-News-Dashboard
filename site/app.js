// Fund Coverage News demo dashboard. Reads the static feed built by
// tools/build_demo_feed.py from work/phase2/demo-feed/. No network calls beyond same-origin
// fetch of local JSON; run a static server from the repo root (see README) so fetch works.
const DATA_ROOT = "../work/phase2/demo-feed";

const state = { dates: [], index: 0, indexMeta: null, cardCounts: {} };

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function renderDisclosure(meta) {
  document.getElementById("disclosure").textContent = meta.disclosure;
}

function renderNav() {
  const select = document.getElementById("dateSelect");
  select.innerHTML = state.dates
    .map((date, i) => `<option value="${i}">${date}</option>`)
    .join("");
  select.value = state.index;
  document.getElementById("prevDay").disabled = state.index <= 0;
  document.getElementById("nextDay").disabled = state.index >= state.dates.length - 1;
}

function pill(text, cls) {
  return `<span class="pill ${cls || ""}">${text}</span>`;
}

function renderCard(card) {
  const relevance = card.relevance_level ? pill(card.relevance_level, card.relevance_level) : "";
  const score = pill(`score ${card.total_score ?? "n/a"}`, "score");
  const sources = card.sources
    .map((s) => `<a href="${s.url}" target="_blank" rel="noopener">${s.publisher}: ${s.title}</a>`)
    .join("<br>");
  return `
    <div class="card">
      <div class="card-top">
        <h3 class="headline">${card.en.headline}</h3>
        <div>${relevance}${score}</div>
      </div>
      <p class="summary">${card.en.summary}</p>
      <div class="zh-block">中文 (Chinese rendering): ${card.zh_status}</div>
      <div class="sources">${sources || "No source captured"}</div>
      <div class="meta">
        ${card.primary_event_type} / ${card.subtype ?? "—"} ·
        partition: ${card.partition} · status: ${card.status}
      </div>
    </div>`;
}

async function renderDay() {
  const main = document.getElementById("main");
  const dayStats = document.getElementById("dayStats");
  if (state.dates.length === 0) {
    main.innerHTML = `<div class="empty"><h3>No dated candidates in this demo feed</h3>
      <p>Run <code>python -m tools.build_demo_feed</code> to (re)generate it.</p></div>`;
    dayStats.textContent = "";
    return;
  }
  const date = state.dates[state.index];
  let cards = [];
  try {
    cards = await fetchJson(`${DATA_ROOT}/${date}.json`);
  } catch (error) {
    main.innerHTML = `<div class="stale"><h3>Could not load ${date}</h3><p>${error.message}</p></div>`;
    return;
  }
  dayStats.textContent = `${cards.length} candidate${cards.length === 1 ? "" : "s"} on ${date}`;
  if (cards.length === 0) {
    main.innerHTML = `<div class="empty"><h3>No shortlisted candidates for ${date}</h3>
      <p>This is expected: the baseline shortlisted 22 events across the whole corpus.</p></div>`;
    return;
  }
  main.innerHTML = cards.map(renderCard).join("");
}

function goTo(delta) {
  const next = state.index + delta;
  if (next < 0 || next >= state.dates.length) return;
  state.index = next;
  renderNav();
  renderDay();
}

async function init() {
  let meta;
  try {
    meta = await fetchJson(`${DATA_ROOT}/index.json`);
  } catch (error) {
    document.getElementById("disclosure").textContent =
      `Could not load the demo feed index (${error.message}). ` +
      `Run "python -m tools.build_demo_feed" from the repo root, then serve this ` +
      `folder over HTTP (e.g. "python -m http.server" from the repo root) rather than ` +
      `opening index.html directly.`;
    document.getElementById("main").innerHTML = "";
    return;
  }
  state.indexMeta = meta;
  state.dates = meta.dates;
  const lastWithCards = meta.dates_with_cards[meta.dates_with_cards.length - 1];
  const defaultIndex = lastWithCards ? state.dates.indexOf(lastWithCards) : state.dates.length - 1;
  state.index = defaultIndex >= 0 ? defaultIndex : (state.dates.length ? state.dates.length - 1 : 0);
  renderDisclosure(meta);
  renderNav();
  renderDay();

  document.getElementById("prevDay").addEventListener("click", () => goTo(-1));
  document.getElementById("nextDay").addEventListener("click", () => goTo(1));
  document.getElementById("dateSelect").addEventListener("change", (event) => {
    state.index = Number(event.target.value);
    renderDay();
  });
}

init();
