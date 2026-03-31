"""
Guardian AI  —  Core Engine
============================
Orchestrates the full enforcement workflow:
  1.  Receive Slack message via Socket Mode
  2.  Analyse with Groq (Llama 3.3-70b) using a refined, low-false-positive prompt
  3.  On RISK  →  cross-correlate with GitHub gists & recent commits
  4.  Severity scoring (1-10) based on AI keywords + GitHub confirmation
  5.  On confirmed leak  →  post an in-thread Security Warning to the user in Slack
  6.  Email escalation for severity ≥ 7
  7.  Always write a structured JSON audit report to /artifacts
  8.  Channel allowlist gating
  9.  /report self-report slash command
  10. Reaction-based feedback loop (✅ dismiss / ⚠️ escalate)
"""

import os
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from groq import Groq
from dotenv import load_dotenv

from app.integrations.github_client import GitHubClient
from app.notifications.email_alerter import send_security_alert
from app.scanners.secret_scanner import scan_for_secrets

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("guardian")

# Ensure the artifacts directory always exists
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Policy URL — replace with your real Confluence / Notion page
INTERNAL_AI_POLICY_URL = "https://your-company.example.com/internal-ai-policy"

# ---------------------------------------------------------------------------
# Channel Allowlist  (Component 2)
# ---------------------------------------------------------------------------
_raw_channels = os.getenv("GUARDIAN_CHANNELS", "").strip()
ALLOWED_CHANNELS: set[str] | None = (
    {c.strip() for c in _raw_channels.split(",") if c.strip()}
    if _raw_channels else None
)

# Security channel for escalation DMs / digest posts
SECURITY_CHANNEL = os.getenv("GUARDIAN_SECURITY_CHANNEL", "")

# ---------------------------------------------------------------------------
# In-memory warning tracker  (Component 4  —  maps message_ts → report dict)
# ---------------------------------------------------------------------------
ACTIVE_WARNINGS: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

try:
    github_client = GitHubClient()
    log.info("✅ GitHub client ready.")
except ValueError as e:
    github_client = None
    log.warning("⚠️  GitHub client unavailable — cross-correlation disabled. (%s)", e)

# ---------------------------------------------------------------------------
# Refined System Prompt  (fewer false positives)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are Guardian AI, a corporate security auditor embedded in a Slack workspace.

Your ONLY job is to detect genuine data-security violations. Apply strict criteria:

FLAG as RISK (reply: "RISK: <concise reason>") ONLY when the message clearly shows:
  • Sharing actual credentials, API keys, passwords, tokens, or secrets in plain text.
  • Uploading, posting, or describing plans to exfiltrate proprietary source code,
    customer PII, internal financials, or other confidential company data to
    an external service, repository, or person.
  • Using an explicitly unauthorised AI tool to process confidential company data
    (e.g. "I pasted our client list into ChatGPT").

IGNORE and reply "SAFE" for:
  • General "how-to" or conceptual questions about AI, coding, or tools.
  • Mentioning AI tool names without evidence of data transfer.
  • Hypothetical or educational discussions.
  • Messages containing only code snippets with no confidential context.
  • Questions asking whether something is allowed.

Be concise. One sentence max in your RISK reason. No preamble or explanation.
""".strip()

# ---------------------------------------------------------------------------
# Severity scoring  (Component 1)
# ---------------------------------------------------------------------------
# Keywords that indicate higher severity (regex patterns, case-insensitive)
_HIGH_SEVERITY_PATTERNS = [
    r"credential", r"password", r"secret", r"api[_\- ]?key",
    r"token", r"exfiltrat", r"upload", r"paste", r"leak",
    r"pii", r"ssn", r"credit.?card", r"customer.?data",
]

def compute_severity_score(ai_reasoning: str, github_confirmed: bool) -> int:
    """
    Computes a 1–10 severity score from two signals:
      • Groq confidence keywords → base score (1–7)
      • GitHub confirmation bonus → +3 (capped at 10)
    """
    text = ai_reasoning.lower()

    # Count how many high-severity patterns match
    hits = sum(1 for pat in _HIGH_SEVERITY_PATTERNS if re.search(pat, text))

    # Map hits to a base score (1–7)
    if hits >= 4:
        base = 7
    elif hits >= 3:
        base = 6
    elif hits >= 2:
        base = 5
    elif hits >= 1:
        base = 4
    else:
        base = 2  # RISK detected but no high-severity keywords

    # GitHub confirmation bonus
    if github_confirmed:
        base += 3

    return min(base, 10)


def _severity_emoji(score: int) -> str:
    """Returns a colour-coded emoji for the severity score."""
    if score >= 7:
        return "🔴"
    elif score >= 4:
        return "🟠"
    return "🟡"

# ---------------------------------------------------------------------------
# Groq analysis
# ---------------------------------------------------------------------------

def analyze_security_risk(text: str) -> str:
    """
    Sends `text` to Groq for intent analysis.
    Returns either  "SAFE"  or  "RISK: <reason>".
    """
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Slack message: {text}"},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0,   # deterministic — reduces creative false positives
            max_tokens=120,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.error("❌ Groq API error: %s", e)
        return "ERROR"

# ---------------------------------------------------------------------------
# GitHub cross-correlation
# ---------------------------------------------------------------------------

def run_github_cross_correlation(slack_user_id: str, message_text: str) -> dict:
    """
    Maps the Slack user ID to a GitHub username via the env var
    GITHUB_USER_MAP (JSON dict: {"U12345": "github-handle", ...}).
    Falls back to a best-effort search if the map is absent.

    Returns a merged result dict with keys: confirmed, evidence, github_url.
    """
    if github_client is None:
        return {"confirmed": False, "evidence": [], "github_url": None}

    # Resolve Slack user ID → GitHub username
    user_map_raw = os.getenv("GITHUB_USER_MAP", "{}")
    try:
        user_map: dict = json.loads(user_map_raw)
    except json.JSONDecodeError:
        user_map = {}

    github_username = user_map.get(slack_user_id)

    if not github_username:
        log.info(
            "ℹ️  No GitHub username mapped for Slack user %s — skipping cross-correlation.",
            slack_user_id,
        )
        return {"confirmed": False, "evidence": [], "github_url": None}

    log.info("🔍 Cross-correlating GitHub activity for %s (%s)…", slack_user_id, github_username)

    gist_result   = github_client.scan_user_gists(github_username, message_text)
    commit_result = github_client.scan_user_commits(github_username, message_text)

    all_evidence = gist_result["evidence"] + commit_result["evidence"]
    confirmed    = gist_result["confirmed"] or commit_result["confirmed"]

    # Pick the best evidence URL for the audit report
    github_url = None
    if all_evidence:
        github_url = all_evidence[0].get("url") or all_evidence[0].get("commit_url")

    return {
        "confirmed":  confirmed,
        "evidence":   all_evidence,
        "github_url": github_url,
    }

# ---------------------------------------------------------------------------
# Slack — post security warning  (updated with severity badge)
# ---------------------------------------------------------------------------

def post_security_warning(
    channel: str, thread_ts: str, user_id: str, ai_reasoning: str, severity: int
) -> str | None:
    """
    Posts a formatted, in-thread Security Warning visible to the whole channel.
    Returns the warning message timestamp (for tracking) or None on failure.
    """
    emoji = _severity_emoji(severity)

    warning_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 Guardian AI — Security Warning",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"<@{user_id}> — Guardian AI has detected a potential *Shadow AI / data-leak risk* "
                    "in your message.\n\n"
                    f"*AI Reasoning:* _{ai_reasoning}_\n"
                    f"*Severity:* {emoji} *{severity}/10*"
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"📋 Please review our *<{INTERNAL_AI_POLICY_URL}|Internal AI Policy>* "
                    "before sharing company data with external AI services.\n\n"
                    "React ✅ to dismiss  •  React ⚠️ to escalate to Security."
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"⏱ Detected at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                }
            ],
        },
    ]

    try:
        result = app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            blocks=warning_blocks,
            text=f"🚨 Security Warning for <@{user_id}> — Severity {severity}/10",
        )
        warning_ts = result.get("ts")
        log.info("📢 Security Warning posted in thread %s (ts=%s).", thread_ts, warning_ts)
        return warning_ts
    except Exception as e:
        log.error("❌ Failed to post Slack warning: %s", e)
        return None

def send_remediation_dm(channel: str, user_id: str, ai_reasoning: str, severity: int):
    """
    Sends a private DM to the offending user with remediation steps.
    """
    emoji = _severity_emoji(severity)
    
    dm_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🛡️ Guardian AI — Action Required",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"Hi <@{user_id}>, I detected a potential security risk in your recent message in <#{channel}>.\n\n"
                    f"*AI Reasoning:* _{ai_reasoning}_\n"
                    f"*Severity:* {emoji} *{severity}/10*\n\n"
                    "*What you need to do:*\n"
                    "1. If this was a real credential or customer data leak, rotate the key or delete the uploaded data immediately.\n"
                    "2. If this was a mistake or false positive, react to my message in the channel with ✅ to dismiss it.\n"
                    f"3. Review our <{INTERNAL_AI_POLICY_URL}|Internal AI Policy> for more guidance."
                ),
            },
        },
    ]

    try:
        app.client.chat_postMessage(
            channel=user_id,
            blocks=dm_blocks,
            text=f"🛡️ Action Required: Security risk detected (Severity {severity}/10)",
        )
        log.info("📩 Remediation DM sent to user %s.", user_id)
    except Exception as e:
        log.error("❌ Failed to send DM to user %s: %s", user_id, e)

# ---------------------------------------------------------------------------
# Audit logging  (updated with severity field)
# ---------------------------------------------------------------------------

def save_audit_report(
    user_id: str,
    channel: str,
    message_text: str,
    ai_reasoning: str,
    github_result: dict,
    severity: int,
    detected_by: str = "ai",
) -> dict:
    """
    Writes a JSON incident report to /artifacts/<timestamp>_incident.json.
    Returns the report dict.
    """
    timestamp   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = ARTIFACTS_DIR / f"{timestamp}_incident_{user_id}.json"

    report = {
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "user":             user_id,
        "channel":          channel,
        "slack_message":    message_text,
        "ai_reasoning":     ai_reasoning,
        "severity":         severity,
        "detected_by":      detected_by,
        "github_confirmed": github_result["confirmed"],
        "github_evidence":  github_result["evidence"],
        "github_url":       github_result.get("github_url"),
        "policy_url":       INTERNAL_AI_POLICY_URL,
    }

    try:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("📁 Audit report saved → %s", report_path)
    except Exception as e:
        log.error("❌ Failed to write audit report: %s", e)

    return report

# ---------------------------------------------------------------------------
# Main message event handler  —  full enforcement orchestration
# ---------------------------------------------------------------------------

@app.event("message")
def handle_message_events(body, logger):
    """
    Full enforcement workflow:
        1. Gate-check (ignore bots, empty messages, channel allowlist)
        2. Groq AI risk analysis
        3. If RISK → GitHub cross-correlation
        4. Compute severity score
        5. If confirmed leak → post threaded Slack warning
        6. If severity ≥ 7 → send email alert
        7. Always log incident to /artifacts (only on RISK)
    """
    event   = body.get("event", {})
    channel = event.get("channel", "")
    ts      = event.get("ts", "")          # timestamp = unique message ID
    user_id = event.get("user")

    # ── 1. Gate-check ────────────────────────────────────────────────────
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return  # Never respond to ourselves — prevents infinite loops

    text = event.get("text", "").strip()
    if not text or not user_id:
        return

    # Channel allowlist (Component 2)
    if ALLOWED_CHANNELS is not None and channel not in ALLOWED_CHANNELS:
        return  # silently skip channels not in the allowlist

    log.info("👂 [%s] Analysing message from %s: '%s…'", channel, user_id, text[:60])

    # ── 2. Pattern-Based Secret Scanner (Fast Path) ──────────────────────
    secret_matches = scan_for_secrets(text)
    detected_by = "regex" if secret_matches else "ai"

    if secret_matches:
        # Highest severity matched
        base_severity = max(m.severity for m in secret_matches)
        discovered_secrets = ", ".join(m.pattern_name for m in secret_matches)
        ai_decision = f"RISK: Regex detected secrets: {discovered_secrets}."
        log.warning("🚨 [FAST PATH] Regex secret match for %s: %s", user_id, discovered_secrets)
        # We skip Groq if regex hits
    else:
        # ── 2.5 Groq AI risk analysis ─────────────────────────────────────────
        ai_decision = analyze_security_risk(text)
    
        if ai_decision == "ERROR":
            log.warning("⚠️  Skipping enforcement — Groq returned an error.")
            return
    
        if "RISK" not in ai_decision.upper():
            log.info("✅ SAFE — no action required.")
            return

    # ── 3. RISK detected — run GitHub cross-correlation ──────────────────
    log.warning("🚨 RISK DETECTED for user %s | Reason: %s", user_id, ai_decision)

    github_result = run_github_cross_correlation(user_id, text)

    if github_result["confirmed"]:
        log.warning(
            "🔴 CONFIRMED LEAK — GitHub evidence found: %d item(s).",
            len(github_result["evidence"]),
        )
    else:
        log.info(
            "🟡 UNCONFIRMED — No matching GitHub activity found (or no mapping set). "
            "Posting warning from AI signal alone."
        )

    # ── 4. Compute severity score ────────────────────────────────────────
    if detected_by == "regex":
        severity = base_severity
        if github_result["confirmed"]:
            severity = min(severity + 3, 10)
    else:
        severity = compute_severity_score(ai_decision, github_result["confirmed"])
    
    log.info("📊 Severity score: %s %d/10", _severity_emoji(severity), severity)

    # ── 5. Post in-thread Security Warning ──────────────────────────────
    warning_ts = post_security_warning(
        channel      = channel,
        thread_ts    = ts,
        user_id      = user_id,
        ai_reasoning = ai_decision,
        severity     = severity,
    )

    # ── 6. Write audit report ────────────────────────────────────────────
    report = save_audit_report(
        user_id       = user_id,
        channel       = channel,
        message_text  = text,
        ai_reasoning  = ai_decision,
        github_result = github_result,
        severity      = severity,
        detected_by   = detected_by,
    )

    # ── 6.5 Send DM Remediation Steps ────────────────────────────────────
    send_remediation_dm(
        channel=channel,
        user_id=user_id,
        ai_reasoning=ai_decision,
        severity=severity,
    )

    # ── 7. Track warning for feedback loop ──────────────────────────────
    if warning_ts:
        ACTIVE_WARNINGS[warning_ts] = report

    # ── 8. Email escalation for high severity ───────────────────────────
    if severity >= 7:
        send_security_alert(report)


# ---------------------------------------------------------------------------
# Component 3  —  /report  Self-Report Slash Command
# ---------------------------------------------------------------------------

@app.command("/report")
def handle_report_command(ack, body, client):
    """Opens a modal for users to self-report a potential security incident."""
    ack()

    trigger_id = body.get("trigger_id")
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "self_report_modal",
            "title": {"type": "plain_text", "text": "🛡️ Self-Report"},
            "submit": {"type": "plain_text", "text": "Submit Report"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "Use this form to proactively report a potential security "
                            "violation you've observed or been involved in."
                        ),
                    },
                },
                {
                    "type": "input",
                    "block_id": "description_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Describe the incident. What happened, when, and who was involved?",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Incident Description"},
                },
                {
                    "type": "input",
                    "block_id": "severity_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "severity",
                        "placeholder": {"type": "plain_text", "text": "Select severity"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "🟡 Low (1-3)"}, "value": "3"},
                            {"text": {"type": "plain_text", "text": "🟠 Medium (4-6)"}, "value": "5"},
                            {"text": {"type": "plain_text", "text": "🔴 High (7-10)"}, "value": "8"},
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Estimated Severity"},
                },
            ],
        },
    )


@app.view("self_report_modal")
def handle_self_report_submission(ack, body, client, view):
    """Processes the self-report modal submission."""
    ack()

    user_id = body["user"]["id"]
    values = view["state"]["values"]
    description = values["description_block"]["description"]["value"]
    severity = int(values["severity_block"]["severity"]["selected_option"]["value"])

    # Save a self_report audit JSON
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = ARTIFACTS_DIR / f"{timestamp}_incident_{user_id}.json"

    report = {
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "type":          "self_report",
        "user":          user_id,
        "channel":       "self-report",
        "slack_message": description,
        "ai_reasoning":  "Self-reported by user via /report command.",
        "severity":      severity,
        "github_confirmed": False,
        "github_evidence":  [],
        "github_url":    None,
        "policy_url":    INTERNAL_AI_POLICY_URL,
    }

    try:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("📁 Self-report saved → %s", report_path)
    except Exception as e:
        log.error("❌ Failed to write self-report: %s", e)

    # Notify GUARDIAN_SECURITY_CHANNEL
    if SECURITY_CHANNEL:
        emoji = _severity_emoji(severity)
        try:
            client.chat_postMessage(
                channel=SECURITY_CHANNEL,
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🗣️ Self-Report Received",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"<@{user_id}> submitted a self-report.\n\n"
                                f"*Description:*\n> {description}\n\n"
                                f"*Severity:* {emoji} *{severity}/10*"
                            ),
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"⏱ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                            }
                        ],
                    },
                ],
                text=f"🗣️ Self-report from <@{user_id}> — Severity {severity}/10",
            )
            log.info("📢 Self-report notification sent to security channel.")
        except Exception as e:
            log.error("❌ Failed to post self-report to security channel: %s", e)

    # Also send email if severity is high
    if severity >= 7:
        send_security_alert(report)


# ---------------------------------------------------------------------------
# Component 4  —  Reaction-Based Feedback Loop
# ---------------------------------------------------------------------------

@app.event("reaction_added")
def handle_reaction_feedback(body, client, logger):
    """
    Listens for ✅ (white_check_mark) and ⚠️ (warning) reactions on
    tracked warning messages. Updates the audit JSON accordingly.
    """
    event = body.get("event", {})
    reaction = event.get("reaction", "")
    item = event.get("item", {})
    item_ts = item.get("ts", "")
    channel = item.get("channel", "")
    reactor = event.get("user", "")

    # Only process reactions on tracked warnings
    if item_ts not in ACTIVE_WARNINGS:
        return

    report = ACTIVE_WARNINGS[item_ts]

    if reaction == "white_check_mark":
        feedback = "dismissed"
        log.info("✅ User %s dismissed warning %s.", reactor, item_ts)
    elif reaction == "warning":
        feedback = "escalated"
        log.info("⚠️ User %s escalated warning %s.", reactor, item_ts)
    else:
        return  # ignore other reactions

    # Update the report with feedback
    report["user_feedback"] = feedback
    report["feedback_by"] = reactor
    report["feedback_at"] = datetime.now(timezone.utc).isoformat()

    # Find and update the corresponding artifact JSON on disk
    _update_artifact_feedback(report, feedback)

    # If escalated, re-notify GUARDIAN_SECURITY_CHANNEL
    if feedback == "escalated" and SECURITY_CHANNEL:
        try:
            severity = report.get("severity", 0)
            emoji = _severity_emoji(severity)
            client.chat_postMessage(
                channel=SECURITY_CHANNEL,
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "⚠️ Incident Escalated",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"<@{reactor}> has escalated an incident.\n\n"
                                f"*Original user:* <@{report.get('user', '?')}>\n"
                                f"*Severity:* {emoji} *{severity}/10*\n"
                                f"*AI Reasoning:* _{report.get('ai_reasoning', 'N/A')}_"
                            ),
                        },
                    },
                ],
                text=f"⚠️ Incident escalated by <@{reactor}>",
            )
            log.info("📢 Escalation notification sent to security channel.")
        except Exception as e:
            log.error("❌ Failed to send escalation notification: %s", e)

    # Remove from active tracking
    del ACTIVE_WARNINGS[item_ts]


def _update_artifact_feedback(report: dict, feedback: str):
    """Finds the matching incident JSON on disk and updates it with feedback."""
    user_id = report.get("user", "")
    ts_str = report.get("timestamp", "")

    for path in ARTIFACTS_DIR.glob(f"*_incident_{user_id}.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("timestamp") == ts_str:
                data["user_feedback"] = feedback
                data["feedback_by"] = report.get("feedback_by")
                data["feedback_at"] = report.get("feedback_at")
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                log.info("📝 Updated artifact with feedback: %s → %s", path.name, feedback)
                return
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Component E  —  Slack App Home Tab
# ---------------------------------------------------------------------------

@app.event("app_home_opened")
def update_app_home(client, event, logger):
    """
    Renders Guardian AI's App Home tab with stats and quick links.
    """
    user_id = event["user"]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🛡️ Guardian AI Home",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Welcome! I am your automated data-security auditor. I monitor Slack and cross-correlate with GitHub to detect Shadow AI usage and leaked credentials."
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Quick Actions*"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📄 Read AI Policy",
                        "emoji": True
                    },
                    "url": INTERNAL_AI_POLICY_URL,
                    "action_id": "policy_btn"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Self-Report Incident",
                        "emoji": True
                    },
                    "action_id": "home_report_btn"
                }
            ]
        }
    ]

    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: %s", e)

@app.action("home_report_btn")
def handle_home_report_btn(ack, body, client):
    """Trigger the `/report` modal from the App Home button."""
    ack()
    
    # We can reuse the modal presentation from the slash command
    trigger_id = body.get("trigger_id")
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "self_report_modal",
            "title": {"type": "plain_text", "text": "🛡️ Self-Report"},
            "submit": {"type": "plain_text", "text": "Submit Report"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Use this form to proactively report a potential security violation you've observed or been involved in."
                    }
                },
                {
                    "type": "input",
                    "block_id": "description_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "Describe the incident..."}
                    },
                    "label": {"type": "plain_text", "text": "Incident Description"}
                },
                {
                    "type": "input",
                    "block_id": "severity_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "severity",
                        "placeholder": {"type": "plain_text", "text": "Select severity"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "🟡 Low (1-3)"}, "value": "3"},
                            {"text": {"type": "plain_text", "text": "🟠 Medium (4-6)"}, "value": "5"},
                            {"text": {"type": "plain_text", "text": "🔴 High (7-10)"}, "value": "8"},
                        ]
                    },
                    "label": {"type": "plain_text", "text": "Estimated Severity"}
                }
            ]
        }
    )

@app.action("policy_btn")
def handle_policy_btn(ack):
    """Acknowledge the link button click"""
    ack()


# ---------------------------------------------------------------------------
# Standalone entry-point (for direct `python app/engine.py` runs)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token:
        log.critical("❌ SLACK_APP_TOKEN is missing from .env — cannot start.")
    else:
        handler = SocketModeHandler(app, app_token)
        log.info("⚡ Guardian AI Engine is LIVE and listening…")
        handler.start()