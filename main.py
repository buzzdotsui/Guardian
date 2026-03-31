import os
import sys
from dotenv import load_dotenv
from app.engine import app 
from slack_bolt.adapter.socket_mode import SocketModeHandler

# 1. Load configuration from .env file
load_dotenv()

def bootstrap():
    """Ensures the environment is ready for Guardian to run."""
    print("🛡️  Guardian AI: Bootstrapping System...")
    
    # Create artifacts folder if it doesn't exist
    if not os.path.exists("artifacts"):
        os.makedirs("artifacts")
        print("📁 Created 'artifacts' directory.")

    # We check for the NAMES of the variables, not the values themselves
    required_vars = [
        "SLACK_BOT_TOKEN", 
        "SLACK_APP_TOKEN", 
        "GITHUB_TOKEN", 
        "GROQ_API_KEY"
    ]
    
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print(f"❌ ERROR: Missing environment variables: {', '.join(missing)}")
        print("Check your .env file. It should look like: SLACK_BOT_TOKEN=xoxb-...")
        sys.exit(1)
    else:
        print("✅ Environment Variables Verified.")

if __name__ == "__main__":
    bootstrap()
    
    # 2. Launch the Engine
    print("🚀 Initializing Socket Mode...")
    
    # We pull the actual value from the environment using the label
    app_token = os.getenv("SLACK_APP_TOKEN")
    
    try:
        handler = SocketModeHandler(app, app_token)
        print("⚡ GUARDIAN IS ONLINE. Listening for threats...")
        handler.start()
    except Exception as e:
        print(f"❌ Failed to start Guardian: {e}")