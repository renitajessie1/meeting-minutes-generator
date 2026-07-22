// ============================================
// CONFIG
// ============================================
// Change this to your deployed backend URL when ready
// e.g. "https://your-app.up.railway.app"
const API_BASE_URL = "http://127.0.0.1:8000";

// ============================================
// THEME
// ============================================
function initTheme() {
  const saved = localStorage.getItem("theme");
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved || (systemDark ? "dark" : "light");
  applyTheme(theme);
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  const label = document.getElementById("themeLabel");
  if (label) label.textContent = theme === "dark" ? "Light mode" : "Dark mode";
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  applyTheme(current === "dark" ? "light" : "dark");
}

// ============================================
// TOAST
// ============================================
let toastTimer = null;
function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("is-error", isError);
  toast.hidden = false;
  requestAnimationFrame(() => toast.classList.add("is-visible"));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove("is-visible");
    setTimeout(() => { toast.hidden = true; }, 200);
  }, 3200);
}

// ============================================
// NAVIGATION
// ============================================
function switchView(viewName) {
  document.querySelectorAll(".nav-item").forEach(btn => {
    const active = btn.dataset.view === viewName;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-selected", active);
  });
  document.querySelectorAll(".view").forEach(view => {
    view.classList.toggle("is-active", view.id === `view-${viewName}`);
  });
  if (viewName === "history") loadHistory();
}

// ============================================
// INPUT MODE SWITCH (paste vs upload)
// ============================================
function switchInputMode(mode) {
  document.querySelectorAll(".mode-btn").forEach(btn => {
    const active = btn.dataset.mode === mode;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-selected", active);
  });
  document.getElementById("panel-paste").classList.toggle("is-active", mode === "paste");
  document.getElementById("panel-upload").classList.toggle("is-active", mode === "upload");
}

// ============================================
// RESULT RAIL RENDERING
// ============================================
const RAIL_STEPS = [
  { key: "summary", label: "Summary", cssClass: "step-summary", icon: `<path d="M3 4.5h10M3 8h10M3 11.5h6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>` },
  { key: "decisions", label: "Decisions", cssClass: "step-decisions", icon: `<path d="M3 8l3.5 3.5L13 4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>` },
  { key: "action_items", label: "Action items", cssClass: "step-actions", icon: `<rect x="3" y="3" width="10" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M5.5 8h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>` },
  { key: "deadlines", label: "Deadlines", cssClass: "step-deadlines", icon: `<circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3l2 1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>` },
];

function renderRail(data, scope) {
  return RAIL_STEPS.map((step, i) => `
    <div class="rail-step ${step.cssClass}">
      <div class="rail-marker">
        <div class="rail-dot"><svg viewBox="0 0 16 16" fill="none">${step.icon}</svg></div>
        ${i < RAIL_STEPS.length - 1 ? '<div class="rail-line"></div>' : ''}
      </div>
      <div class="rail-content">
        <div class="rail-label-row">
          <div class="rail-label">${step.label}</div>
          <button class="copy-btn" data-copy-scope="${scope}" data-copy-field="${step.key}" type="button">
            <svg viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="8" height="8" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M3 10.5V4a1 1 0 0 1 1-1h6.5" stroke="currentColor" stroke-width="1.3"/></svg>
            <span class="copy-btn-label">Copy</span>
          </button>
        </div>
        <div class="rail-text">${escapeHtml(data[step.key] || "—")}</div>
      </div>
    </div>
  `).join("");
}

let resultData = null;
let modalData = null;

document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".copy-btn");
  if (!btn) return;
  const scope = btn.dataset.copyScope;
  const field = btn.dataset.copyField;
  const source = scope === "modal" ? modalData : resultData;
  const text = (source && source[field]) || "";
  try {
    await navigator.clipboard.writeText(text);
    btn.classList.add("is-copied");
    const label = btn.querySelector(".copy-btn-label");
    const original = label.textContent;
    label.textContent = "Copied";
    setTimeout(() => {
      btn.classList.remove("is-copied");
      label.textContent = original;
    }, 1400);
  } catch (err) {
    showToast("Couldn't copy — try selecting the text manually", true);
  }
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatTimestamp(ts) {
  if (!ts) return "";
  // backend format: "2026-07-14 17:54:36"
  return ts.replace(" ", " · ");
}

// ============================================
// API CALLS
// ============================================
async function processTranscriptText(transcript) {
  const url = new URL(`${API_BASE_URL}/process-transcript`);
  url.searchParams.set("transcript", transcript);
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

async function uploadTranscriptFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE_URL}/upload-transcript`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

async function fetchHistory() {
  const res = await fetch(`${API_BASE_URL}/history`);
  if (!res.ok) throw new Error("Could not load history");
  const data = await res.json();
  return data.meetings || [];
}

async function fetchSearch(keyword) {
  const url = new URL(`${API_BASE_URL}/search`);
  url.searchParams.set("keyword", keyword);
  const res = await fetch(url);
  if (!res.ok) throw new Error("Search failed");
  const data = await res.json();
  return data.meetings || [];
}

// ============================================
// NEW MEETING — TEXT
// ============================================
const transcriptText = document.getElementById("transcriptText");
const charCount = document.getElementById("charCount");
const processTextBtn = document.getElementById("processTextBtn");
const resultPanel = document.getElementById("resultPanel");
const resultRail = document.getElementById("resultRail");
const resultTimestamp = document.getElementById("resultTimestamp");
const clear = document.getElementById("clear");

clear.addEventListener("click", () => {
    transcriptText.value = "";
    charCount.textContent = "0 characters";
    transcriptText.focus();
});

transcriptText.addEventListener("input", () => {
  const n = transcriptText.value.length;
  charCount.textContent = `${n.toLocaleString()} character${n === 1 ? "" : "s"}`;
});

processTextBtn.addEventListener("click", async () => {
  const text = transcriptText.value.trim();
  if (!text) {
    showToast("Paste a transcript first", true);
    return;
  }
  setButtonLoading(processTextBtn, true);
  try {
    const data = await processTranscriptText(text);
    showResult(data);
    showToast("Minutes generated and saved");
  } catch (e) {
    showToast(e.message, true);
  } finally {
    setButtonLoading(processTextBtn, false);
  }
});

function showResult(data) {
  resultData = data;
  resultRail.innerHTML = renderRail(data, "result");
  resultTimestamp.textContent = new Date().toLocaleString();
  showSuccessCheck();
  resultPanel.hidden = false;
  resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function showSuccessCheck() {
  const check = document.getElementById("successCheck");
  check.classList.remove("is-visible");
  void check.offsetWidth; // restart animation
  check.hidden = false;
  check.classList.add("is-visible");
  setTimeout(() => { check.hidden = true; }, 1100);
}

function setButtonLoading(btn, isLoading) {
  btn.classList.toggle("is-loading", isLoading);
  btn.disabled = isLoading;
}

// ============================================
// NEW MEETING — FILE UPLOAD
// ============================================
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const fileChip = document.getElementById("fileChip");
const fileChipName = document.getElementById("fileChipName");
const fileChipRemove = document.getElementById("fileChipRemove");
const processFileBtn = document.getElementById("processFileBtn");
let selectedFile = null;

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) setSelectedFile(fileInput.files[0]);
});

["dragenter", "dragover"].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("is-dragover");
  });
});
["dragleave", "drop"].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("is-dragover");
  });
});
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) setSelectedFile(file);
});

const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10MB

function setSelectedFile(file) {
  const validExt = /\.(docx|pdf)$/i.test(file.name);
  if (!validExt) {
    showToast("Only .docx and .pdf files are supported", true);
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    showToast("File is larger than 10MB — please upload a smaller file", true);
    return;
  }
  selectedFile = file;
  fileChipName.textContent = file.name;
  fileChip.hidden = false;
  processFileBtn.disabled = false;
}

fileChipRemove.addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();
  selectedFile = null;
  fileInput.value = "";
  fileChip.hidden = true;
  processFileBtn.disabled = true;
});

processFileBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  setButtonLoading(processFileBtn, true);
  try {
    const data = await uploadTranscriptFile(selectedFile);
    showResult(data);
    showToast("Minutes generated and saved");
  } catch (e) {
    showToast(e.message, true);
  } finally {
    setButtonLoading(processFileBtn, false);
  }
});

// ============================================
// INPUT MODE TABS
// ============================================
document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => switchInputMode(btn.dataset.mode));
});

// ============================================
// NAV TABS
// ============================================
document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

// ============================================
// HISTORY LIST
// ============================================
const historyList = document.getElementById("historyList");
const historyEmpty = document.getElementById("historyEmpty");
let allMeetings = [];

async function loadHistory() {
  try {
    allMeetings = await fetchHistory();
    renderHistoryList(allMeetings);
  } catch (e) {
    showToast(e.message, true);
  }
}

function renderHistoryList(meetings) {
  historyList.innerHTML = "";
  historyEmpty.hidden = meetings.length > 0;
  document.getElementById("statsBar").hidden = meetings.length === 0;
  renderStats(meetings);
  meetings.forEach(m => {
    const card = document.createElement("div");
    card.className = "history-card";
    card.innerHTML = `
      <div class="history-card-top">
        <span class="history-card-id">#${m.id}</span>
        <span class="history-card-time">${formatTimestamp(m.created_at)}</span>
      </div>
      <div class="history-card-snippet">${escapeHtml((m.transcript || "").slice(0, 220))}</div>
    `;
    card.addEventListener("click", () => openMeetingModal(m));
    historyList.appendChild(card);
  });
}

function renderStats(meetings) {
  document.getElementById("statTotal").textContent = meetings.length;

  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const thisWeek = meetings.filter(m => {
    const d = parseBackendDate(m.created_at);
    return d && d >= weekAgo;
  }).length;
  document.getElementById("statWeek").textContent = thisWeek;

  const mostRecent = meetings.reduce((latest, m) => {
    const d = parseBackendDate(m.created_at);
    if (!d) return latest;
    return (!latest || d > latest) ? d : latest;
  }, null);
  document.getElementById("statLast").textContent = mostRecent ? relativeTime(mostRecent) : "—";
}

function parseBackendDate(ts) {
  if (!ts) return null;
  // backend format: "2026-07-14 17:54:36" -> make it ISO-parseable
  const iso = ts.replace(" ", "T");
  const d = new Date(iso);
  return isNaN(d) ? null : d;
}

function relativeTime(date) {
  const diffMs = Date.now() - date.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ============================================
// SEARCH
// ============================================
const searchInput = document.getElementById("searchInput");
let searchDebounce = null;

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  const keyword = searchInput.value.trim();
  searchDebounce = setTimeout(async () => {
    switchView("history");
    if (!keyword) {
      renderHistoryList(allMeetings);
      return;
    }
    try {
      const results = await fetchSearch(keyword);
      renderHistoryList(results);
    } catch (e) {
      showToast(e.message, true);
    }
  }, 350);
});

// ============================================
// MEETING DETAIL MODAL
// ============================================
const modalOverlay = document.getElementById("modalOverlay");
const modalTitle = document.getElementById("modalTitle");
const modalTimestamp = document.getElementById("modalTimestamp");
const modalRail = document.getElementById("modalRail");
const modalTranscript = document.getElementById("modalTranscript");
const modalClose = document.getElementById("modalClose");
const exportMdBtn = document.getElementById("exportMdBtn");
const exportPdfBtn = document.getElementById("exportPdfBtn");
let currentMeetingId = null;

function openMeetingModal(meeting) {
  currentMeetingId = meeting.id;
  modalData = meeting;
  modalTitle.textContent = `Meeting #${meeting.id}`;
  modalTimestamp.textContent = formatTimestamp(meeting.created_at);
  modalRail.innerHTML = renderRail(meeting, "modal");
  modalTranscript.textContent = meeting.transcript || "";
  modalOverlay.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeMeetingModal() {
  modalOverlay.hidden = true;
  document.body.style.overflow = "";
  currentMeetingId = null;
}

modalClose.addEventListener("click", closeMeetingModal);
modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) closeMeetingModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalOverlay.hidden) closeMeetingModal();
});

exportMdBtn.addEventListener("click", () => {
  if (currentMeetingId == null) return;
  window.open(`${API_BASE_URL}/export/markdown/${currentMeetingId}`, "_blank");
});
exportPdfBtn.addEventListener("click", () => {
  if (currentMeetingId == null) return;
  window.open(`${API_BASE_URL}/export/pdf/${currentMeetingId}`, "_blank");
});

// ============================================
// THEME TOGGLE BINDING
// ============================================
document.getElementById("themeToggle").addEventListener("click", toggleTheme);

// ============================================
// INIT
// ============================================
initTheme();



