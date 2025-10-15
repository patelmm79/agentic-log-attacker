import os
from google.cloud.logging import Client, DESCENDING
from datetime import datetime, timedelta

def get_gcp_logs(service_name: str, limit: int = 500, page_token: str = None, start_time: str = None, end_time: str = None) -> tuple[str, str, Exception]:
    """Fetches logs from a Google Cloud project for a specific service.

    Args:
        service_name: The name of the Cloud Run service.
        limit: The maximum number of log entries to fetch.
        page_token: The token for the next page of logs.
        start_time: The start of the time range in ISO 8601 format (e.g., '2024-01-01T12:00:00Z').
        end_time: The end of the time range in ISO 8601 format (e.g., '2024-01-01T13:00:00Z').

    Returns:
        A tuple containing the log entries, the next page token, and an exception if one occurred.
    """
    
    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    print(f"Project ID: {project_id}")
    client = Client(project=project_id)
    
    log_filter = f'resource.type = "cloud_run_revision" AND resource.labels.service_name = "{service_name}"'

    if start_time and end_time:
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            if end - start > timedelta(days=1):
                raise ValueError("Time range cannot exceed 24 hours.")
            log_filter += f' AND timestamp >= "{start_time}" AND timestamp <= "{end_time}"'
        except ValueError as e:
            return "", None, e

    try:
        entries = client.list_entries(
            filter_=log_filter,
            order_by=DESCENDING,
            page_size=limit
        )
        log_entries = [str(entry) for i, entry in enumerate(entries) if i < limit]
        logs = "\n".join(log_entries)
        return logs, None, None

    except Exception as e:
        print(f"Error fetching logs: {e}")
        return "", None, e