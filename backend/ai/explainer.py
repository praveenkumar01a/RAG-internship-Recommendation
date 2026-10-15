"""
Phase 10 — Explain Results

Generates human-readable explanations for why each internship
was recommended, including match reasons and score breakdowns.
"""


def generate_explanations(candidates, hard_filters):
    """
    Generate human-readable match explanations for each candidate.

    For each internship, produces:
        - Match percentage headline
        - Domain/skill match reasons
        - Eligibility details
        - Stipend/location info
        - Freshness status

    Args:
        candidates (list[dict]): Ranked candidates from Phase 9.
        hard_filters (dict): Student's requirements for context.

    Returns:
        list[dict]: Candidates with added "explanation" field
                    containing structured match reasons.
    """
    for candidate in candidates:
        explanation = {
            "match_percentage": candidate.get("match_percentage", 0),
            "reasons": [],
            "details": {}
        }

        # ── Domain Match ─────────────────────────
        student_domains = set(
            d.lower() for d in hard_filters.get("domains", [])
        )
        internship_domains = set(
            d.lower() for d in (candidate.get("domain") or [])
        )

        if student_domains and internship_domains:
            overlap = student_domains & internship_domains
            if overlap:
                matched = ", ".join(
                    d for d in candidate.get("domain", [])
                    if d.lower() in overlap
                )
                explanation["reasons"].append(
                    f"🎯 {matched} matches your interest"
                )
            else:
                # Check for related domains
                all_domains = ", ".join(candidate.get("domain", []))
                explanation["reasons"].append(
                    f"📌 Related domain: {all_domains}"
                )

        # ── Skill Match ──────────────────────────
        student_skills = set(
            s.lower() for s in hard_filters.get("skills", [])
        )
        internship_skills = set(
            s.lower() for s in (candidate.get("skills") or [])
        )

        if student_skills and internship_skills:
            overlap = student_skills & internship_skills
            if overlap:
                matched_skills = [
                    s for s in candidate.get("skills", [])
                    if s.lower() in overlap
                ]
                explanation["reasons"].append(
                    f"💡 Your skills match: {', '.join(matched_skills)}"
                )

            # Mention skills student could learn
            new_skills = internship_skills - student_skills
            if new_skills:
                learn_list = [
                    s for s in candidate.get("skills", [])
                    if s.lower() in new_skills
                ][:3]  # Limit to 3
                explanation["details"]["new_skills"] = learn_list

        # ── Eligibility ──────────────────────────
        branch = hard_filters.get("branch")
        year = hard_filters.get("year")

        if branch and year:
            eligible_years = candidate.get("eligible_years", [])
            eligible_branches = candidate.get("eligible_branches", [])
            explanation["reasons"].append(
                f"✅ {branch} + Year {year} eligible"
            )
            explanation["details"]["eligible_branches"] = eligible_branches
            explanation["details"]["eligible_years"] = eligible_years

        # ── Stipend Info ─────────────────────────
        stipend = candidate.get("stipend", 0)
        if stipend > 0:
            explanation["reasons"].append(
                f"💰 Paid ₹{stipend:,}/month"
            )
        else:
            explanation["reasons"].append("📋 Unpaid internship")

        # ── Location & Work Mode ─────────────────
        location = candidate.get("location", "Not specified")
        work_mode = candidate.get("work_mode", "Not specified")
        explanation["reasons"].append(
            f"📍 {location} / {work_mode}"
        )

        # ── Duration ─────────────────────────────
        duration = candidate.get("duration_months")
        if duration:
            explanation["details"]["duration"] = f"{duration} months"

        # ── Organization ─────────────────────────
        org = candidate.get("organization")
        if org:
            explanation["details"]["organization"] = org

        # ── Freshness ────────────────────────────
        freshness = candidate.get("freshness", {})
        freshness_label = freshness.get("freshness_label")
        if freshness_label:
            explanation["reasons"].append(freshness_label)

        deadline_status = freshness.get("deadline_status")
        days_until = freshness.get("days_until_deadline")
        if deadline_status == "closing_soon" and days_until is not None:
            explanation["reasons"].append(
                f"⚡ Apply soon — {days_until} days left!"
            )

        # ── Reranker Insight ─────────────────────
        rerank_reason = candidate.get("rerank_reason")
        if rerank_reason:
            explanation["details"]["ai_assessment"] = rerank_reason

        # ── Score Breakdown ──────────────────────
        final_scores = candidate.get("final_scores", {})
        if final_scores:
            explanation["score_breakdown"] = {
                "Semantic Relevance": f"{final_scores.get('semantic', 0) * 100:.0f}%",
                "AI Relevance Score": f"{final_scores.get('reranker', 0) * 100:.0f}%",
                "Eligibility Fit": f"{final_scores.get('eligibility', 0) * 100:.0f}%",
                "Freshness": f"{final_scores.get('freshness', 0) * 100:.0f}%",
                "Preference Match": f"{final_scores.get('preference', 0) * 100:.0f}%"
            }

        candidate["explanation"] = explanation

    return candidates


def format_results_text(candidates):
    """
    Format results as a human-readable text string.
    Useful for CLI/debugging output.

    Args:
        candidates (list[dict]): Candidates with explanations.

    Returns:
        str: Formatted text output.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  INTERNSHIP RECOMMENDATIONS")
    lines.append("=" * 60)

    for i, candidate in enumerate(candidates, 1):
        explanation = candidate.get("explanation", {})
        pct = explanation.get("match_percentage", 0)

        lines.append(f"\n{'─' * 50}")
        lines.append(f"  #{i}  {candidate.get('title', 'Unknown')}")
        lines.append(f"       at {candidate.get('organization', 'Unknown')}")
        lines.append(f"       {pct}% Match")
        lines.append(f"{'─' * 50}")

        reasons = explanation.get("reasons", [])
        for reason in reasons:
            lines.append(f"  {reason}")

        breakdown = explanation.get("score_breakdown", {})
        if breakdown:
            lines.append(f"\n  Score Breakdown:")
            for key, value in breakdown.items():
                lines.append(f"    {key}: {value}")

    lines.append(f"\n{'=' * 60}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_candidate = {
        "title": "ML Intern",
        "organization": "ABC Tech",
        "domain": ["AI", "Machine Learning"],
        "skills": ["Python", "TensorFlow", "SQL"],
        "eligible_branches": ["CSE", "AI"],
        "eligible_years": [3, 4],
        "location": "Chennai",
        "work_mode": "Hybrid",
        "stipend": 25000,
        "duration_months": 3,
        "match_percentage": 92.5,
        "final_scores": {
            "semantic": 0.85,
            "reranker": 0.90,
            "eligibility": 1.0,
            "freshness": 0.9,
            "preference": 0.95
        },
        "freshness": {
            "freshness_label": "✅ Verified 2 hours ago",
            "deadline_status": "open",
            "days_until_deadline": 24
        },
        "rerank_reason": "Strong AI/ML match with relevant skills"
    }

    test_filters = {
        "branch": "CSE",
        "year": 3,
        "domains": ["AI", "Machine Learning"],
        "skills": ["Python", "TensorFlow"],
        "stipend_type": "paid",
        "stipend_minimum": None,
        "locations": ["Chennai"],
        "work_modes": ["remote"],
        "experience_years": 0
    }

    results = generate_explanations([test_candidate], test_filters)
    print(format_results_text(results))
