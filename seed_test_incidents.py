"""
Generates sample incident files in /artifacts so you can test the dashboard.
Run:  python seed_test_incidents.py
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

samples = [
    {
        "user": "U0APVA4D760",
        "channel": "C0AQL1M5M1N",
        "slack_message": "I pasted our entire client database into ChatGPT to help me clean the data",
        "ai_reasoning": "RISK: User admits to uploading confidential customer data to an external AI service (ChatGPT).",
        "severity": 9,
        "github_confirmed": True,
        "github_evidence": [{"url": "https://gist.github.com/example/abc123", "description": "client_data_export.csv", "matched_keyword": "client"}],
        "github_url": "https://gist.github.com/example/abc123",
        "delta_hours": 2,
    },
    {
        "user": "U0APVA4D760",
        "channel": "C0AQL1M5M1N",
        "slack_message": "Here is the prod API key: sk-proj-abc123xyz456 — use it for the demo",
        "ai_reasoning": "RISK: Sharing an API key (sk-proj-...) in plain text in a public channel.",
        "severity": 7,
        "github_confirmed": False,
        "github_evidence": [],
        "github_url": None,
        "delta_hours": 5,
    },
    {
        "user": "U099EXAMPLE",
        "channel": "C0AQL1M5M1N",
        "slack_message": "I uploaded the internal financial report Q1 to my personal Google Drive",
        "ai_reasoning": "RISK: User describes exfiltrating confidential financial data to an external service.",
        "severity": 6,
        "github_confirmed": False,
        "github_evidence": [],
        "github_url": None,
        "delta_hours": 24,
    },
    {
        "user": "U099EXAMPLE",
        "channel": "C0AQL1M5M1N",
        "slack_message": "Used Copilot to refactor the auth module — fed it our entire auth.py with the JWT secret",
        "ai_reasoning": "RISK: User fed proprietary source code containing a JWT secret to an external AI tool.",
        "severity": 8,
        "github_confirmed": True,
        "github_evidence": [{"url": "https://github.com/example/repo/commit/abc123", "commit_message": "refactor auth module", "matched_keyword": "auth"}],
        "github_url": "https://github.com/example/repo/commit/abc123",
        "delta_hours": 48,
        "user_feedback": "escalated",
    },
    {
        "user": "U0APVA4D760",
        "channel": "C0AQL1M5M1N",
        "slack_message": "password for staging DB is Passw0rd!123 if anyone needs it",
        "ai_reasoning": "RISK: Sharing a database password in plain text.",
        "severity": 5,
        "github_confirmed": False,
        "github_evidence": [],
        "github_url": None,
        "delta_hours": 72,
        "user_feedback": "dismissed",
    },
]

for sample in samples:
    ts = datetime.now(timezone.utc) - timedelta(hours=sample.pop("delta_hours"))
    ts_str = ts.strftime("%Y%m%d_%H%M%S")
    user = sample["user"]
    feedback = sample.pop("user_feedback", None)

    report = {
        "timestamp": ts.isoformat(),
        **sample,
        "policy_url": "https://your-company.example.com/internal-ai-policy",
    }
    if feedback:
        report["user_feedback"] = feedback

    path = ARTIFACTS_DIR / f"{ts_str}_incident_{user}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Created: {path.name}  (severity {sample['severity']})")

print(f"\nDone! {len(samples)} test incidents written to /artifacts.")
print("Refresh the dashboard at http://localhost:5000 to see them.")
