"""
Phase 3 — Embedding Generation

Uses Ollama's nomic-embed-text model to generate 768-dimensional
vectors for search queries and internship descriptions.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment from the same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


def generate_embedding(text):
    """
    Generate a vector embedding for the given text using Ollama.

    Args:
        text (str): The text to embed.

    Returns:
        list[float]: A 768-dimensional embedding vector.
    """
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        },
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(
            f"Ollama embedding error: {response.status_code} — {response.text}"
        )

    data = response.json()
    return data["embedding"]


def build_internship_text(internship):
    """
    Build a combined text representation of an internship
    suitable for embedding generation.

    Combines title, description, domains, skills, location,
    work mode, and other key fields into a single string.

    Args:
        internship (dict): An internship record.

    Returns:
        str: Combined text for embedding.
    """
    parts = []

    if internship.get("title"):
        parts.append(internship["title"])

    if internship.get("organization"):
        parts.append(f"at {internship['organization']}")

    if internship.get("description"):
        parts.append(internship["description"])

    if internship.get("domain"):
        parts.append("Domain: " + ", ".join(internship["domain"]))

    if internship.get("skills"):
        parts.append("Skills: " + ", ".join(internship["skills"]))

    if internship.get("eligible_branches"):
        parts.append(
            "Eligible branches: " + ", ".join(internship["eligible_branches"])
        )

    if internship.get("location"):
        parts.append(f"Location: {internship['location']}")

    if internship.get("work_mode"):
        parts.append(f"Work mode: {internship['work_mode']}")

    if internship.get("stipend") is not None:
        if internship["stipend"] > 0:
            parts.append(f"Stipend: ₹{internship['stipend']}/month (paid)")
        else:
            parts.append("Stipend: Unpaid")

    if internship.get("duration_months"):
        parts.append(f"Duration: {internship['duration_months']} months")

    return ". ".join(parts)


# ─────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_text = "AI Machine Learning internship CSE Chennai paid remote"
    print(f"Generating embedding for: {test_text}")

    embedding = generate_embedding(test_text)

    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
