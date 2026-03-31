"""
Guardian AI  —  Pattern-Based Secret Scanner
=============================================
Fast regex-based detection of secrets and credentials in message text.
Runs BEFORE the Groq AI analysis as a zero-latency first pass.

If a secret pattern is matched, the engine can skip the Groq call entirely
and immediately flag the message as RISK with high severity.
"""

import re
import logging
from dataclasses import dataclass

log = logging.getLogger("guardian.secrets")


@dataclass
class SecretMatch:
    """Represents a detected secret in a message."""
    pattern_name: str
    matched_text: str      # redacted snippet
    severity: int          # suggested severity (8-10)
    description: str


# ────────────────────────────────────────────────────────
# Regex patterns for common secret types
# Each tuple: (name, compiled_regex, severity, description)
# ────────────────────────────────────────────────────────
_PATTERNS: list[tuple[str, re.Pattern, int, str]] = [
    (
        "AWS Access Key",
        re.compile(r"(?:^|[^A-Z0-9])(?P<key>AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)"),
        9,
        "AWS IAM access key ID detected.",
    ),
    (
        "AWS Secret Key",
        re.compile(r"(?:aws_secret_access_key|aws_secret|secret_key)\s*[=:]\s*['\"]?(?P<key>[A-Za-z0-9/+=]{40})['\"]?", re.IGNORECASE),
        10,
        "AWS secret access key detected.",
    ),
    (
        "GitHub Token (ghp/gho/ghu/ghs/ghr)",
        re.compile(r"(?P<key>(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255})"),
        9,
        "GitHub personal access token detected.",
    ),
    (
        "GitHub PAT (Classic)",
        re.compile(r"(?P<key>github_pat_[A-Za-z0-9_]{22,255})"),
        9,
        "GitHub fine-grained personal access token detected.",
    ),
    (
        "Slack Bot Token",
        re.compile(r"(?P<key>xoxb-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,34})"),
        10,
        "Slack bot token detected.",
    ),
    (
        "Slack App Token",
        re.compile(r"(?P<key>xapp-[0-9]-[A-Z0-9]+-[0-9]+-[A-Za-z0-9]+)"),
        10,
        "Slack app-level token detected.",
    ),
    (
        "Slack Webhook URL",
        re.compile(r"(?P<key>https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+)"),
        8,
        "Slack incoming webhook URL detected.",
    ),
    (
        "Generic API Key",
        re.compile(r"(?:api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*['\"]?(?P<key>[A-Za-z0-9_\-]{20,64})['\"]?", re.IGNORECASE),
        8,
        "Generic API key/secret detected.",
    ),
    (
        "OpenAI API Key",
        re.compile(r"(?P<key>sk-[A-Za-z0-9]{20,}T3BlbkFJ[A-Za-z0-9]{20,})"),
        9,
        "OpenAI API key detected.",
    ),
    (
        "Groq API Key",
        re.compile(r"(?P<key>gsk_[A-Za-z0-9]{20,})"),
        9,
        "Groq API key detected.",
    ),
    (
        "JWT Token",
        re.compile(r"(?P<key>eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"),
        8,
        "JSON Web Token (JWT) detected.",
    ),
    (
        "SSH Private Key",
        re.compile(r"(?P<key>-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)"),
        10,
        "SSH/RSA private key header detected.",
    ),
    (
        "Password in Connection String",
        re.compile(r"(?:mysql|postgres|postgresql|mongodb|redis|amqp)://[^:]+:(?P<key>[^@\s]{4,})@", re.IGNORECASE),
        9,
        "Database password in connection string detected.",
    ),
    (
        "Bearer Token",
        re.compile(r"(?:Authorization|Bearer)\s*[=:]\s*['\"]?Bearer\s+(?P<key>[A-Za-z0-9_\-.]{20,})['\"]?", re.IGNORECASE),
        8,
        "Authorization bearer token detected.",
    ),
    (
        "Private Key (Hex/Base64)",
        re.compile(r"(?:private[_-]?key|secret[_-]?key|signing[_-]?key)\s*[=:]\s*['\"]?(?P<key>[A-Fa-f0-9]{32,}|[A-Za-z0-9+/=]{40,})['\"]?", re.IGNORECASE),
        9,
        "Private/signing key value detected.",
    ),
    (
        "Google API Key",
        re.compile(r"(?P<key>AIza[0-9A-Za-z_-]{35})"),
        8,
        "Google API key detected.",
    ),
    (
        "Stripe Secret Key",
        re.compile(r"(?P<key>sk_(?:live|test)_[0-9a-zA-Z]{24,})"),
        10,
        "Stripe secret API key detected.",
    ),
    (
        "SendGrid API Key",
        re.compile(r"(?P<key>SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43})"),
        8,
        "SendGrid API key detected.",
    ),
    (
        "Heroku API Key",
        re.compile(r"(?:heroku.*api[_-]?key|HEROKU_API_KEY)\s*[=:]\s*['\"]?(?P<key>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})['\"]?", re.IGNORECASE),
        8,
        "Heroku API key (UUID) detected.",
    ),
]


def _redact(text: str, max_show: int = 8) -> str:
    """Shows the first `max_show` chars and redacts the rest."""
    if len(text) <= max_show:
        return text
    return text[:max_show] + "•" * min(len(text) - max_show, 20)


def scan_for_secrets(text: str) -> list[SecretMatch]:
    """
    Scans message text against all known secret patterns.
    Returns a list of SecretMatch objects (may be empty).
    """
    matches: list[SecretMatch] = []

    for name, pattern, severity, description in _PATTERNS:
        for m in pattern.finditer(text):
            raw = m.group("key") if "key" in m.groupdict() else m.group(0)
            matches.append(SecretMatch(
                pattern_name=name,
                matched_text=_redact(raw),
                severity=severity,
                description=description,
            ))

    if matches:
        log.warning(
            "🔐 Secret scanner found %d pattern match(es): %s",
            len(matches),
            ", ".join(m.pattern_name for m in matches),
        )

    return matches
