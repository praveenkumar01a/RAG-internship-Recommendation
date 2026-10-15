"""
Phase 6 — Hard Filtering / Eligibility

Applies rule-based eligibility checks that must be satisfied.
Semantic similarity alone does not guarantee eligibility —
this phase ensures hard constraints are met.
"""


def filter_eligible(candidates, hard_filters):
    """
    Filter candidates based on hard eligibility requirements.

    Checks:
        1. Branch eligibility
        2. Year eligibility
        3. Experience requirement
        4. Location / work mode match
        5. Stipend requirement

    Args:
        candidates (list[dict]): Internships from similarity search.
        hard_filters (dict): From query_builder.extract_hard_filters().
            {
                "branch", "year", "experience_years",
                "locations", "work_modes",
                "stipend_type", "stipend_minimum",
                "domains", "skills"
            }

    Returns:
        list[dict]: Eligible candidates, each with an added
                    "eligibility_details" field explaining pass/fail.
    """
    eligible = []

    for candidate in candidates:
        details = {}
        is_eligible = True

        # ── 1. Branch Eligibility ────────────────
        branch = hard_filters.get("branch")
        eligible_branches = candidate.get("eligible_branches", [])

        if branch and eligible_branches:
            branch_match = _fuzzy_branch_match(branch, eligible_branches)
            details["branch"] = {
                "passed": branch_match,
                "student_branch": branch,
                "accepted_branches": eligible_branches
            }
            if not branch_match:
                is_eligible = False
        else:
            details["branch"] = {"passed": True, "reason": "Not specified"}

        # ── 2. Year Eligibility ──────────────────
        year = hard_filters.get("year")
        eligible_years = candidate.get("eligible_years", [])

        if year and eligible_years:
            year_match = year in eligible_years
            details["year"] = {
                "passed": year_match,
                "student_year": year,
                "accepted_years": eligible_years
            }
            if not year_match:
                is_eligible = False
        else:
            details["year"] = {"passed": True, "reason": "Not specified"}

        # ── 3. Experience Requirement ────────────
        student_exp = hard_filters.get("experience_years") or 0
        required_exp = candidate.get("experience_required", 0)

        exp_match = student_exp >= required_exp
        details["experience"] = {
            "passed": exp_match,
            "student_experience": student_exp,
            "required_experience": required_exp
        }
        if not exp_match:
            is_eligible = False

        # ── 4. Location / Work Mode ──────────────
        student_locations = [
            loc.lower() for loc in hard_filters.get("locations", [])
        ]
        student_work_modes = [
            wm.lower() for wm in hard_filters.get("work_modes", [])
        ]

        internship_location = (candidate.get("location") or "").lower()
        internship_work_mode = (candidate.get("work_mode") or "").lower()

        # Location check: pass if student didn't specify,
        # or if internship location matches, or if remote is accepted
        location_match = True
        if student_locations:
            location_match = (
                any(loc in internship_location for loc in student_locations) or
                internship_work_mode == "remote" or
                "remote" in student_work_modes
            )

        # Work mode check: pass if student didn't specify,
        # or if work modes match
        work_mode_match = True
        if student_work_modes:
            work_mode_match = (
                internship_work_mode in student_work_modes or
                # "hybrid" matches both "remote" and "on-site" partially
                internship_work_mode == "hybrid"
            )

        details["location_work_mode"] = {
            "passed": location_match and work_mode_match,
            "location_match": location_match,
            "work_mode_match": work_mode_match,
            "internship_location": candidate.get("location"),
            "internship_work_mode": candidate.get("work_mode")
        }
        # Location/work mode is a soft filter — don't hard-fail
        # but flag it for scoring

        # ── 5. Stipend Requirement ───────────────
        stipend_type = hard_filters.get("stipend_type")
        stipend_minimum = hard_filters.get("stipend_minimum")
        internship_stipend = candidate.get("stipend", 0)

        stipend_match = True
        if stipend_type == "paid" and internship_stipend == 0:
            stipend_match = False
        if stipend_minimum and internship_stipend < stipend_minimum:
            stipend_match = False

        details["stipend"] = {
            "passed": stipend_match,
            "student_requirement": stipend_type,
            "student_minimum": stipend_minimum,
            "internship_stipend": internship_stipend
        }
        if not stipend_match:
            is_eligible = False

        # ── Final decision ───────────────────────
        candidate["eligibility_passed"] = is_eligible
        candidate["eligibility_details"] = details

        if is_eligible:
            eligible.append(candidate)

    return eligible


def _fuzzy_branch_match(student_branch, eligible_branches):
    """
    Check if the student's branch matches any eligible branch.

    Handles common aliases:
        - "CSE" matches "Computer Science", "CS", "CSE"
        - "AI & DS" matches "AI", "Data Science"
        - "IT" matches "Information Technology"
    """
    branch_aliases = {
        "cse": ["cse", "cs", "computer science",
                "computer science and engineering"],
        "it": ["it", "information technology"],
        "ece": ["ece", "electronics", "electronics and communication"],
        "eee": ["eee", "electrical", "electrical and electronics"],
        "ai": ["ai", "artificial intelligence", "ai & ds",
               "ai and data science"],
        "data science": ["data science", "ds", "ai & ds",
                         "ai and data science"],
        "mechanical": ["mechanical", "mech", "me"],
        "civil": ["civil", "ce"],
        "biomedical": ["biomedical", "bme"],
        "mathematics": ["mathematics", "maths", "math"],
    }

    student_lower = student_branch.lower().strip()

    # Find all aliases for the student's branch
    student_aliases = set()
    student_aliases.add(student_lower)
    for key, aliases in branch_aliases.items():
        if student_lower in aliases or student_lower == key:
            student_aliases.update(aliases)
            student_aliases.add(key)

    # Check if any eligible branch matches
    for eligible in eligible_branches:
        eligible_lower = eligible.lower().strip()
        if eligible_lower in student_aliases:
            return True

        # Also check if the eligible branch has aliases that match
        for key, aliases in branch_aliases.items():
            if eligible_lower in aliases or eligible_lower == key:
                if student_aliases & set(aliases):
                    return True

    return False


# ─────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Test fuzzy branch matching
    assert _fuzzy_branch_match("CSE", ["Computer Science", "IT"]) is True
    assert _fuzzy_branch_match("AI & DS", ["AI", "Data Science"]) is True
    assert _fuzzy_branch_match("CSE", ["ECE", "EEE"]) is False
    assert _fuzzy_branch_match("Mechanical", ["Mech", "Civil"]) is True

    print("✓ All branch matching tests passed.")

    # Test filtering
    test_candidates = [
        {
            "title": "ML Intern",
            "eligible_branches": ["CSE", "AI"],
            "eligible_years": [3, 4],
            "experience_required": 0,
            "location": "Chennai",
            "work_mode": "Hybrid",
            "stipend": 25000
        },
        {
            "title": "Mech Intern",
            "eligible_branches": ["Mechanical"],
            "eligible_years": [3, 4],
            "experience_required": 0,
            "location": "Chennai",
            "work_mode": "On-site",
            "stipend": 15000
        }
    ]

    test_filters = {
        "branch": "CSE",
        "year": 3,
        "experience_years": 0,
        "locations": ["Chennai"],
        "work_modes": ["remote"],
        "stipend_type": "paid",
        "stipend_minimum": None,
        "domains": ["AI"],
        "skills": ["Python"]
    }

    result = filter_eligible(test_candidates, test_filters)
    print(f"\n{len(result)} eligible out of {len(test_candidates)} candidates")
    for r in result:
        print(f"  ✓ {r['title']}")
