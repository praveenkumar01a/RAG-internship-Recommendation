/* ═══════════════════════════════════════════
   AI INTERNSHIP DISCOVERY — APP LOGIC
   ═══════════════════════════════════════════ */

const API_BASE = "http://localhost:5000";

// ── State ───────────────────────────────────
let currentResults = [];
let lastPrompt = "";

// ── DOM References ──────────────────────────
const heroSection = document.getElementById("heroSection");
const loadingSection = document.getElementById("loadingSection");
const resultsSection = document.getElementById("resultsSection");
const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

// ── Init ────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  });
});

// ── Health Check ────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/`);
    if (res.ok) {
      statusDot.className = "status-dot online";
      statusText.textContent = "System Online";
    }
  } catch {
    statusDot.className = "status-dot error";
    statusText.textContent = "Backend Offline";
  }
}

// ── Search ──────────────────────────────────
async function handleSearch() {
  const prompt = searchInput.value.trim();
  if (!prompt) return;

  lastPrompt = prompt;
  showSection("loading");
  animatePipeline();

  try {
    const res = await fetch(`${API_BASE}/api/ai/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    });

    const data = await res.json();

    // Complete pipeline animation
    await completePipelineAnimation();

    if (data.needs_clarification) {
      showClarification(data.clarification_question, data.partial_requirements);
      return;
    }

    if (data.success) {
      currentResults = data.results || [];
      renderResults(data);
    } else {
      showError(data.error || "Something went wrong");
    }
  } catch (err) {
    await completePipelineAnimation();
    showError("Could not connect to the backend. Make sure both servers are running.");
    console.error(err);
  }
}

// ── Clarification Flow ──────────────────────
function showClarification(question, partialReqs) {
  showSection("results");

  const panel = document.getElementById("clarificationPanel");
  const text = document.getElementById("clarificationText");
  const grid = document.getElementById("resultsGrid");
  const noRes = document.getElementById("noResults");
  const reqPanel = document.getElementById("requirementsPanel");

  panel.classList.remove("hidden");
  grid.innerHTML = "";
  noRes.classList.add("hidden");
  reqPanel.classList.add("hidden");

  text.textContent = question;

  document.getElementById("resultsStats").innerHTML =
    "The AI needs more information to find your matches.";
}

async function handleClarification() {
  const input = document.getElementById("clarificationInput");
  const extra = input.value.trim();
  if (!extra) return;

  // Combine original prompt with clarification
  searchInput.value = lastPrompt + ". " + extra;
  handleSearch();
}

// ── Example Chips ───────────────────────────
function useExample(btn) {
  searchInput.value = btn.textContent;
  searchInput.focus();
}

// ── Pipeline Animation ──────────────────────
let pipelineInterval = null;

function animatePipeline() {
  const phases = document.querySelectorAll(".phase");
  phases.forEach((p) => { p.className = "phase"; });

  let i = 0;
  pipelineInterval = setInterval(() => {
    if (i > 0 && i <= phases.length) {
      phases[i - 1].classList.remove("active");
      phases[i - 1].classList.add("done");
    }
    if (i < phases.length) {
      phases[i].classList.add("active");
    }
    i++;
    if (i > phases.length) {
      clearInterval(pipelineInterval);
      pipelineInterval = null;
    }
  }, 1500);
}

async function completePipelineAnimation() {
  if (pipelineInterval) {
    clearInterval(pipelineInterval);
    pipelineInterval = null;
  }
  const phases = document.querySelectorAll(".phase");
  phases.forEach((p) => {
    p.classList.remove("active");
    p.classList.add("done");
  });
  await sleep(400);
}

// ── Render Results ──────────────────────────
function renderResults(data) {
  showSection("results");

  const grid = document.getElementById("resultsGrid");
  const noRes = document.getElementById("noResults");
  const stats = document.getElementById("resultsStats");
  const clPanel = document.getElementById("clarificationPanel");

  clPanel.classList.add("hidden");

  // Stats
  const ps = data.pipeline_stats || {};
  stats.innerHTML = `
    <strong>${data.total_results}</strong> matches found &nbsp;·&nbsp;
    ${ps.semantic_matches || "?"} searched &nbsp;·&nbsp;
    ${ps.after_eligibility || "?"} eligible &nbsp;·&nbsp;
    ${ps.after_freshness || "?"} fresh &nbsp;·&nbsp;
    ${(ps.execution_time_ms / 1000).toFixed(1)}s
  `;

  // Requirements panel
  renderRequirements(data.extracted_requirements, data.search_query);

  // Results
  if (!data.results || data.results.length === 0) {
    grid.innerHTML = "";
    noRes.classList.remove("hidden");
    return;
  }

  noRes.classList.add("hidden");
  grid.innerHTML = data.results.map((r, i) => renderCard(r, i)).join("");
}

function renderCard(result, index) {
  const pct = result.match_percentage || 0;
  const matchClass = pct >= 85 ? "high" : pct >= 70 ? "medium" : "low";
  const explanation = result.explanation || {};
  const reasons = (explanation.reasons || []).slice(0, 4);
  const freshness = result.freshness || {};
  const fStatus = freshness.status || "unknown";
  const fLabel = freshness.label || "";
  const fClass = fStatus === "fresh" || fStatus === "recent" ? "fresh"
               : fStatus === "closing_soon" ? "closing" : "stale";

  const domains = (result.domain || []).map(d =>
    `<span class="domain-tag">${escapeHtml(d)}</span>`
  ).join("");

  const reasonsHtml = reasons.map(r =>
    `<div class="reason-item">${escapeHtml(r)}</div>`
  ).join("");

  const delay = index * 0.08;

  return `
    <div class="result-card" style="animation-delay: ${delay}s" onclick="openModal(${index})">
      <div class="card-top">
        <div>
          <div class="card-rank">#${index + 1} Result</div>
          <div class="card-title">${escapeHtml(result.title)}</div>
          <div class="card-org">${escapeHtml(result.organization)}</div>
        </div>
        <div class="card-match">
          <div class="match-circle ${matchClass}">
            ${pct}%
            <span class="match-label">match</span>
          </div>
        </div>
      </div>

      <div class="card-meta">
        <span class="meta-item"><span class="meta-icon">💰</span> ₹${(result.stipend || 0).toLocaleString()}/mo</span>
        <span class="meta-item"><span class="meta-icon">📍</span> ${escapeHtml(result.location || "N/A")}</span>
        <span class="meta-item"><span class="meta-icon">🏢</span> ${escapeHtml(result.work_mode || "N/A")}</span>
        <span class="meta-item"><span class="meta-icon">⏱</span> ${result.duration_months || "?"} months</span>
      </div>

      <div class="card-domains">${domains}</div>

      <div class="card-reasons">${reasonsHtml}</div>

      <div class="card-freshness">
        <span class="freshness-badge ${fClass}">${escapeHtml(fLabel)}</span>
        <span class="view-details">View Details →</span>
      </div>
    </div>
  `;
}

// ── Requirements Panel ──────────────────────
function renderRequirements(reqs, searchQuery) {
  const panel = document.getElementById("requirementsPanel");
  const tagsEl = document.getElementById("reqTags");
  const queryEl = document.getElementById("reqQuery");

  if (!reqs) {
    panel.classList.add("hidden");
    return;
  }

  panel.classList.remove("hidden");

  const tags = [];
  const sp = reqs.student_profile || {};
  const rq = reqs.requirements || {};
  const stipend = rq.stipend || {};

  if (sp.branch) tags.push({ label: sp.branch, cls: "branch" });
  if (sp.year) tags.push({ label: `Year ${sp.year}`, cls: "branch" });
  if (sp.degree) tags.push({ label: sp.degree, cls: "branch" });

  (rq.domain || []).forEach(d => tags.push({ label: d, cls: "domain" }));
  (sp.skills || []).forEach(s => tags.push({ label: s, cls: "skill" }));
  (rq.location || []).forEach(l => tags.push({ label: l, cls: "location" }));
  (rq.work_mode || []).forEach(w => tags.push({ label: w, cls: "work-mode" }));

  if (stipend.type) tags.push({ label: stipend.type, cls: "stipend" });
  if (stipend.minimum) tags.push({ label: `≥₹${stipend.minimum}`, cls: "stipend" });

  tagsEl.innerHTML = tags.map(t =>
    `<span class="req-tag ${t.cls}">${escapeHtml(t.label)}</span>`
  ).join("");

  queryEl.innerHTML = searchQuery
    ? `<strong>Search query:</strong> "${escapeHtml(searchQuery)}"`
    : "";
}

function toggleRequirements() {
  const body = document.getElementById("reqBody");
  const chevron = document.getElementById("reqChevron");
  body.classList.toggle("collapsed");
  chevron.classList.toggle("open");
}

// ── Detail Modal ────────────────────────────
function openModal(index) {
  const r = currentResults[index];
  if (!r) return;

  const overlay = document.getElementById("modalOverlay");
  const content = document.getElementById("modalContent");
  const explanation = r.explanation || {};
  const breakdown = explanation.score_breakdown || {};
  const details = explanation.details || {};
  const freshness = r.freshness || {};

  const skillsHtml = (r.skills || []).map(s => {
    const matched = (explanation.reasons || []).some(
      reason => reason.toLowerCase().includes(s.toLowerCase())
    );
    return `<span class="modal-skill ${matched ? "matched" : ""}">${escapeHtml(s)}</span>`;
  }).join("");

  const scoresHtml = Object.entries(breakdown).map(([label, value]) => {
    const numVal = parseInt(value);
    return `
      <div class="score-bar-row">
        <span class="score-bar-label">${escapeHtml(label)}</span>
        <div class="score-bar-track">
          <div class="score-bar-fill" style="width: ${numVal}%"></div>
        </div>
        <span class="score-bar-value">${escapeHtml(value)}</span>
      </div>
    `;
  }).join("");

  const reasonsHtml = (explanation.reasons || []).map(r =>
    `<div class="reason-item">${escapeHtml(r)}</div>`
  ).join("");

  content.innerHTML = `
    <div class="card-match" style="float:right; margin-left:16px;">
      <div class="match-circle ${r.match_percentage >= 85 ? 'high' : r.match_percentage >= 70 ? 'medium' : 'low'}">
        ${r.match_percentage}%
        <span class="match-label">match</span>
      </div>
    </div>
    <div class="modal-title">${escapeHtml(r.title)}</div>
    <div class="modal-org">${escapeHtml(r.organization)}</div>
    <div class="modal-desc">${escapeHtml(r.description)}</div>

    <div class="modal-section">
      <div class="modal-section-title">Details</div>
      <div class="modal-grid">
        <div class="modal-info">
          <div class="modal-info-label">Stipend</div>
          <div class="modal-info-value">₹${(r.stipend || 0).toLocaleString()}/month</div>
        </div>
        <div class="modal-info">
          <div class="modal-info-label">Location</div>
          <div class="modal-info-value">${escapeHtml(r.location || "N/A")}</div>
        </div>
        <div class="modal-info">
          <div class="modal-info-label">Work Mode</div>
          <div class="modal-info-value">${escapeHtml(r.work_mode || "N/A")}</div>
        </div>
        <div class="modal-info">
          <div class="modal-info-label">Duration</div>
          <div class="modal-info-value">${r.duration_months || "?"} months</div>
        </div>
        <div class="modal-info">
          <div class="modal-info-label">Deadline</div>
          <div class="modal-info-value">${escapeHtml(r.deadline || "N/A")}${freshness.days_until_deadline != null ? ` (${freshness.days_until_deadline}d left)` : ""}</div>
        </div>
        <div class="modal-info">
          <div class="modal-info-label">Start Date</div>
          <div class="modal-info-value">${escapeHtml(r.start_date || "N/A")}</div>
        </div>
      </div>
    </div>

    <div class="modal-section">
      <div class="modal-section-title">Why This Matches</div>
      <div class="card-reasons">${reasonsHtml}</div>
    </div>

    <div class="modal-section">
      <div class="modal-section-title">Score Breakdown</div>
      <div class="score-bars">${scoresHtml}</div>
    </div>

    <div class="modal-section">
      <div class="modal-section-title">Required Skills</div>
      <div class="modal-skills">${skillsHtml}</div>
      ${details.new_skills && details.new_skills.length > 0 ? `
        <div style="margin-top:10px; font-size:0.78rem; color:var(--text-muted);">
          📚 Skills you could learn: ${details.new_skills.join(", ")}
        </div>
      ` : ""}
    </div>

    ${r.source_url ? `
      <a href="${escapeHtml(r.source_url)}" target="_blank" class="modal-link">
        🔗 View Original Posting (${escapeHtml(r.source || "source")})
      </a>
    ` : ""}
  `;

  overlay.classList.remove("hidden");
  document.body.style.overflow = "hidden";

  // Animate score bars after modal opens
  setTimeout(() => {
    content.querySelectorAll(".score-bar-fill").forEach(bar => {
      bar.style.width = bar.style.width; // Trigger reflow
    });
  }, 100);
}

function closeModal(event) {
  if (event && event.target !== document.getElementById("modalOverlay")) return;
  document.getElementById("modalOverlay").classList.add("hidden");
  document.body.style.overflow = "";
}

// ── Section Navigation ──────────────────────
function showSection(section) {
  heroSection.classList.add("hidden");
  loadingSection.classList.add("hidden");
  resultsSection.classList.add("hidden");

  if (section === "hero") heroSection.classList.remove("hidden");
  if (section === "loading") loadingSection.classList.remove("hidden");
  if (section === "results") resultsSection.classList.remove("hidden");
}

function goBack() {
  showSection("hero");
  searchInput.focus();
}

// ── Error Display ───────────────────────────
function showError(message) {
  showSection("results");
  document.getElementById("resultsGrid").innerHTML = "";
  document.getElementById("requirementsPanel").classList.add("hidden");
  document.getElementById("clarificationPanel").classList.add("hidden");

  const noRes = document.getElementById("noResults");
  noRes.classList.remove("hidden");
  noRes.innerHTML = `
    <div class="no-results-icon">⚠️</div>
    <h3>Error</h3>
    <p>${escapeHtml(message)}</p>
  `;

  document.getElementById("resultsStats").innerHTML = "";
}

// ── Utilities ───────────────────────────────
function escapeHtml(str) {
  if (!str) return "";
  const el = document.createElement("span");
  el.textContent = str;
  return el.innerHTML;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
