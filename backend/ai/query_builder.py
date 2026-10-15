"""
Phase 2 — Query Preparation

Converts the structured requirements extracted by Qwen (Phase 1)
into a natural-language search query string suitable for embedding.
Also extracts hard filter parameters for Phase 6.
"""


def build_search_query(requirements):
    """
    Build a natural-language search query from structured requirements.

    Takes the JSON output from Qwen (Phase 1) and constructs a
    descriptive query string that captures the student's intent
    for semantic search.

    Args:
        requirements (dict): Structured requirements from Phase 1.
            Expected structure:
            {
                "student_profile": { "branch", "year", "degree", "skills", ... },
                "requirements": { "domain", "location", "work_mode", "stipend", ... },
                "preferences": [...]
            }

    Returns:
        str: A natural-language search query for embedding.

    Example:
        Input:  { domain: ["AI"], branch: "CSE", location: ["Chennai"], ... }
        Output: "AI internship for CSE student in Chennai paid remote"
    """
    parts = []

    student = requirements.get("student_profile", {})
    reqs = requirements.get("requirements", {})
    preferences = requirements.get("preferences", [])

    # ── Domain ───────────────────────────────────
    domains = reqs.get("domain", [])
    if domains:
        parts.append(" ".join(domains))

    # ── Add "internship" keyword ─────────────────
    parts.append("internship")

    # ── Branch / Degree ──────────────────────────
    if student.get("branch"):
        parts.append(f"for {student['branch']} student")

    if student.get("degree"):
        parts.append(student["degree"])

    # ── Skills ───────────────────────────────────
    skills = student.get("skills", [])
    if skills:
        parts.append("skills: " + " ".join(skills))

    # ── Location ─────────────────────────────────
    locations = reqs.get("location", [])
    if locations:
        parts.append("in " + " or ".join(locations))

    # ── Work Mode ────────────────────────────────
    work_modes = reqs.get("work_mode", [])
    if work_modes:
        parts.append(" ".join(work_modes))

    # ── Stipend ──────────────────────────────────
    stipend = reqs.get("stipend", {})
    if stipend:
        stipend_type = stipend.get("type")
        if stipend_type:
            parts.append(stipend_type)

        minimum = stipend.get("minimum")
        if minimum:
            parts.append(f"minimum ₹{minimum}/month")

    # ── Duration ─────────────────────────────────
    duration = reqs.get("duration")
    if duration:
        parts.append(f"{duration} months duration")

    # ── Preferences ──────────────────────────────
    if preferences:
        parts.extend(preferences)

    query = " ".join(parts)
    return query.strip()


def extract_hard_filters(requirements):
    """
    Extract hard filter parameters from structured requirements.

    These are used in Phase 6 (Eligibility Filtering) for
    rule-based checks that must be satisfied.

    Args:
        requirements (dict): Structured requirements from Phase 1.

    Returns:
        dict: Hard filter parameters:
            {
                "branch": str or None,
                "year": int or None,
                "experience_years": int or None,
                "locations": list[str],
                "work_modes": list[str],
                "stipend_type": str or None,    # "paid" / "unpaid"
                "stipend_minimum": int or None,
                "domains": list[str],
                "skills": list[str]
            }
    """
    student = requirements.get("student_profile", {})
    reqs = requirements.get("requirements", {})
    stipend = reqs.get("stipend", {})

    return {
        "branch": student.get("branch"),
        "year": student.get("year"),
        "experience_years": student.get("experience_years"),
        "locations": reqs.get("location", []) or [],
        "work_modes": reqs.get("work_mode", []) or [],
        "stipend_type": stipend.get("type") if stipend else None,
        "stipend_minimum": stipend.get("minimum") if stipend else None,
        "domains": reqs.get("domain", []) or [],
        "skills": student.get("skills", []) or []
    }


# ─────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    sample_requirements = {
        "student_profile": {
            "branch": "CSE",
            "year": 3,
            "degree": "B.Tech",
            "skills": ["Python", "TensorFlow"],
            "experience_years": 0
        },
        "requirements": {
            "domain": ["AI", "Machine Learning"],
            "location": ["Chennai"],
            "work_mode": ["remote"],
            "stipend": {"type": "paid", "minimum": None},
            "duration": None,
            "start_date": None
        },
        "preferences": []
    }

    query = build_search_query(sample_requirements)
    print(f"Search query: {query}")

    filters = extract_hard_filters(sample_requirements)
    print(f"\nHard filters:")
    for key, value in filters.items():
        print(f"  {key}: {value}")
