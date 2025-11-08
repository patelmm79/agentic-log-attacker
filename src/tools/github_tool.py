import os
from github import Github

def get_github_issues(repo_url: str) -> list[dict]:
    """Fetches both open and closed issues from a GitHub repository."""
    try:
        token = os.environ["GITHUB_TOKEN"]
        repo_name = repo_url.replace("https://github.com/", "")
        
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        issues = repo.get_issues(state="all")
        
        issue_list = []
        for issue in issues:
            issue_list.append({
                "title": issue.title,
                "number": issue.number,
                "state": issue.state,
                "labels": [label.name for label in issue.labels]
            })

        return issue_list
        
    except Exception as e:
        print(f"Error fetching GitHub issues: {e}")
        return []
