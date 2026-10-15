"""
Master Pipeline Orchestrator

Orchestrates Phases 2–10 in sequence:
    Phase 2: Build search query from extracted requirements
    Phase 3: Generate query embedding via Ollama
    Phase 5: Similarity search in pgvector → Top 20
    Phase 6: Hard eligibility filtering
    Phase 7: Rerank with Qwen
    Phase 8: Freshness check
    Phase 9: Final multi-factor ranking
    Phase 10: Generate explanations
"""

import time
from query_builder import build_search_query, extract_hard_filters
from embedding_service import generate_embedding
from vector_store import get_connection, similarity_search, local_similarity_search
from eligibility_filter import filter_eligible
from reranker import rerank_candidates
from freshness_checker import filter_by_freshness
from final_ranker import compute_final_ranking
from explainer import generate_explanations


def run_pipeline(requirements, top_n=20, max_results=10):
    """
    Run the full internship recommendation pipeline.

    Args:
        requirements (dict): Structured requirements from Phase 1 (Qwen).
            Expected structure:
            {
                "student_profile": {...},
                "requirements": {...},
                "preferences": [...]
            }
        top_n (int): Number of candidates from similarity search.
        max_results (int): Maximum final results to return.

    Returns:
        dict: Pipeline results:
            {
                "success": bool,
                "results": list[dict],  # Ranked internships with explanations
                "search_query": str,
                "pipeline_stats": {
                    "total_in_db": int,
                    "semantic_matches": int,
                    "after_eligibility": int,
                    "after_freshness": int,
                    "final_count": int,
                    "execution_time_ms": float
                }
            }
    """
    start_time = time.time()
    stats = {}

    print("\n" + "=" * 60)
    print("  PIPELINE EXECUTION")
    print("=" * 60)

    try:
        # ── Phase 2: Build Search Query ──────────
        print("\n[Phase 2] Building search query...")
        search_query = build_search_query(requirements)
        hard_filters = extract_hard_filters(requirements)
        print(f"  Query: {search_query}")
        print(f"  Filters: {hard_filters}")

        # ── Phase 3: Generate Query Embedding ────
        print("\n[Phase 3] Generating query embedding...")
        query_embedding = generate_embedding(search_query)
        print(f"  Embedding dimension: {len(query_embedding)}")

        # ── Phase 5: Similarity Search ───────────
        print(f"\n[Phase 5] Similarity search (top {top_n})...")
        candidates = []
        conn = None
        try:
            conn = get_connection()
            candidates = similarity_search(conn, query_embedding, top_n)
        except Exception as db_err:
            print(f"  [WARN] Database connection failed ({db_err}). Falling back to local vector search...")
            candidates = local_similarity_search(query_embedding, top_n)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        stats["semantic_matches"] = len(candidates)
        print(f"  Found {len(candidates)} semantic matches")

        if not candidates:
            return _empty_result(search_query, stats, start_time)

        # Print top 5 similarity scores
        for c in candidates[:5]:
            print(f"    {c['title']}: {c['similarity_score']:.3f}")

        # ── Phase 6: Eligibility Filtering ───────
        print("\n▶ Phase 6: Applying hard eligibility filters...")
        eligible = filter_eligible(candidates, hard_filters)
        stats["after_eligibility"] = len(eligible)
        print(f"  {len(eligible)} candidates passed eligibility")

        if not eligible:
            print("  [WARN] No eligible candidates. Relaxing filters...")
            # Fall back to semantic matches with eligibility details
            eligible = candidates
            for c in eligible:
                c["eligibility_passed"] = False
                c["eligibility_details"] = {"relaxed": True}
            stats["after_eligibility"] = len(eligible)

        # ── Phase 7: Reranking ───────────────────
        print("\n[Phase 7] Reranking with Qwen...")
        reranked = rerank_candidates(eligible, search_query,
                                     max_candidates=min(len(eligible), 15))
        print(f"  Reranked {len(reranked)} candidates")
        for c in reranked[:5]:
            print(f"    {c['title']}: score={c.get('rerank_score', 'N/A')}")

        # ── Phase 8: Freshness Check ─────────────
        print("\n[Phase 8] Freshness check...")
        fresh = filter_by_freshness(reranked)
        stats["after_freshness"] = len(fresh)
        print(f"  {len(fresh)} candidates are fresh/active")

        if not fresh:
            return _empty_result(search_query, stats, start_time)

        # ── Phase 9: Final Ranking ───────────────
        print("\n[Phase 9] Computing final ranking...")
        ranked = compute_final_ranking(fresh, hard_filters)

        # Limit to max_results
        ranked = ranked[:max_results]
        stats["final_count"] = len(ranked)

        print(f"  Final top {len(ranked)} results:")
        for c in ranked:
            print(f"    {c['title']}: {c['match_percentage']}%")

        # ── Phase 10: Generate Explanations ──────
        print("\n[Phase 10] Generating explanations...")
        explained = generate_explanations(ranked, hard_filters)

        # ── Build response ───────────────────────
        elapsed_ms = (time.time() - start_time) * 1000

        # Clean up internal fields before returning
        results = []
        for c in explained:
            result = {
                "id": c.get("id"),
                "title": c.get("title"),
                "organization": c.get("organization"),
                "description": c.get("description"),
                "domain": c.get("domain"),
                "skills": c.get("skills"),
                "eligible_branches": c.get("eligible_branches"),
                "eligible_years": c.get("eligible_years"),
                "location": c.get("location"),
                "work_mode": c.get("work_mode"),
                "stipend": c.get("stipend"),
                "duration_months": c.get("duration_months"),
                "start_date": c.get("start_date"),
                "deadline": c.get("deadline"),
                "source": c.get("source"),
                "source_url": c.get("source_url"),
                "match_percentage": c.get("match_percentage"),
                "explanation": c.get("explanation"),
                "freshness": {
                    "status": c.get("freshness", {}).get("overall_status"),
                    "label": c.get("freshness", {}).get("freshness_label"),
                    "deadline_status": c.get("freshness", {}).get("deadline_status"),
                    "days_until_deadline": c.get("freshness", {}).get("days_until_deadline")
                }
            }
            results.append(result)

        print(f"\n[OK] Pipeline complete in {elapsed_ms:.0f}ms")
        print("=" * 60)

        return {
            "success": True,
            "results": results,
            "search_query": search_query,
            "pipeline_stats": {
                **stats,
                "execution_time_ms": round(elapsed_ms, 1)
            }
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"\n[ERROR] Pipeline error: {e}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e),
            "search_query": locals().get("search_query", ""),
            "results": [],
            "pipeline_stats": {
                **stats,
                "execution_time_ms": round(elapsed_ms, 1)
            }
        }


def _empty_result(search_query, stats, start_time):
    """Helper to return an empty result set."""
    elapsed_ms = (time.time() - start_time) * 1000
    return {
        "success": True,
        "results": [],
        "search_query": search_query,
        "message": "No matching internships found.",
        "pipeline_stats": {
            **stats,
            "final_count": 0,
            "execution_time_ms": round(elapsed_ms, 1)
        }
    }


# ─────────────────────────────────────────────
# CLI self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Simulated Phase 1 output
    test_requirements = {
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
        "preferences": [],
        "clarification": {"required": False, "question": None}
    }

    result = run_pipeline(test_requirements)

    if result["success"]:
        print(f"\n✓ Found {len(result['results'])} results")
        for r in result["results"]:
            print(f"  {r['match_percentage']}% — {r['title']} at {r['organization']}")
    else:
        print(f"\n✗ Error: {result.get('error')}")
