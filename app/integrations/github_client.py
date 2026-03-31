import os
import base64
from github import Github
from dotenv import load_dotenv

load_dotenv()

class GitHubClient:
    def __init__(self):
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN not found in .env")
        self.gh = Github(token)

    def get_repo_dependencies(self, repo_full_name):
        """
        Scans common manifest files for AI-related libraries.
        Example repo_full_name: 'your-org/your-repo'
        """
        repo = self.gh.get_repo(repo_full_name)
        manifests = ["requirements.txt", "package.json", "Pipfile", "pyproject.toml"]
        results = {}

        for file_path in manifests:
            try:
                content_file = repo.get_contents(file_path)
                # GitHub returns base64 encoded content
                decoded = base64.b64decode(content_file.content).decode("utf-8")
                results[file_path] = decoded
            except Exception:
                continue # File not found in this repo
        
        return results