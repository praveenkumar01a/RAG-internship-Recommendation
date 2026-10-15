"""
Phase 9 — Final Ranking

Combines scores from all pipeline phases into a single
match percentage for each internship candidate.

Score weights:
    - Semantic similarity (Phase 5):  30%
    - Reranker relevance (Phase 7):   25%
    - Eligibility fit (Phase 6):      20%
    - Freshness score (Phase 8):      15%
    - Preference match (misc):        10%
"""


def compute_final_ranking(candidates, hard_filters):
    """
    Compute the final match percentage for each candidate.

    Combines:
        1. semantic_score  — cosine similarity from pgvector
        2. reranker_score  — Qwen relevance score
        3. eligibility_fit — how well eligibility criteria match
        4. freshness_score — deadline + verification recency
        5. preference_score — stipend/location/skill preference fit

    Args:
        candidates (list[dict]): Candidates with scores from prior phases.
        hard_filters (dict): Student's requirements for preference scoring.

    Returns:
        list[dict]: Candidates sorted by match_percentage (desc),
                    each with a "final_scores" breakdown.
    """
    for candidate in candidates:
        scores = {}

        # ── 1. Semantic Score (30%) ──────────────
        # Cosine similarity from Phase 5 (0.0 to 1.0)
        raw_sim = candidate.get("similarity_score", 0.5)
        scores["semantic"] = max(0.0, min(1.0, float(raw_sim)))

        # ── 2. Reranker Score (25%) ──────────────
        # Qwen relevance score from Phase 7 (0 to 100 → normalize)
        raw_rerank = candidate.get("rerank_score", 50)
        scores["reranker"] = max(0.0, min(1.0, raw_rerank / 100.0))

        # ── 3. Eligibility Fit (20%) ─────────────
        scores["eligibility"] = _compute_eligibility_score(candidate)

        # ── 4. Freshness Score (15%) ─────────────
        freshness = candidate.get("freshness", {})
        scores["freshness"] = freshness.get("freshness_score", 0.5)

        # ── 5. Preference Score (10%) ────────────
        scores["preference"] = _compute_preference_score(
            candidate, hard_filters
        )

        # ── Weighted combination ─────────────────
        match_pct = (
            scores["semantic"]    * 0.30 +
            scores["reranker"]    * 0.25 +
            scores["eligibility"] * 0.20 +
            scores["freshness"]   * 0.15 +
            scores["preference"]  * 0.10
        ) * 100  # Convert to percentage

        candidate["match_percentage"] = round(match_pct, 1)
        candidate["final_scores"] = {
            k: round(v, 3) for k, v in scores.items()
        }

    # Sort by match percentage descending
    candidates.sort(
        key=lambda x: x.get("match_percentage", 0),
        reverse=True
    )

    return candidates


def _compute_eligibility_score(candidate):
    """
    Compute an eligibility fit score (0.0 to 1.0) based on
    how many eligibility criteria the candidate passes.
    """
    details = candidate.get("eligibility_details", {})

    if not details:
        return 1.0  # No details = assume passed

    checks = ["branch", "year", "experience", "stipend"]
    passed = 0
    total = 0

    for check in checks:
        info = details.get(check, {})
        if info.get("reason") == "Not specified":
            continue  # Skip unspecified checks
        total += 1
        if info.get("passed", False):
            passed += 1

    # Also factor in location/work_mode (softer)
    loc_info = details.get("location_work_mode", {})
    if loc_info:
        total += 1
        if loc_info.get("passed", False):
            passed += 1

    if total == 0:
        return 1.0

    return passed / total


def _compute_preference_score(candidate, hard_filters):
    """
    Compute a preference match score (0.0 to 1.0) based on
    how well the internship matches the student's softer preferences.

    Factors:
        - Skill overlap
        - Stipend satisfaction
        - Location exactness
    """
    score = 0.0
    components = 0

    # ── Skill overlap ────────────────────────────
    student_skills = set(
        s.lower() for s in hard_filters.get("skills", [])
    )
    internship_skills = set(
        s.lower() for s in (candidate.get("skills") or [])
    )

    if student_skills and internship_skills:
        overlap = student_skills & internship_skills
        skill_score = len(overlap) / len(student_skills)
        score += skill_score
        components += 1

    # ── Stipend satisfaction ─────────────────────
    stipend_min = hard_filters.get("stipend_minimum")
    internship_stipend = candidate.get("stipend", 0)

    if hard_filters.get("stipend_type") == "paid":
        if internship_stipend > 0:
            if stipend_min and stipend_min > 0:
                # How much above minimum?
                ratio = min(2.0, internship_stipend / stipend_min)
                score += min(1.0, ratio)
            else:
                score += 1.0  # Just wants paid, and it is paid
        else:
            score += 0.0  # Wants paid but it's unpaid
        components += 1

    # ── Location exactness ───────────────────────
    student_locations = [
        l.lower() for l in hard_filters.get("locations", [])
    ]
    internship_location = (candidate.get("location") or "").lower()

    if student_locations:
        if any(loc in internship_location for loc in student_locations):
            score += 1.0  # Exact location match
        elif (candidate.get("work_mode") or "").lower() == "remote":
            score += 0.8  # Remote is acceptable
        else:
            score += 0.3  # Different location
        components += 1

    if components == 0:
        return 0.5  # No preferences to evaluate

    return score / components


# ─────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_candidate = {
        "title": "ML Intern",
        "similarity_score": 0.85,
        "rerank_score": 90,
        "eligibility_passed": True,
        "eligibility_details": {
            "branch": {"passed": True},
            "year": {"passed": True},
            "experience": {"passed": True},
            "stipend": {"passed": True},
            "location_work_mode": {"passed": True}
        },
        "freshness": {"freshness_score": 0.9},
        "skills": ["Python", "TensorFlow", "SQL"],
        "stipend": 25000,
        "location": "Chennai",
        "work_mode": "Hybrid"
    }

    test_filters = {
        "branch": "CSE",
        "year": 3,
        "skills": ["Python", "TensorFlow"],
        "stipend_type": "paid",
        "stipend_minimum": 20000,
        "locations": ["Chennai"],
        "work_modes": ["remote"],
        "domains": ["AI"],
        "experience_years": 0
    }

    results = compute_final_ranking([test_candidate], test_filters)

    for r in results:
        print(f"{r['title']}: {r['match_percentage']}% match")
        print(f"  Breakdown: {r['final_scores']}")
