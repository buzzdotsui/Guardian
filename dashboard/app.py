"""
Guardian AI  —  Dashboard (Flask)
==================================
Web UI for browsing incident reports with authentication and analytics.

Routes:
    GET  /login        → login page
    POST /login        → authenticate
    GET  /logout       → log out
    GET  /             → dashboard (auth required)
    GET  /api/incidents    → all incident JSONs (auth required)
    GET  /api/analytics    → aggregated analytics data (auth required)
"""

import os
import json
import logging
import functools
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("guardian.dashboard")

from app.database import SessionLocal
from app.models import Incident
app = Flask(__name__, template_folder="templates", static_folder="ui", static_url_path="/")
app.secret_key = os.getenv("DASHBOARD_SECRET_KEY", "guardian-ai-secret-key-change-me")

# Auth credentials from env
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "guardian")


# ── Auth decorator ───────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ── Auth routes ──────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == DASHBOARD_USER and password == DASHBOARD_PASS:
            session["authenticated"] = True
            session.permanent = True
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/policy")
def policy():
    """Publicly accessible internal AI Policy page."""
    return render_template("policy.html")


# ── Helpers ──────────────────────────────────────────────
def _load_all_incidents() -> list[dict]:
    """Load all incident records from the database."""
    db = SessionLocal()
    try:
        incidents = db.query(Incident).order_by(Incident.timestamp.desc()).all()
        return [inc.to_dict() for inc in incidents]
    except Exception as e:
        log.error("Failed to fetch incidents from DB: %s", e)
        return []
    finally:
        db.close()


# ── Dashboard ────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return app.send_static_file("index.html")


@app.route("/api/incidents")
@login_required
def api_incidents():
    return jsonify(_load_all_incidents())


@app.route("/api/analytics")
@login_required
def api_analytics():
    """Aggregated analytics for charts."""
    incidents = _load_all_incidents()

    # Severity distribution
    sev_dist = {"low": 0, "medium": 0, "high": 0}
    for inc in incidents:
        s = inc.get("severity", 0)
        if s >= 7:
            sev_dist["high"] += 1
        elif s >= 4:
            sev_dist["medium"] += 1
        else:
            sev_dist["low"] += 1

    # Top users (top 8)
    user_counts = Counter(inc.get("user", "unknown") for inc in incidents)
    top_users = [{"user": u, "count": c} for u, c in user_counts.most_common(8)]

    # Incidents over time (last 14 days, bucketed by day)
    today = datetime.now(timezone.utc).date()
    day_counts = {}
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        day_counts[d.isoformat()] = 0

    for inc in incidents:
        try:
            ts = datetime.fromisoformat(inc.get("timestamp", "")).date().isoformat()
            if ts in day_counts:
                day_counts[ts] += 1
        except Exception:
            continue

    timeline = [{"date": d, "count": c} for d, c in day_counts.items()]

    # Feedback breakdown
    feedback = {"dismissed": 0, "escalated": 0, "pending": 0}
    for inc in incidents:
        fb = inc.get("user_feedback")
        if fb == "dismissed":
            feedback["dismissed"] += 1
        elif fb == "escalated":
            feedback["escalated"] += 1
        else:
            feedback["pending"] += 1

    # Detection source
    sources = {"regex": 0, "ai": 0, "self_report": 0}
    for inc in incidents:
        if inc.get("type") == "self_report":
            sources["self_report"] += 1
        elif inc.get("detected_by") == "regex":
            sources["regex"] += 1
        else:
            sources["ai"] += 1

    return jsonify({
        "total": len(incidents),
        "severity_distribution": sev_dist,
        "top_users": top_users,
        "timeline": timeline,
        "feedback": feedback,
        "sources": sources,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
