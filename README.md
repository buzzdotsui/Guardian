# 🛡️ Guardian AI

**Enterprise Shadow AI & Data-Leak Detection for Slack**

Guardian AI is a real-time security enforcement engine that monitors Slack messages for data-security violations — leaked credentials, unauthorised AI tool usage, and data exfiltration. It cross-correlates findings with GitHub activity and provides severity-scored incident reports with full audit trails.

---

## ✨ Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Regex Secret Scanner** | Zero-latency pre-filter matching 19+ secret patterns (AWS, GitHub, Slack tokens, SSH keys, etc.) |
| 2 | **AI Risk Analysis** | Groq-powered (Llama 3.3-70b) context analysis for generic leaks or Shadow AI usage |
| 3 | **GitHub Cross-Correlation** | Scans user gists & recent commits for leaked content matching Slack messages |
| 4 | **Severity Scoring** | 1–10 risk score computed from regex matches, AI confidence, and GitHub confirmation |
| 5 | **Actionable DMs** | Sends a private Slack DM with remediation steps to the offending user |
| 6 | **Channel Allowlist** | Restrict monitoring to specific Slack channels via `GUARDIAN_CHANNELS` |
| 7 | **`/report` Command** | Users self-report incidents via a Slack modal |
| 8 | **Feedback Loop** | React ✅ to dismiss or ⚠️ to escalate — feedback persisted in audit JSON |
| 9 | **Slack App Home** | Quick links and stats view natively in the Slack App Home tab |
| 10 | **Email Escalation** | Severity ≥ 7 triggers an HTML email alert via SMTP |
| 11 | **Weekly Digest** | APScheduler posts a Block Kit summary every Monday 08:00 UTC |
| 12 | **Auth Dashboard** | Protected dark-mode web dashboard featuring Chart.js incident analytics |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- A Slack App with Socket Mode enabled, plus these scopes: `chat:write`, `reactions:read`, `commands`
- GROQ API key
- GitHub personal access token

### Installation

**Option A: Run with Docker (Recommended for Production)**
Guardian AI is fully containerised. The easiest way to run the engine and dashboard is via Docker Compose:

```bash
git clone https://github.com/your-org/guardian-ai.git
cd guardian-ai
docker-compose up -d --build
```

**Option B: Local Deployment (Development)**
```bash
git clone https://github.com/your-org/guardian-ai.git
cd guardian-ai
pip install -r requirements.txt
```

### Configuration

Copy the env template and fill in your values:

```env
# ─── Required ──────────────────────────────────────────
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
GITHUB_TOKEN=github_pat_...
GROQ_API_KEY=gsk_...
GITHUB_USER_MAP={"U12345": "github-username"}

# ─── Optional Feature Config ──────────────────────────
# Channel allowlist (comma-separated IDs). Empty = monitor all.
GUARDIAN_CHANNELS=

# Security channel for escalations, self-reports, weekly digests.
GUARDIAN_SECURITY_CHANNEL=C0123456789

# ─── Email Alerting (optional) ────────────────────────
ALERT_EMAIL_FROM=guardian@company.com
ALERT_EMAIL_TO=security@company.com
ALERT_SMTP_HOST=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_SMTP_USER=
ALERT_SMTP_PASS=

# ─── Dashboard Auth ───────────────────────────────────
DASHBOARD_USER=admin
DASHBOARD_PASS=guardian
```

### Run the Engine (Local Dev)

```bash
# First time DB Setup/Migration
python migrate_json_to_db.py

# Start the Engine
python main.py
```

This starts:
- The Slack Socket Mode listener (real-time message monitoring)
- The APScheduler weekly digest (Monday 08:00 UTC)

### Run the Dashboard (Local Dev)

```bash
python dashboard/run.py
```

Open **http://localhost:5000** to view the incident dashboard.

---

## 📁 Project Structure

```
guardian-ai/
├── main.py                          # Entry point — starts engine + scheduler
├── app/
│   ├── engine.py                    # Core enforcement engine (all Slack handlers)
│   ├── scheduler.py                 # APScheduler weekly digest
│   ├── database.py                  # SQLAlchemy Engine & Session setup
│   ├── models.py                    # SQLAlchemy Incident schema
│   ├── integrations/
│   │   ├── github_client.py         # GitHub gist & commit scanner
│   │   └── slack_client.py          # Slack helper utilities
│   ├── notifications/
│   │   └── email_alerter.py         # SMTP email escalation
│   ├── scanners/
│   │   └── shadow_ai_detector.py    # Shadow AI detection patterns
│   └── data/                        # Static data / pattern files
├── dashboard/
│   ├── app.py                       # Flask API, login, and analytics endpoints
│   ├── run.py                       # Dashboard entry point
│   └── templates/
│       ├── index.html               # Dark-mode dashboard with Chart.js
│       └── login.html               # Authentication page
├── data/                            # Persistent SQLite database storage
├── requirements.txt
├── .env
├── Dockerfile                       # Multi-stage Docker container
├── docker-compose.yml               # Production Compose file
├── migrate_json_to_db.py            # Used to migrate old JSON artifacts to SQLite
└── README.md
```

---

## 🔒 Severity Scoring

| Score | Level | Criteria |
|-------|-------|----------|
| 1–3 | 🟡 Low | Risk flagged but no high-severity keywords |
| 4–6 | 🟠 Medium | Contains some credential/leak-related keywords |
| 7–10 | 🔴 High | Multiple keyword hits and/or GitHub-confirmed leak |

GitHub confirmation adds **+3** to the base score (capped at 10).

---

## 🗣️ Slack Commands

### `/report`
Opens a modal for any user to self-report a potential security incident. The report is saved as an audit JSON and posted to the `GUARDIAN_SECURITY_CHANNEL`.

### Reaction Feedback
On any Guardian warning message:
- React **✅** (`white_check_mark`) → Dismiss the warning (marked in audit JSON)
- React **⚠️** (`warning`) → Escalate to the security channel

---

## 📧 Email Alerts

When an incident scores **severity ≥ 7**, an HTML email is sent via SMTP. Configure the `ALERT_EMAIL_*` env vars to enable. If not configured, email alerting is silently skipped.

---

## 📊 Weekly Digest

Every **Monday at 08:00 UTC**, a Block Kit digest is posted to `GUARDIAN_SECURITY_CHANNEL` containing:
- Total incident count
- Severity breakdown
- Top flagged users
- List of confirmed leaks

---

## 📋 License

MIT License — see [LICENSE](LICENSE) for details.
