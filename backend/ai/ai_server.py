"""
Flask AI Microservice — Port 5001

Provides HTTP endpoints for the AI pipeline.
Called by the Node.js backend (port 5000).

Endpoints:
    POST /api/search    — Run full recommendation pipeline
    POST /api/embed     — Generate embedding for text (utility)
    POST /api/seed      — Seed the database with internship data
    GET  /api/health    — Health check
"""

import os
import sys
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from pipeline import run_pipeline
from embedding_service import generate_embedding
from db_setup import save_organization_submission

DEMO_ORG_EMAIL = "orgdemo@internai.com"
DEMO_ORG_PASSWORD = "Demo@1234"
DEMO_ORG_TOKEN = "demo-org-token"
DEMO_ORG_NAME = "Demo Organization"

app = Flask(__name__)
CORS(app)


def validate_org_token(request_obj):
    auth_header = request_obj.headers.get("Authorization", "")
    token_header = request_obj.headers.get("X-Org-Token", "")

    if auth_header.startswith("Bearer "):
        auth_header = auth_header.replace("Bearer ", "", 1).strip()

    token = auth_header or token_header
    return token == DEMO_ORG_TOKEN


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Check if the AI service is running."""
    return jsonify({
        "status": "healthy",
        "service": "AI Internship Pipeline",
        "version": "1.0.0"
    })


# ─────────────────────────────────────────────
# POST /api/search — Main Pipeline
# ─────────────────────────────────────────────

@app.route("/api/search", methods=["POST"])
def search():
    """
    Run the full recommendation pipeline.

    Request body:
        {
            "requirements": {
                "student_profile": {...},
                "requirements": {...},
                "preferences": [...]
            },
            "top_n": 20,       // optional
            "max_results": 10  // optional
        }

    Returns:
        {
            "success": true,
            "results": [...],
            "search_query": "...",
            "pipeline_stats": {...}
        }
    """
    try:
        data = request.get_json()

        if not data or "requirements" not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'requirements' in request body"
            }), 400

        requirements = data["requirements"]
        top_n = data.get("top_n", 20)
        max_results = data.get("max_results", 10)

        result = run_pipeline(requirements, top_n, max_results)

        return jsonify(result)

    except Exception as e:
        print(f"Search error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ─────────────────────────────────────────────
# POST /api/organization/login — Demo Login
# ─────────────────────────────────────────────

@app.route("/api/organization/login", methods=["POST"])
def organization_login():
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if email == DEMO_ORG_EMAIL and password == DEMO_ORG_PASSWORD:
            return jsonify({
                "success": True,
                "token": DEMO_ORG_TOKEN,
                "organization": {
                    "name": DEMO_ORG_NAME,
                    "email": DEMO_ORG_EMAIL
                }
            })

        return jsonify({
            "success": False,
            "error": "Invalid demo organization credentials"
        }), 401

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ─────────────────────────────────────────────
# POST /api/organization/internships — Insert internship
# ─────────────────────────────────────────────

@app.route("/api/organization/internships", methods=["POST"])
def organization_internships():
    try:
        if not validate_org_token(request):
            return jsonify({
                "success": False,
                "error": "Unauthorized organization request"
            }), 401

        data = request.get_json() or {}
        submission = data.get("internship") or data

        result = save_organization_submission(submission)

        return jsonify({
            "success": True,
            "message": "Internship saved locally in internships.json",
            "submission": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ─────────────────────────────────────────────
# POST /api/embed — Embedding Utility
# ─────────────────────────────────────────────

@app.route("/api/embed", methods=["POST"])
def embed():
    """
    Generate an embedding for a text string.

    Request body:
        { "text": "some text to embed" }

    Returns:
        { "embedding": [...], "dimension": 768 }
    """
    try:
        data = request.get_json()
        text = data.get("text", "")

        if not text:
            return jsonify({"error": "Missing 'text'"}), 400

        embedding = generate_embedding(text)

        return jsonify({
            "embedding": embedding,
            "dimension": len(embedding)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# POST /api/seed — Database Seeding
# ─────────────────────────────────────────────

@app.route("/api/seed", methods=["POST"])
def seed():
    """
    Seed the database with internship data.
    Triggers db_setup.py's seeding process.
    """
    try:
        from db_setup import seed_database
        stats = seed_database()

        return jsonify({
            "success": True,
            "message": "Database seeded successfully",
            "stats": stats
        })

    except Exception as e:
        print(f"Seed error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ─────────────────────────────────────────────
# Start Server
# ─────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("AI_SERVICE_PORT", 5001))

    print("=" * 50)
    print(f"  AI Internship Pipeline Service")
    print(f"  Running on http://localhost:{port}")
    print("=" * 50)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
