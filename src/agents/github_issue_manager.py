
import os
from github import Github
from .log_reviewer import Issue
from ..tools.github_tool import get_github_issues

def github_issue_manager_agent(issues: list[Issue], repo_url: str):
    """Creates GitHub issues for a list of issues."""
    try:
        # Get GitHub token from environment variables
        token = os.environ["GITHUB_TOKEN"]
        
        # Get repo name from URL
        repo_name = repo_url.replace("https://github.com/", "")

        # Initialize Github object
        g = Github(token)

        # Get the repository
        repo = g.get_repo(repo_name)

        # Get existing issues
        existing_issues = get_github_issues(repo_url)
        existing_titles = [issue['title'] for issue in existing_issues]

    except Exception as e:
        return {"github_issue_manager_history": [f"Error initializing GitHub: {e}"]}

    created_issues = 0
    skipped_issues = 0
    for issue in issues:
        try:
            title = f"Bug: {issue.description[:50]}"
            if title in existing_titles:
                # Check if the issue is open or closed with "wontfix"
                for existing_issue in existing_issues:
                    if existing_issue['title'] == title:
                        if existing_issue['state'] == 'open':
                            print(f"Skipping issue '{title}' as it already exists and is open.")
                            skipped_issues += 1
                            break
                        elif existing_issue['state'] == 'closed' and 'wontfix' in existing_issue['labels']:
                            print(f"Skipping issue '{title}' as it already exists and is closed with 'wontfix' label.")
                            skipped_issues += 1
                            break
                else:
                    continue
            else:
                log_entries_str = "\n".join(issue.log_entries)
                body = f"""{issue.description}

**Relevant Log Entries:**
```
{log_entries_str}
```
"""
                repo.create_issue(
                    title=title,
                    body=body,
                    labels=[issue.priority]
                )
                created_issues += 1
        except Exception as e:
            print(f"Error creating GitHub issue: {e}")

    return {"github_issue_manager_history": [f"Created {created_issues} GitHub issues, skipped {skipped_issues}."]}
