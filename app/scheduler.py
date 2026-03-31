"""
Guardian AI  —  Weekly Digest Scheduler
========================================
Every Monday at 08:00 UTC, posts a Block Kit summary of the
past 7 days' incidents to GUARDIAN_SECURITY_CHANNEL.

Uses APScheduler (BackgroundScheduler) so it runs inside the
same process as the Slack bot — no separate cron job needed.
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger("guardian.scheduler")

ARTIFACTS_DIR = Path("artifacts")


def _load_recent_incidents(days: int = 7) -> list[dict]:
    """Reads all incident JSON files from /artifacts created in the last `days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    incidents = []

    if not ARTIFACTS_DIR.exists():
        return incidents

    for path in ARTIFACTS_DIR.glob("*_incident_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ts = datetime.fromisoformat(data.get("timestamp", ""))
            if ts >= cutoff:
                incidents.append(data)
        except Exception:
            continue  # skip malformed files

    return incidents


def _build_digest_blocks(incidents: list[dict]) -> list[dict]:
    """Builds Slack Block Kit blocks for the weekly digest message."""
    total = len(incidents)
    confirmed = sum(1 for i in incidents if i.get("github_confirmed"))
    high_sev = sum(1 for i in incidents if i.get("severity", 0) >= 7)

    # Severity breakdown
    sev_counter = Counter()
    for inc in incidents:
        s = inc.get("severity", 0)
        if s >= 7:
            sev_counter["🔴 High (7-10)"] += 1
        elif s >= 4:
            sev_counter["🟠 Medium (4-6)"] += 1
        else:
            sev_counter["🟡 Low (1-3)"] += 1

    sev_text = "\n".join(f"  • {k}: *{v}*" for k, v in sev_counter.most_common())
    if not sev_text:
        sev_text = "  _No incidents this week_ 🎉"

    # Top users
    user_counter = Counter(inc.get("user", "unknown") for inc in incidents)
    top_users = "\n".join(
        f"  • <@{user}>: *{count}* incident(s)"
        for user, count in user_counter.most_common(5)
    )
    if not top_users:
        top_users = "  _None_"

    # Confirmed leaks list
    leak_lines = []
    for inc in incidents:
        if inc.get("github_confirmed"):
            ts = inc.get("timestamp", "?")[:10]
            user = inc.get("user", "?")
            reason = inc.get("ai_reasoning", "N/A")[:80]
            leak_lines.append(f"  • `{ts}` — <@{user}> — _{reason}_")
    leaks_text = "\n".join(leak_lines) if leak_lines else "  _No confirmed leaks_ ✅"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Guardian AI — Weekly Security Digest",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Period:* Past 7 days (ending {now})\n\n"
                    f"📈 *Total Incidents:* `{total}`\n"
                    f"🔴 *Confirmed Leaks:* `{confirmed}`\n"
                    f"⚠️ *High Severity (≥7):* `{high_sev}`"
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Severity Breakdown:*\n{sev_text}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Top Flagged Users:*\n{top_users}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Confirmed Leaks:*\n{leaks_text}",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🛡️ _Guardian AI Weekly Digest — {now}_",
                }
            ],
        },
    ]
    return blocks


def post_weekly_digest(slack_app):
    """Collects last 7 days of incidents and posts a digest to Slack."""
    channel = os.getenv("GUARDIAN_SECURITY_CHANNEL")
    if not channel:
        log.warning("⚠️  GUARDIAN_SECURITY_CHANNEL not set — skipping weekly digest.")
        return

    incidents = _load_recent_incidents(days=7)
    blocks = _build_digest_blocks(incidents)

    try:
        slack_app.client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=f"📊 Weekly Security Digest — {len(incidents)} incident(s) this week.",
        )
        log.info("📊 Weekly digest posted to %s (%d incidents).", channel, len(incidents))
    except Exception as e:
        log.error("❌ Failed to post weekly digest: %s", e)


def start_scheduler(slack_app):
    """
    Starts the APScheduler BackgroundScheduler.
    Posts the weekly digest every Monday at 08:00 UTC.
    """
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        post_weekly_digest,
        trigger="cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        args=[slack_app],
        id="weekly_digest",
        replace_existing=True,
    )
    scheduler.start()
    log.info("⏰ Scheduler started — weekly digest runs every Monday 08:00 UTC.")
    return scheduler
