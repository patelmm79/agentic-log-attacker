
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
    skipped_reasons = []
    error_messages = []

    print(f"\n[github_issue_manager] Processing {len(issues)} issues...")
    print(f"[github_issue_manager] Found {len(existing_issues)} existing issues in repository")

    for i, issue in enumerate(issues):
        try:
            title = issue.description[:256] # Use the description as the title, up to 256 chars
            print(f"\n[github_issue_manager] Issue {i+1}/{len(issues)}: '{title}'")
            print(f"[github_issue_manager] Priority: {issue.priority}")

            if title in existing_titles:
                print(f"[github_issue_manager] ⚠️  Title matches existing issue, checking status...")
                # Check if the issue is open or closed with "wontfix"
                for existing_issue in existing_issues:
                    if existing_issue['title'] == title:
                        if existing_issue['state'] == 'open':
                            reason = f"Issue '{title[:100]}...' already exists and is open (#{existing_issue.get('number', 'unknown')})"
                            print(f"[github_issue_manager] ❌ SKIPPED: {reason}")
                            skipped_issues += 1
                            skipped_reasons.append(reason)
                            break
                        elif existing_issue['state'] == 'closed' and 'wontfix' in existing_issue['labels']:
                            reason = f"Issue '{title[:100]}...' is closed with 'wontfix' label (#{existing_issue.get('number', 'unknown')})"
                            print(f"[github_issue_manager] ❌ SKIPPED: {reason}")
                            skipped_issues += 1
                            skipped_reasons.append(reason)
                            break
                else:
                    # Duplicate title but not open or wontfix, proceed to create
                    print(f"[github_issue_manager] ✓ Duplicate title but issue is closed, will create new one")
                    pass
            else:
                print(f"[github_issue_manager] ✓ No duplicate found, creating new issue...")

            # Only create if we didn't skip in the above logic
            if title not in existing_titles or (title in existing_titles and not any(r.startswith(f"Issue '{title[:100]}") for r in skipped_reasons)):
                log_entries_str = "\n".join(issue.log_entries)
                body = f"""{issue.description}

**Relevant Log Entries:**
```
{log_entries_str}
```
"""
                print(f"[github_issue_manager] 📝 Calling GitHub API to create issue...")
                result = repo.create_issue(
                    title=title,
                    body=body,
                    labels=[issue.priority]
                )
                print(f"[github_issue_manager] ✅ SUCCESS! Created issue #{result.number}: {result.html_url}")
                created_issues += 1
        except Exception as e:
            error_msg = f"Error creating issue '{title[:100]}...': {str(e)}"
            print(f"[github_issue_manager] ❌ ERROR: {error_msg}")
            error_messages.append(error_msg)

    # Build detailed status message
    status_parts = [f"Created {created_issues} GitHub issue(s), skipped {skipped_issues}."]

    if skipped_issues > 0:
        status_parts.append("\n\nSkipped issues:")
        for reason in skipped_reasons:
            status_parts.append(f"  - {reason}")

    if error_messages:
        status_parts.append("\n\nErrors encountered:")
        for error in error_messages:
            status_parts.append(f"  - {error}")

    if created_issues == 0 and skipped_issues == 0 and not error_messages:
        status_parts.append("\n\n⚠️ No issues were created or skipped. Possible reasons:")
        status_parts.append("  - The issue list provided was empty")
        status_parts.append("  - All issues were filtered out during processing")

    status_message = "\n".join(status_parts)
    print(f"\n[github_issue_manager] Final status: {status_message}")

    return {"github_issue_manager_history": [status_message]}
