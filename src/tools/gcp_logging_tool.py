import os
from google.cloud.logging import Client

def get_gcp_logs(service_name: str) -> str:
    """Fetches logs from a Google Cloud project for a specific service.

    Args:
        service_name: The name of the Cloud Run service.

    Returns:
        A string containing the log entries.
    """
    
    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    print (f"Project ID: {project_id}")
    client = Client(project=project_id)
    # A simplified log filter
    log_filter = f'resource.type = "cloud_run_revision" AND resource.labels.service_name = "{service_name}"'

    try:
        entries = client.list_entries(
            filter_=log_filter,
            page_size=100, # Limit the number of log entries for now
        )
        
        log_entries = []
        for entry in entries:
            log_entries.append(str(entry))

        logs = "\n".join(log_entries)

        return logs

    except Exception as e:
        print(f"Error fetching logs: {e}")
        return ""