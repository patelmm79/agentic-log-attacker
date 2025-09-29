import json
from pydantic import BaseModel
import google.generativeai as genai

from src.tools.gcp_logging_tool import get_gcp_logs

class Issue(BaseModel):
    """Represents an issue identified in the logs."""
    description: str
    priority: str

def log_reviewer_agent(service_name: str) -> list[Issue]:
    """Analyzes logs from a Google Cloud project and identifies issues."""
    
    logs = get_gcp_logs(service_name=service_name)

    if not logs:
        return []

    prompt = f"""Analyze the following logs and identify any potential issues.
    For each issue, provide a description and a priority (High, Medium, or Low).
    Return the output as a JSON array of objects, where each object has a 'description' and 'priority' key.
    For example:
    [
        {{
            "description": "Null pointer exception in user service",
            "priority": "High"
        }},
        {{
            "description": "Database connection timeout",
            "priority": "Medium"
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
