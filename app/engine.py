import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from groq import Groq
from dotenv import load_dotenv

# 1. Load the .env file so os.getenv can find your keys
load_dotenv()

# 2. Initialize Clients using the VARIABLE NAMES from your .env
# This is the "Valet Ticket" method: os.getenv("LABEL")
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_security_risk(text):
    """Uses Groq (Llama 3) to analyze the intent behind a message."""
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the Guardian AI Security Auditor. "
                        "Analyze the message. If it involves sharing credentials, "
                        "using unauthorized AI tools, or leaking company data, "
                        "respond with 'RISK: [brief reason]'. "
                        "Otherwise, respond with 'SAFE'."
                    )
                },
                {
                    "role": "user",
                    "content": f"Analyze this Slack message: {text}"
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        # If the API key is invalid, this will print the 401 error
        print(f"❌ Brain Error (Groq): {e}")
        return "ERROR"

@app.event("message")
def handle_message_events(body, logger):
    event = body.get("event", {})
    
    # Security Rule: Ignore bot messages to prevent infinite feedback loops
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    text = event.get("text", "")
    user = event.get("user")

    if not text:
        return

    print(f"\n👂 Hearing: '{text[:50]}...'")
    
    # Trigger the AI Analysis
    decision = analyze_security_risk(text)
    
    if "RISK" in decision.upper():
        print(f"🚨 ALERT: Potential Shadow AI risk detected from user {user}!")
        print(f"   AI Reasoning: {decision}")
    else:
        print("✅ Analysis: Message appears safe.")

if __name__ == "__main__":
    # Pull the App Token for the Socket Mode connection
    app_token = os.getenv("SLACK_APP_TOKEN")
    
    if not app_token:
        print("❌ CRITICAL ERROR: SLACK_APP_TOKEN is missing from .env!")
    else:
        handler = SocketModeHandler(app, app_token)
        print("⚡ Guardian AI Engine is LIVE and listening...")
        handler.start()