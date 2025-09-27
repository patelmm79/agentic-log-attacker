import os
import json
from pydantic import BaseModel
import google.generativeai as genai
from google.cloud import logging_v2

class Issue(BaseModel):
    """Represents an issue identified in the logs."""
    description: str
    priority: str

def log_reviewer_agent() -> list[Issue]:
    """Analyzes logs from a Google Cloud project and identifies issues."""
    
    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    service_name = os.environ["CLOUD_RUN_SERVICE_NAME"]
    region = os.environ["CLOUD_RUN_REGION"]

    client = logging_v2.services.logging_service_v2.LoggingServiceV2Client()
    resource_names = [f"projects/{project_id}"]
    # Filter for logs from the last 24 hours from a specific Cloud Run service
    filter_ = f'''resource.type = "cloud_run_revision"
               resource.labels.service_name = "{service_name}"
               resource.labels.location = "{region}"
               timestamp >= "2025-09-26T00:00:00Z"'''

    try:
        entries = client.list_log_entries(
            resource_names=resource_names,
            filter_=filter_,
            page_size=100, # Limit the number of log entries for now
        )
        
        log_entries = []
        for entry in entries:
            log_entries.append(str(entry))

        logs = "\n".join(log_entries)

        if not logs:
            return []

    except Exception as e:
        print(f"Error fetching logs: {e}")
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

    model = genai.GenerativeModel('gemini-pro')
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