import os
import logging
from google.cloud.logging import Client, DESCENDING
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
    logger.info(f"Fetching logs for service: {service_name}, Project ID: {project_id}")
    client = Client(project=project_id)

    # Build time filter component if provided
    time_filter = ""
    if start_time and end_time:
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            if end - start > timedelta(days=1):
                raise ValueError("Time range cannot exceed 24 hours.")
            time_filter = f' AND timestamp >= "{start_time}" AND timestamp <= "{end_time}"'
        except ValueError as e:
            return "", None, e

    # Try multiple filter variations for Cloud Run logs
    # Include severity >= DEFAULT to capture all log levels including DEFAULT
    filter_variations = [
        # Original filter with service_name
        f'resource.type = "cloud_run_revision" AND resource.labels.service_name = "{service_name}" AND severity >= DEFAULT{time_filter}',
        # Try with configuration_name (common alternative)
        f'resource.type = "cloud_run_revision" AND resource.labels.configuration_name = "{service_name}" AND severity >= DEFAULT{time_filter}',
        # Try matching any label value (broader search)
        f'resource.type = "cloud_run_revision" AND ("{service_name}") AND severity >= DEFAULT{time_filter}',
    ]

    try:
        for i, log_filter in enumerate(filter_variations):
            logger.info(f"[Filter {i+1}/3] Trying: {log_filter}")
            entries = client.list_entries(
                filter_=log_filter,
                order_by=DESCENDING,
                page_size=limit
            )
            log_entries = [str(entry) for i, entry in enumerate(entries) if i < limit]

            if log_entries:
                logs = "\n".join(log_entries)
                logger.info(f"✓ SUCCESS! Found {len(log_entries)} log entries using filter variation {i+1}")
                return logs, None, None
            else:
                logger.warning(f"✗ No logs found with filter variation {i+1}")

        # If no filter worked, return empty
        logger.error(f"FAILED: No logs found with any of the {len(filter_variations)} filter variations for service '{service_name}'")
        return "", None, None

    except Exception as e:
        logger.error(f"Error fetching logs: {e}", exc_info=True)
        return "", None, e