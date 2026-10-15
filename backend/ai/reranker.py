"""
Phase 7 — Reranking via Qwen

Takes filtered candidates and re-scores them using Qwen
for more precise relevance ordering based on the student's
original query context.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:1.5b")


RERANK_PROMPT = """You are an internship relevance scorer.

Given a student's search query and an internship description,
score the RELEVANCE of this internship to the student on a scale
of 0 to 100.

Scoring guidelines:
- 90-100: Perfect match — domain, skills, location, and preferences all align
- 70-89:  Strong match — most criteria align with minor gaps
- 50-69:  Moderate match — some criteria align but notable gaps exist
- 30-49:  Weak match — few criteria align
- 0-29:   Poor match — barely relevant

Return ONLY a JSON object with this exact structure:
{
  "score": <integer 0-100>,
  "reason": "<one sentence explaining the score>"
}

Do NOT output anything else. No markdown, no explanation, just the JSON.

Student Query:
{query}

Internship:
Title: {title}
Organization: {organization}
Domain: {domain}
Skills: {skills}
Location: {location}
Work Mode: {work_mode}
Stipend: ₹{stipend}/month
Duration: {duration} months
Description: {description}
"""


def rerank_candidates(candidates, search_query, max_candidates=15):
    """
    Rerank candidates using Qwen for precise relevance scoring.

    For each candidate, sends a prompt to Qwen asking it to score
    the relevance of the internship to the student's query.

    Args:
        candidates (list[dict]): Eligible internships from Phase 6.
        search_query (str): The natural-language query from Phase 2.
        max_candidates (int): Maximum number of candidates to rerank
                              (limits Ollama calls for performance).

    Returns:
        list[dict]: Candidates with added "rerank_score" and
                    "rerank_reason" fields, sorted by rerank_score desc.
    """
    # Limit candidates to avoid too many LLM calls
    to_rerank = candidates[:max_candidates]

    for candidate in to_rerank:
        try:
            score, reason = _score_candidate(candidate, search_query)
            candidate["rerank_score"] = score
            candidate["rerank_reason"] = reason
        except Exception as e:
            print(f"  ⚠ Rerank failed for '{candidate.get('title')}': {e}")
            # Fall back to similarity score scaled to 0-100
            sim_score = candidate.get("similarity_score", 0.5)
            candidate["rerank_score"] = int(sim_score * 100)
            candidate["rerank_reason"] = "Scored by semantic similarity (reranker fallback)"

    # Sort by rerank score descending
    to_rerank.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

    return to_rerank


def _score_candidate(candidate, search_query):
    """
    Ask Qwen to score a single candidate's relevance.

    Returns:
        tuple[int, str]: (score 0-100, reason string)
    """
    prompt = RERANK_PROMPT.format(
        query=search_query,
        title=candidate.get("title", "Unknown"),
        organization=candidate.get("organization", "Unknown"),
        domain=", ".join(candidate.get("domain", [])),
        skills=", ".join(candidate.get("skills", [])),
        location=candidate.get("location", "Not specified"),
        work_mode=candidate.get("work_mode", "Not specified"),
        stipend=candidate.get("stipend", 0),
        duration=candidate.get("duration_months", "Not specified"),
        description=candidate.get("description", "No description")
    )

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent scoring
                "num_predict": 150   # Short response expected
            }
        },
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"Ollama error: {response.status_code}")

    data = response.json()
    output = data.get("response", "").strip()

    if not output:
        raise Exception("Empty response from Qwen")

    result = json.loads(output)
    score = max(0, min(100, int(result.get("score", 50))))
    reason = result.get("reason", "No reason provided")

    return score, reason


# ─────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_candidate = {
        "title": "Machine Learning Intern",
        "organization": "ABC Technologies",
        "description": "Work on ML and computer vision projects.",
        "domain": ["AI", "Machine Learning"],
        "skills": ["Python", "TensorFlow"],
        "location": "Chennai",
        "work_mode": "Hybrid",
        "stipend": 25000,
        "duration_months": 3,
        "similarity_score": 0.85
    }

    test_query = "AI Machine Learning internship for CSE student in Chennai paid remote"

    print("Testing reranker...")
    results = rerank_candidates([test_candidate], test_query)

    for r in results:
        print(f"  Score: {r['rerank_score']}")
        print(f"  Reason: {r['rerank_reason']}")
