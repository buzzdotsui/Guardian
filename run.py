# run.py

from app.scanners.shadow_ai_detector import detect_shadow_ai

test_messages = [
    "Hey I used ChatGPT to fix this bug",
    "Here is the API key: sk-123456",
    "Let's deploy this tomorrow",
]

for msg in test_messages:
    result = detect_shadow_ai(msg)
    print(f"\nMessage: {msg}")
    print(f"Risk: {result}")