# Guardian AI — Full Feature Expansion

Build all 7 remaining features on top of the existing enforcement engine.

---

## Proposed Changes

### Component 1 — Severity Scoring (engine layer)

Adds a numeric 1–10 risk score to every incident, computed from two signals:
- Groq confidence keywords (e.g. "credential", "exfiltrat", "paste", "upload") → base score
- GitHub confirmation bonus (+3 if confirmed)

Score is embedded in the audit JSON and passed to all downstream consumers (Slack warning, email, dashboard).

#### [MODIFY] [engine.py](file:///c:/Users/USER/Guardian%20Ai/app/engine.py)
- Add `compute_severity_score(ai_reasoning, github_confirmed) -> int` function
- Embed `severity` field in `save_audit_report` output
- Add score to Slack warning block (colour-coded emoji 🟡🟠🔴)

---

### Component 2 — Channel Allowlist

Prevents Guardian from analysing messages outside approved channels.

#### [MODIFY] [engine.py](file:///c:/Users/USER/Guardian%20Ai/app/engine.py)
- Read `GUARDIAN_CHANNELS` env var (comma-separated channel IDs, e.g. `C123,C456`)
- If set, gate-check drops messages from any channel not in the list
- If unset, monitor all channels (current behaviour preserved)

#### [MODIFY] [.env](file:///c:/Users/USER/Guardian%20Ai/.env)
- Add `GUARDIAN_CHANNELS=` placeholder (empty = watch all)

---

### Component 3 — Slack `/report` Self-Report Command

Lets any user proactively flag a potential violation. Guardian logs it and notifies the security channel.

#### [MODIFY] [engine.py](file:///c:/Users/USER/Guardian%20Ai/app/engine.py)
- Register `@app.command("/report")` handler
- Prompts user with a modal to describe the incident
- Saves a `self_report` audit JSON and posts to `GUARDIAN_SECURITY_CHANNEL`

#### [MODIFY] [.env](file:///c:/Users/USER/Guardian%20Ai/.env)
- Add `GUARDIAN_SECURITY_CHANNEL=` (channel ID for escalation DMs/posts)

> **Note:** Requires Slash Commands enabled in Slack App manifest + `commands` OAuth scope.

---

### Component 4 — False Positive Feedback Loop

Users can react ✅ (`white_check_mark`) to dismiss a warning or ⚠️ (`warning`) to escalate. Guardian logs the feedback against the original incident.

#### [MODIFY] [engine.py](file:///c:/Users/USER/Guardian%20Ai/app/engine.py)
- Register `@app.event("reaction_added")` handler
- Match reaction to a tracked warning message (stored in-memory dict `ACTIVE_WARNINGS`)
- Update the artifact JSON with `user_feedback: "dismissed" | "escalated"`
- If escalated, re-notify `GUARDIAN_SECURITY_CHANNEL`

---

### Component 5 — Email / Alert Escalation

Sends an email alert when severity ≥ 7 (confirmed leaks). Uses Python `smtplib` + env-configured SMTP.

#### [NEW] [app/notifications/email_alerter.py](file:///c:/Users/USER/Guardian%20Ai/app/notifications/email_alerter.py)
- `send_security_alert(report: dict)` — formats and sends HTML email
- Graceful no-op if `ALERT_EMAIL_*` vars are absent

#### [MODIFY] [engine.py](file:///c:/Users/USER/Guardian%20Ai/app/engine.py)
- Call `send_security_alert(report)` after saving audit when `severity >= 7`

#### [MODIFY] [.env](file:///c:/Users/USER/Guardian%20Ai/.env)
- Add `ALERT_EMAIL_FROM=`, `ALERT_EMAIL_TO=`, `ALERT_SMTP_HOST=`, `ALERT_SMTP_PORT=`, `ALERT_SMTP_USER=`, `ALERT_SMTP_PASS=`

---

### Component 6 — Weekly Digest (APScheduler)

Every Monday at 08:00 UTC, posts a summary of the week's incidents to `GUARDIAN_SECURITY_CHANNEL`.

#### [NEW] [app/scheduler.py](file:///c:/Users/USER/Guardian%20Ai/app/scheduler.py)
- Uses `APScheduler` (BackgroundScheduler)
- Reads all `*_incident_*.json` from `/artifacts` from the past 7 days
- Posts a Block Kit digest: total count, top users, severity breakdown, list of confirmed leaks

#### [MODIFY] [main.py](file:///c:/Users/USER/Guardian%20Ai/main.py)
- Start the scheduler before the Socket Mode handler

---

### Component 7 — Dashboard UI (Flask)

A web frontend at `http://localhost:5000` for browsing all incident reports.

#### [NEW] [dashboard/app.py](file:///c:/Users/USER/Guardian%20Ai/dashboard/app.py)
- Flask app with API route `GET /api/incidents` serving all JSONs from `/artifacts`
- Route `GET /` serves the single-page UI

#### [NEW] [dashboard/templates/index.html](file:///c:/Users/USER/Guardian%20Ai/dashboard/templates/index.html)
- Premium dark-mode UI with glassmorphism cards
- Stats bar: Total incidents, Confirmed leaks, High severity count
- Sortable/filterable incident table
- Detail drawer with full JSON + GitHub evidence links
- Severity badge colour-coding (green/amber/red)
- Auto-refreshes every 30 seconds

#### [NEW] [dashboard/run.py](file:///c:/Users/USER/Guardian%20Ai/dashboard/run.py)
- Entry point: `python dashboard/run.py`

---

### Component 8 — Updated Requirements & README

#### [MODIFY] [requirements.txt](file:///c:/Users/USER/Guardian%20Ai/requirements.txt)
- Add `flask`, `apscheduler`

#### [MODIFY] [README.md](file:///c:/Users/USER/Guardian%20Ai/README.md)
- Document all features, env vars, and how to run both the engine and dashboard

---

## Verification Plan

### Automated
```
python -m py_compile app/engine.py app/scheduler.py app/notifications/email_alerter.py dashboard/app.py
```

### Manual
1. Run `python main.py` — engine starts, scheduler starts
2. Send a risky Slack message → confirm warning + audit JSON written with severity score
3. React ✅ to the warning → confirm audit JSON is updated with feedback
4. Use `/report` in Slack → confirm modal + security channel post
5. Run `python dashboard/run.py` → open `localhost:5000` and verify incidents render
