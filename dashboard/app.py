"""
Guardian AI  —  Dashboard (Flask)
==================================
A lightweight web UI for browsing incident reports stored in /artifacts.

Routes:
    GET /           → serves the single-page dashboard
    GET /api/incidents  → returns all incident JSONs as a list
"""

import json
import logging
from pathlib import Path

from flask import Flask, jsonify, render_template

log = logging.getLogger("guardian.dashboard")

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"

app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    """Serve the single-page dashboard UI."""
    return render_template("index.html")


@app.route("/api/incidents")
def api_incidents():
    """Return all incident JSON files from /artifacts as a JSON array."""
    incidents = []

    if not ARTIFACTS_DIR.exists():
        return jsonify(incidents)

    for path in sorted(ARTIFACTS_DIR.glob("*_incident_*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_filename"] = path.name
            incidents.append(data)
        except Exception:
            continue

    return jsonify(incidents)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
