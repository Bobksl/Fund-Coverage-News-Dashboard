// Junson Capital — Fund Coverage News. A static page that reads ./data/index.json,
// ./data/status.json and ./data/YYYY-MM-DD.json (shapes in docs/site-data-contract.md).
//
// Safety: values from the data files are rendered with textContent, never as HTML, and a source
// link is only created for an absolute http(s) URL. Day fetches carry a request token so a slow
// response for a date the reader has already left cannot overwrite the current view.
"use strict";

const I18N = {
  en: {
    pageTitle: "Junson Capital — Fund Coverage News",
    title: "Fund Coverage News",
    prev: "‹ Earlier",
    next: "Later ›",
    today: "Today",
    dateLabel: "Date",
    gpLabel: "Manager",
    sectorLabel: "Sub-sector",
    allGps: "All managers",
    allSectors: "All sub-sectors",
    dateOption: "{date} ({n})",
    itemCount: "{n} items",
    itemCountOne: "1 item",
    filteredCount: "{shown} of {n} items",
    readOriginal: "Read original →",
    unknownPublisher: "Unknown source",
    unreviewed: "Auto-selected · not yet reviewed",
    noToday: "No new items yet today ({today}). Showing the latest day, {date}.",
    noMatch: "No items match these filters.",
    noItems: "No news has been published yet.",
    loading: "Loading…",
    indexError: "The news index could not be loaded. Please reload the page or try again later.",
    dayError: "News for {date} could not be loaded. Try another date or reload the page.",
    lastRefreshed: "Last refreshed {time} HKT",
    refreshFailed: "Latest refresh failed; showing the last successful update.",
    statusUnavailable: "Refresh status unavailable",
    footer: "Summaries are AI-drafted from the linked sources; follow the link for full details.",
    locale: "en-GB",
  },
  zh: {
    pageTitle: "Junson Capital — 基金覆盖新闻",
    title: "基金覆盖新闻",
    prev: "‹ 前一天",
    next: "后一天 ›",
    today: "今天",
    dateLabel: "日期",
    gpLabel: "管理人",
    sectorLabel: "子行业",
    allGps: "全部管理人",
    allSectors: "全部子行业",
    dateOption: "{date}（{n}）",
    itemCount: "{n} 条新闻",
    itemCountOne: "1 条新闻",
    filteredCount: "{n} 条中的 {shown} 条",
    readOriginal: "阅读原文 →",
    unknownPublisher: "来源未知",
    unreviewed: "自动筛选 · 未经审核",
    noToday: "今天（{today}）暂无新内容，以下为最近一天：{date}。",
    noMatch: "没有符合筛选条件的新闻。",
    noItems: "暂未发布任何新闻。",
    loading: "加载中…",
    indexError: "无法加载新闻索引，请刷新页面或稍后再试。",
    dayError: "无法加载 {date} 的新闻，请选择其他日期或刷新页面。",
    lastRefreshed: "最近更新：{time}（香港时间）",
    refreshFailed: "最近一次更新失败，当前显示上次成功更新的内容。",
    statusUnavailable: "更新状态不可用",
    footer: "摘要由 AI 根据所链接的来源撰写，详情请点击原文链接。",
    locale: "zh-CN",
  },
};

const LANG_KEY = "fund-coverage-news-lang";
const state = {
  lang: "en", index: null, status: null, fatal: false,
  date: null, notice: null, gp: "", sector: "",
  days: new Map(), dayErrors: new Set(), token: 0,
};

function t(key, params) {
  let text = I18N[state.lang][key] ?? I18N.en[key] ?? key;
  for (const [name, value] of Object.entries(params || {})) text = text.split(`{${name}}`).join(String(value));
  return text;
}

function readStoredLang() {
  try {
    const value = localStorage.getItem(LANG_KEY);
    return value === "en" || value === "zh" ? value : null;
  } catch {
    return null;
  }
}

function storeLang(lang) {
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    // Storage unavailable (private mode, blocked site data): the choice lasts for this visit.
  }
}

function todayHongKong() {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", {timeZone: "Asia/Hong_Kong", year: "numeric", month: "2-digit", day: "2-digit"})
    .format(new Date());
}

function formatDay(iso, style) {
  const parsed = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return iso;
  const options = style === "short"
    ? {timeZone: "UTC", day: "numeric", month: "short", year: "numeric", weekday: "short"}
    : {timeZone: "UTC", day: "numeric", month: "long", year: "numeric", weekday: "long"};
  return new Intl.DateTimeFormat(t("locale"), options).format(parsed);
}

function formatInstant(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat(t("locale"), {
    timeZone: "Asia/Hong_Kong", day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(parsed);
}

function el(tag, options, children) {
  const node = document.createElement(tag);
  if (options) {
    if (options.className) node.className = options.className;
    if (options.text !== undefined) node.textContent = options.text;
    for (const [name, value] of Object.entries(options.attrs || {})) node.setAttribute(name, value);
  }
  for (const child of children || []) if (child) node.appendChild(child);
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function safeHttpUrl(value) {
  try {
    const url = new URL(String(value));
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function bilingual(value) {
  if (!value || typeof value !== "object") return "";
  return value[state.lang] || value.en || "";
}

function label(kind, id) {
  const entry = state.index && state.index.labels && state.index.labels[kind] && state.index.labels[kind][id];
  return (entry && (entry[state.lang] || entry.en)) || id;
}

async function fetchJson(path) {
  const response = await fetch(path, {cache: "no-store"});
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function dates() {
  return (state.index && Array.isArray(state.index.dates)) ? state.index.dates : [];
}

// ---- Static text, status and controls -----------------------------------------------------

function applyStaticText() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.title = t("pageTitle");
  for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang));
  }
}

function renderStatus() {
  const node = document.getElementById("status");
  clear(node);
  const status = state.status;
  if (!status || !status.last_success_at) {
    node.textContent = t("statusUnavailable");
    return;
  }
  const schedule = status.schedule ? (status.schedule[state.lang] || status.schedule.en) : "";
  node.appendChild(document.createTextNode(
    t("lastRefreshed", {time: formatInstant(status.last_success_at)}) + (schedule ? ` · ${schedule}` : "")));
  if (status.last_refresh_result === "failed") {
    node.appendChild(el("span", {className: "status-warn", text: ` ${t("refreshFailed")}`}));
  }
}

function fillSelect(select, options, value) {
  clear(select);
  for (const [optionValue, text] of options) select.appendChild(el("option", {text, attrs: {value: optionValue}}));
  select.value = value;
}

function renderControls() {
  const list = dates();
  const counts = (state.index && state.index.counts) || {};
  fillSelect(document.getElementById("dateSelect"),
    list.map((day) => [day, t("dateOption", {date: formatDay(day, "short"), n: counts[day] ?? "?"})]),
    state.date || "");
  const labels = (state.index && state.index.labels) || {};
  fillSelect(document.getElementById("gpSelect"),
    [["", t("allGps")], ...Object.keys(labels.gps || {}).map((id) => [id, label("gps", id)])], state.gp);
  fillSelect(document.getElementById("sectorSelect"),
    [["", t("allSectors")], ...Object.keys(labels.sectors || {}).map((id) => [id, label("sectors", id)])], state.sector);

  const position = list.indexOf(state.date);
  const noData = state.fatal || list.length === 0;
  document.getElementById("prev").disabled = noData || position < 0 || position >= list.length - 1;
  document.getElementById("next").disabled = noData || position <= 0;
  for (const id of ["today", "dateSelect", "gpSelect", "sectorSelect"]) document.getElementById(id).disabled = noData;
}

// ---- Day view -------------------------------------------------------------------------------

function renderCard(item) {
  const card = el("article", {className: "card"});
  if (item.review_status === "unreviewed") card.appendChild(el("span", {className: "badge", text: t("unreviewed")}));
  card.appendChild(el("h3", {className: "headline", text: bilingual(item.headline)}));
  card.appendChild(el("p", {className: "summary", text: bilingual(item.summary)}));

  const source = item.source || {};
  const line = el("p", {className: "source"}, [el("span", {text: source.publisher || t("unknownPublisher")})]);
  const href = safeHttpUrl(source.url);
  if (href) {
    line.appendChild(document.createTextNode(" · "));
    line.appendChild(el("a", {text: t("readOriginal"), attrs: {href, target: "_blank", rel: "noopener noreferrer"}}));
  }
  card.appendChild(line);

  const tags = [
    ...(Array.isArray(item.gps) ? item.gps : []).map((id) => el("span", {className: "tag tag-gp", text: label("gps", id)})),
    ...(Array.isArray(item.sectors) ? item.sectors : []).map((id) => el("span", {className: "tag", text: label("sectors", id)})),
  ];
  if (item.region) tags.push(el("span", {className: "tag", text: label("regions", item.region)}));
  if (tags.length) card.appendChild(el("p", {className: "tags"}, tags));
  return card;
}

function renderMain() {
  const main = document.getElementById("main");
  clear(main);
  if (state.fatal) {
    main.appendChild(el("p", {className: "state", text: t("indexError")}));
    return;
  }
  if (!state.date) {
    main.appendChild(el("p", {className: "state", text: t("noItems")}));
    return;
  }
  if (state.notice) {
    main.appendChild(el("p", {className: "notice", text: t("noToday", {
      today: formatDay(state.notice.today), date: formatDay(state.date)})}));
  }
  const heading = el("div", {className: "day-head"}, [el("h2", {text: formatDay(state.date)})]);
  main.appendChild(heading);

  if (state.dayErrors.has(state.date)) {
    main.appendChild(el("p", {className: "state", text: t("dayError", {date: formatDay(state.date)})}));
    return;
  }
  const items = state.days.get(state.date);
  if (!items) {
    main.appendChild(el("p", {className: "state", text: t("loading")}));
    return;
  }
  const shown = items.filter((item) =>
    (!state.gp || (Array.isArray(item.gps) && item.gps.includes(state.gp))) &&
    (!state.sector || (Array.isArray(item.sectors) && item.sectors.includes(state.sector))));
  const filtered = Boolean(state.gp || state.sector);
  heading.appendChild(el("p", {className: "count", text: filtered
    ? t("filteredCount", {shown: shown.length, n: items.length})
    : (items.length === 1 ? t("itemCountOne") : t("itemCount", {n: items.length}))}));
  if (shown.length === 0) {
    main.appendChild(el("p", {className: "state", text: filtered ? t("noMatch") : t("noItems")}));
    return;
  }
  for (const item of shown) main.appendChild(renderCard(item));
}

async function showDate(day, notice) {
  state.date = day;
  state.notice = notice || null;
  renderControls();
  renderMain();
  if (state.days.has(day)) return;
  const token = ++state.token;
  try {
    const data = await fetchJson(`./data/${day}.json`);
    state.days.set(day, Array.isArray(data.items) ? data.items : []);
    state.dayErrors.delete(day);
  } catch {
    state.dayErrors.add(day);
  }
  if (token === state.token && state.date === day) renderMain();
}

function openToday() {
  const list = dates();
  if (list.length === 0) {
    state.date = null;
    renderControls();
    renderMain();
    return;
  }
  const today = todayHongKong();
  // Never present an older day as today: say so, then show the most recent day.
  if (list.includes(today)) showDate(today);
  else showDate(list[0], {today});
}

function setLang(lang) {
  state.lang = lang;
  storeLang(lang);
  applyStaticText();
  renderStatus();
  renderControls();
  renderMain();
}

// ---- Start-up -------------------------------------------------------------------------------

function bindEvents() {
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.addEventListener("click", () => setLang(button.dataset.lang));
  }
  document.getElementById("prev").addEventListener("click", () => {
    const list = dates();
    const position = list.indexOf(state.date);
    if (position >= 0 && position < list.length - 1) showDate(list[position + 1]);
  });
  document.getElementById("next").addEventListener("click", () => {
    const list = dates();
    const position = list.indexOf(state.date);
    if (position > 0) showDate(list[position - 1]);
  });
  document.getElementById("today").addEventListener("click", openToday);
  document.getElementById("dateSelect").addEventListener("change", (event) => showDate(event.target.value));
  document.getElementById("gpSelect").addEventListener("change", (event) => {
    state.gp = event.target.value;
    renderMain();
  });
  document.getElementById("sectorSelect").addEventListener("change", (event) => {
    state.sector = event.target.value;
    renderMain();
  });
}

async function init() {
  const browserZh = (navigator.language || "").toLowerCase().startsWith("zh");
  state.lang = readStoredLang() || (browserZh ? "zh" : "en");
  bindEvents();
  applyStaticText();
  try {
    state.index = await fetchJson("./data/index.json");
  } catch {
    state.fatal = true;
  }
  try {
    state.status = await fetchJson("./data/status.json");
  } catch {
    state.status = null; // Shown as "status unavailable", never as a healthy refresh.
  }
  renderStatus();
  if (state.fatal) {
    renderControls();
    renderMain();
    return;
  }
  openToday();
}

init();
