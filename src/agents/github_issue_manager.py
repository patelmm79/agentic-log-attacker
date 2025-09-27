
import os
from github import Github
from .log_reviewer import Issue

def github_issue_manager_agent(issues: list[Issue]):
    """Creates GitHub issues for a list of issues."""
    try:
        # Get GitHub token and repository from environment variables
        token = os.environ["GITHUB_TOKEN"]
        repo_name = os.environ["GITHUB_REPOSITORY"]

        # Initialize Github object
        g = Github(token)

        # Get the repository
        repo = g.get_repo(repo_name)

    except Exception as e:
        return {"github_issue_manager_history": [f"Error initializing GitHub: {e}"]}

    created_issues = 0
    for issue in issues:
        try:
            repo.create_issue(
                title=f"Bug: {issue.description[:50]}",
                body=issue.description,
                labels=[issue.priority]
            )
            created_issues += 1
        except Exception as e:
            print(f"Error creating GitHub issue: {e}")

    return {"github_issue_manager_history": [f"Created {created_issues} GitHub issues."]}
