"""
Phase 4 & 5 — Vector Database & Similarity Search

Manages PostgreSQL + pgvector for storing internship embeddings
and performing cosine similarity searches.
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ─────────────────────────────────────────────
# Database connection
# ─────────────────────────────────────────────

def get_connection():
    """Create and return a PostgreSQL connection with pgvector registered."""
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", "postgres"),
        dbname=os.getenv("PG_DATABASE", "internship_agent")
    )
    register_vector(conn)
    return conn


# ─────────────────────────────────────────────
# Schema management
# ─────────────────────────────────────────────

def create_tables(conn):
    """
    Create the internships table with a pgvector embedding column.
    Uses 768 dimensions (nomic-embed-text output size).
    """
    with conn.cursor() as cur:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS internships (
                id              SERIAL PRIMARY KEY,
                title           TEXT NOT NULL,
                organization    TEXT,
                description     TEXT,
                domain          TEXT[],
                skills          TEXT[],
                eligible_branches TEXT[],
                eligible_years  INTEGER[],
                experience_required INTEGER DEFAULT 0,
                location        TEXT,
                work_mode       TEXT,
                stipend         INTEGER DEFAULT 0,
                duration_months INTEGER,
                start_date      TEXT,
                deadline        TEXT,
                status          TEXT DEFAULT 'active',
                source          TEXT,
                source_url      TEXT,
                last_verified_at TEXT,
                embedding       vector(768)
            );
        """)

        # Create an index for fast cosine similarity search
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_internship_embedding
            ON internships
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 5);
        """)

    conn.commit()
    print("✓ Tables and indexes created successfully.")


def drop_tables(conn):
    """Drop the internships table (for re-seeding)."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS internships CASCADE;")
    conn.commit()
    print("✓ Tables dropped.")


# ─────────────────────────────────────────────
# Data operations
# ─────────────────────────────────────────────

def store_internship(conn, internship, embedding):
    """
    Insert a single internship record with its embedding vector.

    Args:
        conn: PostgreSQL connection.
        internship (dict): Internship data.
        embedding (list[float]): 768-dimensional vector.
    """
    import numpy as np

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO internships (
                title, organization, description,
                domain, skills, eligible_branches, eligible_years,
                experience_required, location, work_mode,
                stipend, duration_months, start_date, deadline,
                status, source, source_url, last_verified_at,
                embedding
            ) VALUES (
                %(title)s, %(organization)s, %(description)s,
                %(domain)s, %(skills)s, %(eligible_branches)s, %(eligible_years)s,
                %(experience_required)s, %(location)s, %(work_mode)s,
                %(stipend)s, %(duration_months)s, %(start_date)s, %(deadline)s,
                %(status)s, %(source)s, %(source_url)s, %(last_verified_at)s,
                %(embedding)s
            )
            RETURNING id
        """, {
            "title": internship.get("title"),
            "organization": internship.get("organization"),
            "description": internship.get("description"),
            "domain": internship.get("domain", []),
            "skills": internship.get("skills", []),
            "eligible_branches": internship.get("eligible_branches", []),
            "eligible_years": internship.get("eligible_years", []),
            "experience_required": internship.get("experience_required", 0),
            "location": internship.get("location"),
            "work_mode": internship.get("work_mode"),
            "stipend": internship.get("stipend", 0),
            "duration_months": internship.get("duration_months"),
            "start_date": internship.get("start_date"),
            "deadline": internship.get("deadline"),
            "status": internship.get("status", "active"),
            "source": internship.get("source"),
            "source_url": internship.get("source_url"),
            "last_verified_at": internship.get("last_verified_at"),
            "embedding": np.array(embedding)
        })
        inserted_id = cur.fetchone()[0]

    conn.commit()
    return inserted_id


def similarity_search(conn, query_vector, top_n=20):
    """
    Phase 5 — Perform cosine similarity search against stored internships.

    Uses pgvector's <=> operator for cosine distance.
    Lower distance = higher similarity.

    Args:
        conn: PostgreSQL connection.
        query_vector (list[float]): The student's query embedding.
        top_n (int): Number of top results to return.

    Returns:
        list[dict]: Top N internships with similarity scores.
    """
    import numpy as np

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                id, title, organization, description,
                domain, skills, eligible_branches, eligible_years,
                experience_required, location, work_mode,
                stipend, duration_months, start_date, deadline,
                status, source, source_url, last_verified_at,
                1 - (embedding <=> %s::vector) AS similarity_score
            FROM internships
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """, (
            np.array(query_vector).tolist(),
            np.array(query_vector).tolist(),
            top_n
        ))

        results = cur.fetchall()

    # Convert to regular dicts and ensure similarity is float
    output = []
    for row in results:
        record = dict(row)
        record["similarity_score"] = float(record["similarity_score"])
        output.append(record)

    return output


def local_similarity_search(query_vector, top_n=20):
    """
    Fallback cosine similarity search using local internships.json
    when PostgreSQL/Supabase is unreachable or offline.
    """
    import numpy as np

    data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "internships.json")
    if not os.path.exists(data_path):
        return []

    with open(data_path, "r", encoding="utf-8") as f:
        internships = json.load(f)

    q_vec = np.array(query_vector, dtype=float)
    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0:
        return []

    scored = []
    for item in internships:
        if "embedding" in item and len(item["embedding"]) == 768:
            doc_vec = np.array(item["embedding"], dtype=float)
            doc_norm = np.linalg.norm(doc_vec)
            if doc_norm > 0:
                sim = float(np.dot(q_vec, doc_vec) / (q_norm * doc_norm))
                record = dict(item)
                record["similarity_score"] = sim
                scored.append(record)

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:top_n]


def get_all_internships(conn):
    """Retrieve all internships from the database."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                id, title, organization, description,
                domain, skills, eligible_branches, eligible_years,
                experience_required, location, work_mode,
                stipend, duration_months, start_date, deadline,
                status, source, source_url, last_verified_at
            FROM internships
            ORDER BY id;
        """)
        return [dict(row) for row in cur.fetchall()]


def get_internship_count(conn):
    """Return the total number of internships in the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM internships;")
        return cur.fetchone()[0]


# ─────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    conn = get_connection()
    count = get_internship_count(conn)
    print(f"Internships in database: {count}")
    conn.close()
