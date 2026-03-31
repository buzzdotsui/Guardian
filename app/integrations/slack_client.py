import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SlackClient:
    def __init__(self):
        self.token = os.getenv("SLACK_BOT_TOKEN")
        self.base_url = "https://slack.com/api/conversations.history"
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def get_recent_messages(self, channel_id, limit=20):
        """Fetches the latest messages from a specific channel."""
        params = {"channel": channel_id, "limit": limit}
        response = requests.get(self.base_url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return data.get("messages", [])
            print(f"Slack API Error: {data.get('error')}")
        return []