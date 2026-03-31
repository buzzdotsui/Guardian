import os
import re
import base64
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()


class GitHubClient:
    def __init__(self):
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN not found in .env")
        self.gh = Github(token)

    # ------------------------------------------------------------------ #
    # Original method — kept intact
    # ------------------------------------------------------------------ #
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
                decoded = base64.b64decode(content_file.content).decode("utf-8")
                results[file_path] = decoded
            except Exception:
                continue

        return results

    # ------------------------------------------------------------------ #
    # NEW — Cross-correlation helpers
    # ------------------------------------------------------------------ #
    def _extract_keywords(self, text: str, max_words: int = 10) -> list[str]:
        """
        Pulls meaningful tokens from the suspicious message to use as
        search fingerprints.  Strips stop-words and keeps tokens ≥ 4 chars.
        """
        stop_words = {
            "the", "and", "for", "with", "this", "that", "have", "from",
            "they", "will", "your", "what", "when", "where", "there",
            "just", "some", "like", "into", "then", "than", "been",
            "also", "more", "only", "over", "such", "after", "want",
        }
        tokens = re.findall(r"[A-Za-z0-9_@.\-]{4,}", text)
        unique = list(dict.fromkeys(
            t.lower() for t in tokens if t.lower() not in stop_words
        ))
        return unique[:max_words]

    def scan_user_gists(self, github_username: str, message_text: str) -> dict:
        """
        Searches the user's public gists for content matching keywords
        extracted from the suspicious Slack message.

        Returns a dict:
            {
                "confirmed": bool,
                "evidence": [{ "gist_id", "description", "url", "matched_keyword", "snippet" }]
            }
        """
        keywords = self._extract_keywords(message_text)
        evidence = []

        try:
            user = self.gh.get_user(github_username)
            gists = user.get_gists()          # paginated public gists

            for gist in gists:
                for filename, gist_file in gist.files.items():
                    # Pull the raw content (small files only to stay fast)
                    raw_content = ""
                    try:
                        if gist_file.size and gist_file.size < 50_000:
                            import requests
                            r = requests.get(gist_file.raw_url, timeout=8)
                            raw_content = r.text if r.ok else ""
                    except Exception:
                        raw_content = ""

                    haystack = (filename + " " + (gist.description or "") + " " + raw_content).lower()

                    for kw in keywords:
                        if kw in haystack:
                            # Grab a 120-char context snippet
                            idx = haystack.find(kw)
                            snippet = haystack[max(0, idx - 40): idx + 80].replace("\n", " ")
                            evidence.append({
                                "gist_id": gist.id,
                                "description": gist.description or filename,
                                "url": gist.html_url,
                                "matched_keyword": kw,
                                "snippet": snippet,
                            })
                            break  # one hit per gist file is enough

        except GithubException as e:
            print(f"⚠️  GitHub API error scanning gists for '{github_username}': {e}")
        except Exception as e:
            print(f"⚠️  Unexpected error in scan_user_gists: {e}")

        return {"confirmed": len(evidence) > 0, "evidence": evidence}

    def scan_user_commits(self, github_username: str, message_text: str,
                          max_repos: int = 5) -> dict:
        """
        Searches recent commit messages across the user's public repos for
        keywords matching the suspicious Slack message.

        Returns a dict:
            {
                "confirmed": bool,
                "evidence": [{ "repo", "commit_sha", "commit_message", "url", "matched_keyword" }]
            }
        """
        keywords = self._extract_keywords(message_text)
        evidence = []

        try:
            user = self.gh.get_user(github_username)
            repos = list(user.get_repos(type="public", sort="pushed"))[:max_repos]

            for repo in repos:
                try:
                    commits = repo.get_commits()  # most-recent first
                    for commit in list(commits)[:20]:  # cap at 20 commits per repo
                        msg = (commit.commit.message or "").lower()
                        for kw in keywords:
                            if kw in msg:
                                evidence.append({
                                    "repo": repo.full_name,
                                    "commit_sha": commit.sha[:10],
                                    "commit_message": commit.commit.message[:200],
                                    "url": commit.html_url,
                                    "matched_keyword": kw,
                                })
                                break
                except GithubException:
                    continue

        except GithubException as e:
            print(f"⚠️  GitHub API error scanning commits for '{github_username}': {e}")
        except Exception as e:
            print(f"⚠️  Unexpected error in scan_user_commits: {e}")

        return {"confirmed": len(evidence) > 0, "evidence": evidence}