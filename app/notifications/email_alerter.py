"""
Guardian AI  —  Email Alert Escalation
=======================================
Sends an HTML email alert for high-severity incidents (severity ≥ 7).
Gracefully no-ops when ALERT_EMAIL_* env vars are not configured.
"""

import os
import ssl
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

log = logging.getLogger("guardian.email")


def _get_smtp_config() -> dict | None:
    """Returns SMTP config dict if all required vars are present, else None."""
    required = {
        "from":     os.getenv("ALERT_EMAIL_FROM"),
        "to":       os.getenv("ALERT_EMAIL_TO"),
        "host":     os.getenv("ALERT_SMTP_HOST"),
        "port":     os.getenv("ALERT_SMTP_PORT", "587"),
        "user":     os.getenv("ALERT_SMTP_USER"),
        "password": os.getenv("ALERT_SMTP_PASS"),
    }
    if not all([required["from"], required["to"], required["host"]]):
        return None
    return required


def _build_html(report: dict) -> str:
    """Builds a styled HTML email body from an incident report."""
    severity = report.get("severity", 0)
    sev_colour = "#e74c3c" if severity >= 8 else "#e67e22" if severity >= 5 else "#27ae60"
    confirmed = "✅ Yes" if report.get("github_confirmed") else "❌ No"
    github_url = report.get("github_url") or "N/A"
    if github_url != "N/A":
        github_url = f'<a href="{github_url}">{github_url}</a>'

    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 24px;">
      <div style="max-width: 600px; margin: 0 auto; background: #16213e; border-radius: 12px; overflow: hidden; border: 1px solid #0f3460;">
        <div style="background: linear-gradient(135deg, #0f3460, #e94560); padding: 20px 24px;">
          <h1 style="margin: 0; color: #ffffff; font-size: 22px;">🚨 Guardian AI — Security Alert</h1>
        </div>
        <div style="padding: 24px;">
          <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460; font-weight: bold; width: 160px;">Severity</td>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460;">
                <span style="background: {sev_colour}; color: #fff; padding: 3px 10px; border-radius: 6px; font-weight: bold;">{severity}/10</span>
              </td>
            </tr>
            <tr>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460; font-weight: bold;">User</td>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460;">{report.get("user", "Unknown")}</td>
            </tr>
            <tr>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460; font-weight: bold;">Channel</td>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460;">{report.get("channel", "Unknown")}</td>
            </tr>
            <tr>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460; font-weight: bold;">AI Reasoning</td>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460;">{report.get("ai_reasoning", "N/A")}</td>
            </tr>
            <tr>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460; font-weight: bold;">GitHub Confirmed</td>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460;">{confirmed}</td>
            </tr>
            <tr>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460; font-weight: bold;">GitHub URL</td>
              <td style="padding: 10px 0; border-bottom: 1px solid #0f3460;">{github_url}</td>
            </tr>
            <tr>
              <td style="padding: 10px 0; font-weight: bold;">Slack Message</td>
              <td style="padding: 10px 0;"><code style="background: #0f3460; padding: 4px 8px; border-radius: 4px;">{report.get("slack_message", "")[:300]}</code></td>
            </tr>
          </table>
          <p style="margin-top: 20px; font-size: 12px; color: #888;">
            Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by Guardian AI
          </p>
        </div>
      </div>
    </body>
    </html>
    """


def send_security_alert(report: dict) -> bool:
    """
    Sends an HTML email alert for the given incident report.
    Returns True if sent successfully, False otherwise.
    Gracefully no-ops if SMTP is not configured.
    """
    config = _get_smtp_config()
    if config is None:
        log.info("📧 Email alerting skipped — ALERT_EMAIL_* env vars not configured.")
        return False

    severity = report.get("severity", 0)
    subject = f"🚨 Guardian AI Alert — Severity {severity}/10 — {report.get('user', 'Unknown')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["from"]
    msg["To"] = config["to"]

    plain = (
        f"Guardian AI Security Alert\n"
        f"Severity: {severity}/10\n"
        f"User: {report.get('user')}\n"
        f"AI Reasoning: {report.get('ai_reasoning')}\n"
        f"GitHub Confirmed: {report.get('github_confirmed')}\n"
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(_build_html(report), "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(config["host"], int(config["port"]), timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            if config.get("user") and config.get("password"):
                server.login(config["user"], config["password"])
            server.sendmail(config["from"], config["to"].split(","), msg.as_string())
        log.info("📧 Email alert sent to %s", config["to"])
        return True
    except Exception as e:
        log.error("❌ Failed to send email alert: %s", e)
        return False
