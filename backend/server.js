const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");
const { extractRequirements } = require("./ai/queryAgent");
const app = express();
const PORT = 5000;
const AI_SERVICE_URL = "http://localhost:5001";

app.use(cors());
app.use(express.json());

// Serve frontend static files
app.use(express.static(path.join(__dirname, "../frontend")));

// ============================================
// LOAD INTERNSHIP DATA
// ============================================

const dataPath = path.join(__dirname, "../data/internships.json");

const rawData = JSON.parse(
  fs.readFileSync(dataPath, "utf-8")
);

// Support both:
// 1. internships.json containing an array
// 2. internships.json containing a single object

const internships = Array.isArray(rawData)
  ? rawData
  : [rawData];

console.log(`Loaded ${internships.length} internship(s)`);

function normalizeText(value) {
  return String(value || "").toLowerCase().trim();
}

function asArray(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function findLocalMatches(requirements, limit = 10) {
  const studentProfile = requirements?.student_profile || {};
  const requirementBlock = requirements?.requirements || {};

  const branch = normalizeText(studentProfile.branch);
  const year = Number(studentProfile.year);
  const domains = asArray(requirementBlock.domain).map(normalizeText).filter(Boolean);
  const locations = asArray(requirementBlock.location).map(normalizeText).filter(Boolean);
  const workModes = asArray(requirementBlock.work_mode).map(normalizeText).filter(Boolean);
  const stipendType = normalizeText(requirementBlock.stipend?.type);
  const minStipend = Number(requirementBlock.stipend?.minimum || 0) || 0;

  const scored = internships
    .map((internship) => {
      const reasons = [];
      const scoreBreakdown = {
        location: 0,
        domain: 0,
        eligibility: 0,
        stipend: 0,
        work_mode: 0
      };

      const internshipLocation = normalizeText(internship.location);
      const internshipDomains = asArray(internship.domain).map(normalizeText);
      const internshipBranches = asArray(internship.eligible_branches).map(normalizeText);
      const internshipYears = asArray(internship.eligible_years).map((value) => Number(value));
      const internshipWorkMode = normalizeText(internship.work_mode);
      const stipend = Number(internship.stipend || 0);

      if (locations.length === 0 || locations.some((location) => internshipLocation.includes(location))) {
        scoreBreakdown.location = locations.length ? 25 : 10;
        if (locations.length) reasons.push(`Location matches ${internship.location}`);
      }

      if (domains.length === 0 || domains.some((domain) => internshipDomains.some((item) => item.includes(domain) || domain.includes(item)))) {
        scoreBreakdown.domain = domains.length ? 25 : 10;
        if (domains.length) reasons.push(`Domain matches ${asArray(internship.domain).join(", ")}`);
      }

      const branchMatch = !branch || internshipBranches.includes(branch);
      const yearMatch = !year || internshipYears.includes(year);
      if (branchMatch && yearMatch) {
        scoreBreakdown.eligibility = 30;
        if (branch) reasons.push(`Eligible for ${studentProfile.branch}${year ? `, Year ${year}` : ""}`);
      } else if (branchMatch || yearMatch) {
        scoreBreakdown.eligibility = 15;
        if (branchMatch) reasons.push(`Branch matches ${studentProfile.branch}`);
        if (yearMatch) reasons.push(`Year matches ${year}`);
      }

      if (stipend > 0 && (stipendType === "paid" || stipend >= minStipend)) {
        scoreBreakdown.stipend = 15;
        reasons.push(`Paid internship with ₹${stipend.toLocaleString()}/mo stipend`);
      }

      if (!workModes.length || workModes.some((mode) => internshipWorkMode.includes(mode))) {
        scoreBreakdown.work_mode = workModes.length ? 5 : 0;
        if (workModes.length) reasons.push(`Work mode matches ${internship.work_mode}`);
      }

      const totalScore = Object.values(scoreBreakdown).reduce((sum, value) => sum + value, 0);

      return {
        internship,
        totalScore,
        reasons,
        scoreBreakdown
      };
    })
    .filter((item) => item.totalScore > 0)
    .sort((a, b) => b.totalScore - a.totalScore || Number(b.internship.stipend || 0) - Number(a.internship.stipend || 0));

  return scored.slice(0, limit).map((item) => ({
    ...item.internship,
    match_percentage: Math.min(98, item.totalScore + 20),
    explanation: {
      reasons: item.reasons.length ? item.reasons : ["Matched local internship data"],
      score_breakdown: item.scoreBreakdown,
      details: {
        source: "local_fallback"
      }
    },
    freshness: {
      status: "fresh",
      label: "Local fallback",
      deadline_status: "unknown",
      days_until_deadline: null
    }
  }));
}


// ============================================
// TEST API
// ============================================

app.get("/", (req, res) => {
  res.json({
    message: "AI Internship Discovery API is running"
  });
});


// ============================================
// GET ALL INTERNSHIPS
// ============================================

app.get("/api/internships", (req, res) => {
  res.json({
    count: internships.length,
    results: internships
  });
});


// ============================================
// SEARCH INTERNSHIPS
// ============================================

app.get("/api/internships/search", (req, res) => {

  const {
    location,
    domain,
    work_mode,
    min_stipend
  } = req.query;

  let results = internships;


  // -----------------------------
  // LOCATION FILTER
  // -----------------------------

  if (location) {

    results = results.filter((internship) =>
      internship.location
        ?.toLowerCase()
        .includes(location.toLowerCase())
    );

  }


  // -----------------------------
  // DOMAIN FILTER
  // -----------------------------

  if (domain) {

    results = results.filter((internship) =>
      internship.domain?.some((d) =>
        d.toLowerCase().includes(domain.toLowerCase())
      )
    );

  }


  // -----------------------------
  // WORK MODE FILTER
  // -----------------------------

  if (work_mode) {

    results = results.filter(
      (internship) =>
        internship.work_mode
          ?.toLowerCase() === work_mode.toLowerCase()
    );

  }


  // -----------------------------
  // MINIMUM STIPEND FILTER
  // -----------------------------

  if (min_stipend) {

    results = results.filter(
      (internship) =>
        Number(internship.stipend) >= Number(min_stipend)
    );

  }


  // -----------------------------
  // RETURN RESULTS
  // -----------------------------

  res.json({
    count: results.length,
    results
  });

});

// ============================================
// AI REQUIREMENT EXTRACTION
// ============================================

app.post("/api/ai/understand", async (req, res) => {

  try {

    const { prompt } = req.body;

    // Check whether prompt was provided
    if (!prompt) {
      return res.status(400).json({
        error: "Prompt is required"
      });
    }

    // Send student prompt to Qwen
    const requirements = await extractRequirements(prompt);

    // Return structured requirements
    res.json({
      success: true,
      original_prompt: prompt,
      requirements: requirements
    });

  } catch (error) {

    console.error("AI extraction error:", error);

    res.status(500).json({
      success: false,
      error: "Failed to understand the student prompt"
    });

  }

});
// ============================================
// AI FULL PIPELINE — PHASES 1–10
// ============================================

app.post("/api/ai/search", async (req, res) => {

  try {

    const { prompt } = req.body;

    if (!prompt) {
      return res.status(400).json({
        error: "Prompt is required"
      });
    }

    console.log("\n===== FULL PIPELINE =====");
    console.log("Student prompt:", prompt);

    // ── Phase 1: Extract requirements via Qwen ──
    console.log("\n▶ Phase 1: Extracting requirements...");
    const requirements = await extractRequirements(prompt);

    console.log("Extracted:", JSON.stringify(requirements, null, 2));

    // Check if clarification is needed
    if (requirements.clarification?.required) {
      return res.json({
        success: true,
        needs_clarification: true,
        clarification_question: requirements.clarification.question,
        partial_requirements: requirements
      });
    }

    // ── Phases 2–10: Send to Flask AI service ───
    console.log("\n▶ Phases 2–10: Sending to AI pipeline...");

    const aiResponse = await fetch("http://localhost:5001/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requirements: requirements,
        top_n: 20,
        max_results: 10
      })
    });

    if (!aiResponse.ok) {
      const errorText = await aiResponse.text();
      throw new Error(
        `AI pipeline error: ${aiResponse.status} — ${errorText}`
      );
    }

    const pipelineResult = await aiResponse.json();

    if (!pipelineResult.success) {
      console.warn("Flask pipeline failed, using local fallback:", pipelineResult.error);
      const fallbackResults = findLocalMatches(requirements, 10);

      return res.json({
        success: true,
        original_prompt: prompt,
        extracted_requirements: requirements,
        search_query: pipelineResult.search_query || prompt,
        results: fallbackResults,
        pipeline_stats: {
          ...(pipelineResult.pipeline_stats || {}),
          fallback_used: true,
          fallback_source: "local_dataset",
          execution_time_ms: pipelineResult.pipeline_stats?.execution_time_ms
        },
        total_results: fallbackResults.length,
        fallback_used: true,
        fallback_reason: pipelineResult.error || "AI pipeline returned an error"
      });
    }

    const responseResults = pipelineResult.results || [];

    if (responseResults.length === 0) {
      const fallbackResults = findLocalMatches(requirements, 10);

      if (fallbackResults.length > 0) {
        console.warn("AI pipeline returned no results, using local fallback dataset.");

        return res.json({
          success: true,
          original_prompt: prompt,
          extracted_requirements: requirements,
          search_query: pipelineResult.search_query || prompt,
          results: fallbackResults,
          pipeline_stats: {
            ...(pipelineResult.pipeline_stats || {}),
            fallback_used: true,
            fallback_source: "local_dataset"
          },
          total_results: fallbackResults.length,
          fallback_used: true
        });
      }
    }

    console.log("\n✓ Pipeline complete");
    console.log(`  Results: ${responseResults.length}`);
    console.log("===== END PIPELINE =====\n");

    // Return combined response
    res.json({
      success: true,
      original_prompt: prompt,
      extracted_requirements: requirements,
      search_query: pipelineResult.search_query,
      results: responseResults,
      pipeline_stats: pipelineResult.pipeline_stats,
      total_results: responseResults.length,
      fallback_used: false
    });

  } catch (error) {

    console.error("Pipeline error:", error);

    res.status(500).json({
      success: false,
      error: "Failed to process the search request",
      details: error.message
    });

  }

});

// ============================================
// ORGANIZATION AUTH / SUBMISSION PROXY
// ============================================

app.post("/api/organization/login", async (req, res) => {
  try {
    const aiResponse = await fetch(`${AI_SERVICE_URL}/api/organization/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body || {})
    });

    const payload = await aiResponse.json();
    res.status(aiResponse.status).json(payload);
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message || "Organization login failed"
    });
  }
});

app.post("/api/organization/internships", async (req, res) => {
  try {
    const token = req.headers.authorization || req.headers["x-org-token"] || "";

    const aiResponse = await fetch(`${AI_SERVICE_URL}/api/organization/internships`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": token,
        "X-Org-Token": req.headers["x-org-token"] || ""
      },
      body: JSON.stringify(req.body || {})
    });

    const payload = await aiResponse.json();
    res.status(aiResponse.status).json(payload);
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message || "Organization submission failed"
    });
  }
});


// ============================================
// START SERVER
// ============================================

app.listen(PORT, () => {

  console.log(
    `Server running at http://localhost:${PORT}`
  );

});