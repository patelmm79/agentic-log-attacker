import json
from pydantic import BaseModel
import google.generativeai as genai

from src.tools.gcp_logging_tool import get_gcp_logs
from src.tools.github_tool import get_github_issues

class Issue(BaseModel):
    """Represents an issue identified in the logs."""
    description: str
    priority: str
    log_entries: list[str]

def log_reviewer_agent(service_name: str, repo_url: str) -> list[Issue]:
    """Analyzes logs from a Google Cloud project and identifies issues."""
    
    logs = get_gcp_logs(service_name=service_name)

    if not logs:
        return []

    existing_issues = get_github_issues(repo_url)
    existing_issues_str = "\n".join(existing_issues)

    prompt = f"""Analyze the following logs and identify any potential new issues.
    Avoid creating issues that are duplicates of existing ones.

    Existing Issues:
    {existing_issues_str}

    For each new issue, provide a description, a priority (High, Medium, or Low), and the relevant log entries.
    Return the output as a JSON array of objects, where each object has a 'description', 'priority', and 'log_entries' key.
    For example:
    [
        {{
            "description": "Null pointer exception in user service",
            "priority": "High",
            "log_entries": [
                "log entry 1",
                "log entry 2"
            ]
        }},
        {{
            "description": "Database connection timeout",
            "priority": "Medium",
            "log_entries": [
                "log entry 3"
            ]
        }}
    ]

    Logs:
    {logs}
    """

    model = genai.GenerativeModel('models/gemini-pro-latest')
    response = model.generate_content(prompt)

    try:
        # The response may contain markdown, so we need to extract the JSON part
        json_text = response.text.strip(" `").lstrip("json\n").rstrip("\n`")
        issues_data = json.loads(json_text)
        issues = [Issue(**issue_data) for issue_data in issues_data]
        return issues
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing response from Gemini API: {e}")
        print(f"Response text: {response.text}")
        return []
