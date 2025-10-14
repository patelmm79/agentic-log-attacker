import os
from github import Github

def get_github_issues(repo_url: str) -> list[str]:
    """Fetches the titles of open issues from a GitHub repository."""
    try:
        token = os.environ["GITHUB_TOKEN"]
        repo_name = repo_url.replace("https://github.com/", "")
        
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        issues = repo.get_issues(state="open")
        
        return [issue.title for issue in issues]
        
    except Exception as e:
        print(f"Error fetching GitHub issues: {e}")
        return []
