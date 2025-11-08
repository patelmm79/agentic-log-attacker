import os
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

def issue_creation_agent(service_name: str, repo_url: str) -> list[Issue]:
    """Analyzes log files and generates issues in every case."""

    print(f"[issue_creation_agent] Fetching logs for service: {service_name}")
    logs, _, error = get_gcp_logs(service_name=service_name, limit=1000)

    if error:
        print(f"[issue_creation_agent] Error fetching logs: {error}")
        return []
    if not logs:
        print("[issue_creation_agent] No logs found for the specified service and time range.")
        return []

    print(f"[issue_creation_agent] Successfully fetched {len(logs.splitlines())} log lines")

    existing_issues = []
    if repo_url:
        print(f"[issue_creation_agent] Fetching existing issues from {repo_url}")
        existing_issues = get_github_issues(repo_url)
        print(f"[issue_creation_agent] Found {len(existing_issues)} existing issues")
    else:
        print("[issue_creation_agent] No repo_url provided, skipping duplicate check")

    existing_issues_str = "\n".join(str(issue) for issue in existing_issues) if existing_issues else "No existing issues."

    prompt = f"""Analyze the following logs and identify any potential issues, errors, warnings, or problems that should be tracked.

    IMPORTANT INSTRUCTIONS:
    - Look for actual problems, errors, warnings, misconfigurations, or performance issues
    - Each issue should be actionable and specific
    - Avoid creating issues that are duplicates of existing ones (listed below)
    - If you find problems in the logs, you MUST create issues for them
    - Return a JSON array even if there are no issues (return empty array [])

    Existing Issues (do not duplicate these):
    {existing_issues_str}

    For each new issue you identify, provide:
    - description: A clear, concise title describing the issue
    - priority: "High" (critical/blocking), "Medium" (important), or "Low" (minor)
    - log_entries: Array of relevant log lines that show the problem

    Output Format (JSON array):
    [
        {{
            "description": "404 errors on /chat/completions endpoint",
            "priority": "High",
            "log_entries": [
                "POST /chat/completions - 404 Not Found",
                "Error: Endpoint not registered"
            ]
        }},
        {{
            "description": "ulimit warning may cause file descriptor exhaustion",
            "priority": "Medium",
            "log_entries": [
                "WARNING: Failed to increase ulimit"
            ]
        }}
    ]

    If no issues are found, return: []

    Logs to analyze:
    {logs}
    """

    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
    print("[issue_creation_agent] Calling Gemini API to analyze logs...")
    response = model.generate_content(prompt)

    try:
        # The response may contain markdown, so we need to extract the JSON part
        print(f"[issue_creation_agent] Raw Gemini response: {response.text[:500]}...")
        json_text = response.text.strip(" `").lstrip("json\n").rstrip("\n`")
        issues_data = json.loads(json_text)

        if not isinstance(issues_data, list):
            print(f"[issue_creation_agent] ⚠️ WARNING: Expected JSON array but got {type(issues_data)}")
            print(f"[issue_creation_agent] Full response: {response.text}")
            return []

        if len(issues_data) == 0:
            print("[issue_creation_agent] ℹ️ Gemini did not identify any issues in the logs")
            print("[issue_creation_agent] This could mean:")
            print("  - The logs don't contain any errors or warnings")
            print("  - The issues already exist in the repository")
            print("  - The logs are purely informational")
            return []

        issues = [Issue(**issue_data) for issue_data in issues_data]
        print(f"[issue_creation_agent] ✅ Successfully parsed {len(issues)} issue(s) from Gemini response")
        for i, issue in enumerate(issues):
            print(f"  {i+1}. {issue.description} (Priority: {issue.priority})")

        return issues
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[issue_creation_agent] ❌ ERROR parsing response from Gemini API: {e}")
        print(f"[issue_creation_agent] This likely means Gemini didn't return valid JSON")
        print(f"[issue_creation_agent] Full response text: {response.text}")
        print("[issue_creation_agent] Returning empty issue list")
        return []
