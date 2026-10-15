"""
Database Setup & Seeding

Creates the PostgreSQL schema with pgvector and seeds
the database with internship data + embeddings.

Usage:
    python db_setup.py
"""

import os
import sys
import json
import time
from pathlib import Path

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from vector_store import get_connection, create_tables, drop_tables, store_internship, get_internship_count
from embedding_service import generate_embedding, build_internship_text


def resolve_data_path(data_path=None):
    if data_path is None:
        return os.path.join(
            os.path.dirname(__file__),
            "..", "..", "data", "internships.json"
        )

    return data_path


def load_internships_file(data_path=None):
    resolved_path = resolve_data_path(data_path)
    path = Path(resolved_path)

    if not path.exists():
        return resolved_path, []

    with path.open("r", encoding="utf-8") as file:
        internships = json.load(file)

    if not isinstance(internships, list):
        internships = [internships]

    return resolved_path, internships


def save_internships_file(data_path, internships):
    resolved_path = resolve_data_path(data_path)
    path = Path(resolved_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(internships, file, indent=2, ensure_ascii=False)

    temp_path.replace(path)


def append_internship_to_file(internship, data_path=None):
    resolved_path, internships = load_internships_file(data_path)
    internships.append(internship)
    save_internships_file(resolved_path, internships)
    return resolved_path


def delete_internship_from_file(internship_id, data_path=None):
    resolved_path, internships = load_internships_file(data_path)
    remaining = [item for item in internships if item.get("id") != internship_id]
    save_internships_file(resolved_path, remaining)
    return resolved_path


def delete_internship_from_db(conn, internship_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM internships WHERE id = %s;", (internship_id,))
    conn.commit()


def get_next_internship_id(internships):
    numeric_ids = [item.get("id") for item in internships if isinstance(item.get("id"), int)]
    return (max(numeric_ids) + 1) if numeric_ids else 1


def normalize_submission_payload(payload):
    normalized = dict(payload or {})

    def to_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [value]

    normalized["title"] = (normalized.get("title") or "").strip()
    normalized["organization"] = (normalized.get("organization") or normalized.get("company_name") or "").strip()
    normalized["description"] = (normalized.get("description") or "").strip()
    normalized["domain"] = to_list(normalized.get("domain"))
    normalized["skills"] = to_list(normalized.get("skills"))
    normalized["eligible_branches"] = to_list(normalized.get("eligible_branches"))
    normalized["eligible_years"] = [int(year) for year in to_list(normalized.get("eligible_years")) if str(year).strip().isdigit()]
    normalized["location"] = (normalized.get("location") or "").strip()
    normalized["work_mode"] = (normalized.get("work_mode") or "").strip()
    normalized["stipend"] = int(normalized.get("stipend") or 0)
    normalized["duration_months"] = int(normalized.get("duration_months") or 0) or None
    normalized["start_date"] = (normalized.get("start_date") or "").strip() or None
    normalized["deadline"] = (normalized.get("deadline") or "").strip() or None
    normalized["status"] = (normalized.get("status") or "active").strip() or "active"
    normalized["source"] = (normalized.get("source") or "organization_portal").strip()
    normalized["source_url"] = (normalized.get("source_url") or "").strip() or None
    normalized["experience_required"] = int(normalized.get("experience_required") or 0)
    normalized["last_verified_at"] = normalized.get("last_verified_at") or None

    return normalized


def save_organization_submission(submission, data_path=None):
    """Persist a new internship submission locally in internships.json only."""
    resolved_path, internships = load_internships_file(data_path)
    internship = normalize_submission_payload(submission)

    required_fields = ["title", "organization", "description", "location", "work_mode"]
    missing_fields = [field for field in required_fields if not internship.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    embedding_text = build_internship_text(internship)
    embedding = generate_embedding(embedding_text)

    internship_record = dict(internship)
    internship_record["id"] = get_next_internship_id(internships)
    internship_record["embedding"] = embedding
    internships.append(internship_record)
    save_internships_file(resolved_path, internships)

    return {
        "status": "saved",
        "id": internship_record["id"],
        "embedding_dimension": len(embedding),
        "data_path": resolved_path,
        "storage": "local_json"
    }


def seed_database(data_path=None, force_reseed=False):
    """
    Seed the database with internship data from JSON file.

    1. Connects to PostgreSQL
    2. Creates tables (if not exist)
    3. Loads internship data from JSON
    4. Generates embeddings for each internship
    5. Stores internship + embedding in pgvector

    Args:
        data_path (str): Path to internship JSON file.
                         Defaults to ../../data/internships_seed.json
        force_reseed (bool): If True, drops and recreates tables.

    Returns:
        dict: Seeding statistics.
    """
    if data_path is None:
        data_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "data", "internships_seed.json"
        )

    print("\n" + "=" * 50)
    print("  DATABASE SETUP & SEEDING")
    print("=" * 50)

    # ── 1. Connect ───────────────────────────────
    print("\n[Phase 1] Connecting to PostgreSQL...")
    conn = get_connection()
    print("  ✓ Connected")

    # ── 2. Create tables ─────────────────────────
    if force_reseed:
        print("\n[Phase 2] Dropping existing tables...")
        drop_tables(conn)

    print("\n[Phase 2] Creating tables...")
    create_tables(conn)

    # ── 3. Check if already seeded ───────────────
    current_count = get_internship_count(conn)
    if current_count > 0 and not force_reseed:
        print(f"\n  ℹ Database already has {current_count} internships.")
        print("  Use force_reseed=True to reseed.")
        conn.close()
        return {
            "status": "already_seeded",
            "existing_count": current_count
        }

    # ── 4. Load data ─────────────────────────────
    print(f"\n[Phase 3] Loading data from {data_path}...")
    with open(data_path, "r", encoding="utf-8") as f:
        internships = json.load(f)

    if not isinstance(internships, list):
        internships = [internships]

    print(f"  Loaded {len(internships)} internships")

    # ── 5. Generate embeddings and store ─────────
    print("\n[Phase 4] Generating embeddings and storing...")
    success_count = 0
    error_count = 0
    start_time = time.time()

    for i, internship in enumerate(internships, 1):
        try:
            # Build text for embedding
            text = build_internship_text(internship)
            print(f"\n  [{i}/{len(internships)}] {internship.get('title', 'Unknown')}")
            print(f"    Text: {text[:80]}...")

            # Generate embedding
            embedding = generate_embedding(text)
            print(f"    Embedding: {len(embedding)}D vector")

            # Store in database
            store_internship(conn, internship, embedding)
            print("    [OK] Stored successfully")

            success_count += 1

        except Exception as e:
            print(f"    [ERROR] {e}")
            error_count += 1

    elapsed = time.time() - start_time

    # ── Summary ──────────────────────────────────
    print("\n" + "=" * 50)
    print("  SEEDING COMPLETE")
    print(f"  Stored:  {success_count}")
    print(f"  Errors:  {error_count}")
    print(f"  Time:    {elapsed:.1f}s")
    print("=" * 50)

    conn.close()

    return {
        "status": "seeded",
        "stored": success_count,
        "errors": error_count,
        "time_seconds": round(elapsed, 1)
    }


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed the internship database")
    parser.add_argument(
        "--force", action="store_true",
        help="Force reseed (drops existing data)"
    )
    parser.add_argument(
        "--data", type=str, default=None,
        help="Path to internship JSON file"
    )

    args = parser.parse_args()

    result = seed_database(data_path=args.data, force_reseed=args.force)
    print(f"\nResult: {json.dumps(result, indent=2)}")
