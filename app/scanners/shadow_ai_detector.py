def detect_shadow_ai(text: str) -> str:
    text_lower = text.lower()

    keywords = ["chatgpt", "openai", "claude", "prompt"]

    if any(k in text_lower for k in keywords):
        return "⚠️ Suspicious (AI usage)"

    if "api key" in text_lower or "sk-" in text_lower:
        return "🚨 High Risk (Secret exposure)"

    return "✅ Safe"