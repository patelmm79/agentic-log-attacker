
import os
import json
from github import Github
import google.generativeai as genai
from src.agents.issue_creation_agent import Issue
from ..tools.github_tool import get_github_issues

def github_issue_manager_agent(issues: list[Issue], repo_url: str, user_query: str = None, issue_content: str = None):
    """Creates GitHub issues for a list of issues."""
    if not issues and issue_content:
        # If no issues are provided, but issue_content is, create an issue from it.
        # The issue_content is expected to be the full body of the issue.
        title = issue_content.split('\n')[0] if '\n' in issue_content else issue_content
        issues = [Issue(description=title, priority="High", log_entries=[issue_content])]
    elif not issues and user_query:
        # If there are no issues and no issue_content, try to create one from the user query
        prompt = f"""You are a GitHub issue manager. Your job is to extract the title and body of a GitHub issue from the user's query.
        Return a JSON object with the keys 'title' and 'body'.

        User Query: {user_query}
        """
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
        response = model.generate_content(prompt)
        raw_response_text = response.text
        print(f"Gemini API raw response: {raw_response_text}")
        # Strip markdown code block syntax if present
        if raw_response_text.startswith('```json') and raw_response_text.endswith('```'):
            json_string = raw_response_text[len('```json\n'):-len('\n```')]
        else:
            json_string = raw_response_text

        try:
            issue_data = json.loads(json_string)
            if issue_data:
                issues = [Issue(description=issue_data['title'], priority="High", log_entries=[issue_data['body']])] 
        except (json.JSONDecodeError, TypeError) as e:
            return {"github_issue_manager_history": [f"Error parsing response from Gemini API: {e}. Raw response: {raw_response_text}"]}

    """Creates GitHub issues for a list of issues."""
    if not repo_url:
        return {"github_issue_manager_history": ["Error: GitHub repository URL not set."]}

    try:
        # Get GitHub token from environment variables
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            return {"github_issue_manager_history": ["Error: GITHUB_TOKEN environment variable not set."]}
        
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
            title = issue.description[:256] # Use the description as the title, up to 256 chars
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
