import os
from dotenv import load_dotenv
from app.integrations.slack_client import SlackClient
from app.integrations.github_client import GitHubClient

load_dotenv()

def run_guardian_audit():
    print("🛡️  Guardian AI: Starting Mission...")
    
    # 1. Setup Clients
    slack = SlackClient()
    github = GitHubClient()
    
    # 2. Audit Slack (Conversational Shadow AI)
    print("--- Scanning Slack ---")
    # Replace with your actual Channel ID from earlier
    messages = slack.get_recent_messages("C0APKAS4GE7") 
    for msg in messages:
        text = msg.get('text', '').lower()
        if any(word in text for word in ["claude", "gpt-4", "perplexity", "midjourney"]):
            print(f"⚠️  FLAGGED SLACK: User {msg.get('user')} mentioned a potential Shadow AI tool.")

    # 3. Audit GitHub (Infrastructure Shadow AI)
    print("\n--- Scanning GitHub ---")
    # Replace with a repo you own/have access to
    repo_name = "YOUR_USERNAME/YOUR_REPO" 
    deps = github.get_repo_dependencies(repo_name)
    for file, content in deps.items():
        if "openai" in content or "langchain" in content:
            print(f"🚨 ALERT GITHUB: Unauthorized AI library found in {file} of {repo_name}")

if __name__ == "__main__":
    run_guardian_audit()