const API_BASE = "http://localhost:5000";
const DEMO_TOKEN_KEY = "internai_org_token";
const DEMO_ORG_KEY = "internai_org_name";

const loginPanel = document.getElementById("loginPanel");
const dashboardPanel = document.getElementById("dashboardPanel");
const loginForm = document.getElementById("loginForm");
const internshipForm = document.getElementById("internshipForm");
const loginMessage = document.getElementById("loginMessage");
const submitMessage = document.getElementById("submitMessage");
const orgWelcome = document.getElementById("orgWelcome");
const logoutBtn = document.getElementById("logoutBtn");

function showMessage(element, text, type = "info") {
  element.textContent = text;
  element.className = `message-box ${type}`;
  element.classList.remove("hidden");
}

function hideMessage(element) {
  element.className = "message-box hidden";
  element.textContent = "";
}

function isLoggedIn() {
  return Boolean(localStorage.getItem(DEMO_TOKEN_KEY));
}

function setDashboardState(organizationName) {
  loginPanel.classList.add("hidden");
  dashboardPanel.classList.remove("hidden");
  orgWelcome.textContent = `Welcome, ${organizationName}`;
  document.getElementById("orgStatusText").textContent = "Authenticated";
}

function setLoginState() {
  dashboardPanel.classList.add("hidden");
  loginPanel.classList.remove("hidden");
  document.getElementById("orgStatusText").textContent = "Portal Ready";
}

function parseListInput(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function restoreSession() {
  const token = localStorage.getItem(DEMO_TOKEN_KEY);
  const orgName = localStorage.getItem(DEMO_ORG_KEY);

  if (token) {
    setDashboardState(orgName || "Organization");
  } else {
    setLoginState();
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideMessage(loginMessage);

  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  try {
    const response = await fetch(`${API_BASE}/api/organization/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      showMessage(loginMessage, data.error || "Login failed", "error");
      return;
    }

    localStorage.setItem(DEMO_TOKEN_KEY, data.token);
    localStorage.setItem(DEMO_ORG_KEY, data.organization?.name || "Organization");
    setDashboardState(data.organization?.name || "Organization");
    showMessage(submitMessage, "Login successful. You can now add internships.", "success");
  } catch (error) {
    showMessage(loginMessage, "Unable to connect to the server.", "error");
  }
});

internshipForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideMessage(submitMessage);

  const token = localStorage.getItem(DEMO_TOKEN_KEY);
  if (!token) {
    showMessage(submitMessage, "Please log in first.", "error");
    return;
  }

  const payload = {
    title: document.getElementById("title").value.trim(),
    organization: document.getElementById("organization").value.trim(),
    description: document.getElementById("description").value.trim(),
    domain: parseListInput(document.getElementById("domain").value),
    skills: parseListInput(document.getElementById("skills").value),
    eligible_branches: parseListInput(document.getElementById("eligibleBranches").value),
    eligible_years: parseListInput(document.getElementById("eligibleYears").value).map(Number).filter(Number.isFinite),
    location: document.getElementById("location").value.trim(),
    work_mode: document.getElementById("workMode").value.trim(),
    stipend: Number(document.getElementById("stipend").value || 0),
    duration_months: Number(document.getElementById("durationMonths").value || 0) || null,
    start_date: document.getElementById("startDate").value || null,
    deadline: document.getElementById("deadline").value || null,
    source_url: document.getElementById("sourceUrl").value.trim() || null,
    status: "active",
    source: "organization_portal"
  };

  try {
    const response = await fetch(`${API_BASE}/api/organization/internships`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
        "X-Org-Token": token
      },
      body: JSON.stringify({ internship: payload })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      showMessage(submitMessage, data.error || "Failed to save internship.", "error");
      return;
    }

    internshipForm.reset();
    showMessage(
      submitMessage,
      `Saved locally. Record ID ${data.submission?.id} and embedding dimension ${data.submission?.embedding_dimension}.`,
      "success"
    );
  } catch (error) {
    showMessage(submitMessage, "Unable to connect to the server.", "error");
  }
});

logoutBtn.addEventListener("click", () => {
  localStorage.removeItem(DEMO_TOKEN_KEY);
  localStorage.removeItem(DEMO_ORG_KEY);
  setLoginState();
  hideMessage(submitMessage);
});

restoreSession();
