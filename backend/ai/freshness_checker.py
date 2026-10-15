"""
Phase 8 — Real-Time / Freshness Check

Evaluates each internship's freshness based on:
  1. Deadline status (expired / closing soon / open)
  2. Verification recency (fresh / recent / stale)
  3. Active status

This is the major innovation — ensures recommendations
are for real, currently available opportunities.
"""

from datetime import datetime, timedelta


def check_freshness(candidate):
    """
    Evaluate the freshness of an internship.

    Args:
        candidate (dict): An internship record with:
            - deadline (str): ISO date string
            - last_verified_at (str): ISO datetime string
            - status (str): "active" or "expired"

    Returns:
        dict: Freshness assessment:
            {
                "overall_status": "fresh" | "recent" | "stale" | "expired",
                "deadline_status": "expired" | "closing_soon" | "open",
                "days_until_deadline": int,
                "verification_status": "fresh" | "recent" | "stale",
                "hours_since_verified": float,
                "is_active": bool,
                "freshness_score": float (0.0 - 1.0),
                "freshness_label": str
            }
    """
    now = datetime.now()
    result = {}

    # ── 1. Deadline Status ───────────────────────
    deadline_str = candidate.get("deadline")
    if deadline_str:
        try:
            deadline = datetime.fromisoformat(deadline_str)
            days_until = (deadline - now).days

            if days_until < 0:
                result["deadline_status"] = "expired"
                result["days_until_deadline"] = days_until
            elif days_until <= 3:
                result["deadline_status"] = "closing_soon"
                result["days_until_deadline"] = days_until
            else:
                result["deadline_status"] = "open"
                result["days_until_deadline"] = days_until
        except (ValueError, TypeError):
            result["deadline_status"] = "unknown"
            result["days_until_deadline"] = None
    else:
        result["deadline_status"] = "unknown"
        result["days_until_deadline"] = None

    # ── 2. Verification Recency ──────────────────
    verified_str = candidate.get("last_verified_at")
    if verified_str:
        try:
            verified_at = datetime.fromisoformat(verified_str)
            hours_since = (now - verified_at).total_seconds() / 3600

            result["hours_since_verified"] = round(hours_since, 1)

            if hours_since <= 24:
                result["verification_status"] = "fresh"
            elif hours_since <= 168:  # 7 days
                result["verification_status"] = "recent"
            else:
                result["verification_status"] = "stale"
        except (ValueError, TypeError):
            result["verification_status"] = "unknown"
            result["hours_since_verified"] = None
    else:
        result["verification_status"] = "unknown"
        result["hours_since_verified"] = None

    # ── 3. Active Status ─────────────────────────
    status = (candidate.get("status") or "").lower()
    result["is_active"] = status == "active"

    # ── 4. Overall Freshness Score ───────────────
    freshness_score = _calculate_freshness_score(result)
    result["freshness_score"] = freshness_score

    # ── 5. Overall Status Label ──────────────────
    if result["deadline_status"] == "expired" or not result["is_active"]:
        result["overall_status"] = "expired"
        result["freshness_label"] = "❌ Expired"
    elif result["verification_status"] == "stale":
        result["overall_status"] = "stale"
        result["freshness_label"] = "⚠️ Not recently verified"
    elif result["deadline_status"] == "closing_soon":
        result["overall_status"] = "closing_soon"
        result["freshness_label"] = f"⏰ Closing in {result['days_until_deadline']} days"
    elif result["verification_status"] == "fresh":
        result["overall_status"] = "fresh"
        hours = result.get("hours_since_verified")
        if hours and hours < 1:
            result["freshness_label"] = "✅ Verified just now"
        elif hours:
            result["freshness_label"] = f"✅ Verified {int(hours)} hours ago"
        else:
            result["freshness_label"] = "✅ Fresh"
    else:
        result["overall_status"] = "recent"
        result["freshness_label"] = "✅ Recently verified"

    return result


def _calculate_freshness_score(freshness_result):
    """
    Calculate a numeric freshness score from 0.0 to 1.0.

    Components:
        - Deadline score (0.4 weight)
        - Verification score (0.4 weight)
        - Active status (0.2 weight)
    """
    score = 0.0

    # Deadline component (40%)
    deadline_status = freshness_result.get("deadline_status")
    days_until = freshness_result.get("days_until_deadline")

    if deadline_status == "expired":
        deadline_score = 0.0
    elif deadline_status == "closing_soon" and days_until is not None:
        deadline_score = 0.5 + (days_until / 6.0) * 0.5  # 0.5 to 1.0
    elif deadline_status == "open" and days_until is not None:
        # More days = better, cap at 30 days
        deadline_score = min(1.0, days_until / 30.0)
    else:
        deadline_score = 0.5  # Unknown

    score += deadline_score * 0.4

    # Verification component (40%)
    verification_status = freshness_result.get("verification_status")
    hours_since = freshness_result.get("hours_since_verified")

    if verification_status == "fresh":
        verification_score = 1.0
    elif verification_status == "recent":
        if hours_since:
            # Linear decay from 1.0 to 0.5 over 7 days
            verification_score = max(0.5, 1.0 - (hours_since / 336.0))
        else:
            verification_score = 0.7
    elif verification_status == "stale":
        verification_score = 0.2
    else:
        verification_score = 0.4  # Unknown

    score += verification_score * 0.4

    # Active status component (20%)
    is_active = freshness_result.get("is_active", True)
    score += (1.0 if is_active else 0.0) * 0.2

    return round(score, 3)


def filter_by_freshness(candidates):
    """
    Apply freshness checks to all candidates.

    - Removes expired internships entirely.
    - Keeps all others with freshness metadata attached.

    Args:
        candidates (list[dict]): Internships to check.

    Returns:
        list[dict]: Non-expired candidates with freshness data added.
    """
    fresh_candidates = []

    for candidate in candidates:
        freshness = check_freshness(candidate)
        candidate["freshness"] = freshness

        # Remove expired opportunities
        if freshness["overall_status"] == "expired":
            print(f"  ✗ Removed expired: {candidate.get('title')}")
            continue

        fresh_candidates.append(candidate)

    return fresh_candidates


# ─────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        {
            "title": "Fresh AI Intern",
            "deadline": "2026-09-25",
            "last_verified_at": "2026-09-01T09:00:00",
            "status": "active"
        },
        {
            "title": "Expired ML Position",
            "deadline": "2026-07-15",
            "last_verified_at": "2026-07-10T12:00:00",
            "status": "expired"
        },
        {
            "title": "Stale Opportunity",
            "deadline": "2026-10-01",
            "last_verified_at": "2026-08-10T08:00:00",
            "status": "active"
        }
    ]

    print("Freshness checks:")
    for tc in test_cases:
        result = check_freshness(tc)
        print(f"\n  {tc['title']}:")
        print(f"    Status: {result['overall_status']}")
        print(f"    Score:  {result['freshness_score']}")
        print(f"    Label:  {result['freshness_label']}")

    print("\n\nFilter test:")
    filtered = filter_by_freshness(test_cases)
    print(f"  {len(filtered)} survived out of {len(test_cases)}")
