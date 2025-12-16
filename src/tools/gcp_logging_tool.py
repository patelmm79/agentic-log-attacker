import os
import logging
import re
from typing import Optional, Tuple
from google.cloud.logging import Client, DESCENDING
from datetime import datetime, timedelta
from src.models.service_types import ServiceType, SERVICE_CONFIG

logger = logging.getLogger(__name__)


def build_filter_variations(config: dict, service_name: str, project_id: str, time_filter: str) -> list:
    """Build filter variations for GCP log queries.

    Args:
        config: Service configuration from SERVICE_CONFIG containing resource_type and filter_variations.
        service_name: The sanitized service name to use in filters.
        project_id: The sanitized project ID to use in filters.
        time_filter: The timestamp filter string (e.g., ' AND timestamp >= "..." AND timestamp <= "..."').

    Returns:
        A list of filter strings ready for use with GCP Logging API.
    """
    filter_variations = []
    for filter_template in config["filter_variations"]:
        # Replace placeholders with actual values
        filter_str = filter_template.format(
            service_name=service_name,
            project_id=project_id
        )
        # Combine resource type, service filter, severity, and time filters
        full_filter = f'resource.type = "{config["resource_type"]}" AND {filter_str} AND severity >= DEFAULT{time_filter}'
        filter_variations.append(full_filter)

    return filter_variations


def sanitize_identifier(identifier: str, identifier_type: str = "service_name") -> str:
    """Sanitize identifiers (service names, project IDs) to prevent filter injection.

    Args:
        identifier: The identifier to sanitize (e.g., service name, project ID).
        identifier_type: The type of identifier for error messages.

    Returns:
        The sanitized identifier.

    Raises:
        ValueError: If the identifier contains invalid characters.
    """
    if not identifier:
        raise ValueError(f"{identifier_type} cannot be empty")

    # Allow only alphanumeric characters, hyphens, underscores, and dots
    # This matches GCP naming conventions
    if not re.match(r'^[a-zA-Z0-9._-]+$', identifier):
        raise ValueError(
            f"Invalid {identifier_type}: '{identifier}'. "
            f"Only alphanumeric characters, hyphens, underscores, and dots are allowed."
        )

    # Additional length validation (GCP service names are typically max 63 chars)
    if len(identifier) > 255:
        raise ValueError(f"{identifier_type} exceeds maximum length of 255 characters")

    return identifier

def get_gcp_logs(service_name: str, service_type: str = "cloud_run", limit: int = 500, page_token: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None) -> Tuple[str, Optional[str], Optional[Exception]]:
    """Fetches logs from a Google Cloud project for a specific service.

    Args:
        service_name: The name/ID of the service (e.g., service name, build ID, function name).
        service_type: The type of GCP service (cloud_run, cloud_build, cloud_functions, gce, gke, app_engine).
        limit: The maximum number of log entries to fetch.
        page_token: The token for the next page of logs.
        start_time: The start of the time range in ISO 8601 format (e.g., '2024-01-01T12:00:00Z').
        end_time: The end of the time range in ISO 8601 format (e.g., '2024-01-01T13:00:00Z').

    Returns:
        A tuple containing:
        - str: The log entries as a newline-separated string
        - Optional[str]: The next page token (None if no more pages)
        - Optional[Exception]: An exception if one occurred (None on success)
    """

    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]

    # Sanitize inputs to prevent filter injection attacks
    try:
        service_name = sanitize_identifier(service_name, "service_name")
        project_id = sanitize_identifier(project_id, "project_id")
    except ValueError as e:
        logger.error(f"Input validation failed: {e}")
        return "", None, e

    # Convert string to ServiceType enum
    try:
        service_type_enum = ServiceType(service_type)
    except ValueError:
        error_msg = f"Unsupported service type: {service_type}. Supported types: {', '.join([t.value for t in ServiceType])}"
        logger.error(error_msg)
        return "", None, ValueError(error_msg)

    logger.info(f"Fetching logs for service: {service_name}, Type: {service_type_enum.value}, Project ID: {project_id}")
    client = Client(project=project_id)

    # Build time filter component if provided, otherwise use default 24-hour lookback
    time_filter = ""
    auto_retry_48h = False

    if start_time and end_time:
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            if end - start > timedelta(days=2):
                raise ValueError("Time range cannot exceed 48 hours.")
            time_filter = f' AND timestamp >= "{start_time}" AND timestamp <= "{end_time}"'
        except ValueError as e:
            return "", None, e
    else:
        # Default to 24-hour lookback, with automatic 48-hour retry if no logs found
        auto_retry_48h = True
        end = datetime.utcnow()
        start = end - timedelta(hours=24)
        time_filter = f' AND timestamp >= "{start.isoformat()}Z" AND timestamp <= "{end.isoformat()}Z"'
        logger.info(f"Using default 24-hour lookback: {start.isoformat()}Z to {end.isoformat()}Z")

    # Get service-specific configuration
    config = SERVICE_CONFIG.get(service_type_enum)
    if not config:
        error_msg = f"No configuration found for service type: {service_type_enum}"
        logger.error(error_msg)
        return "", None, ValueError(error_msg)

    # Build filter variations based on service type
    filter_variations = build_filter_variations(config, service_name, project_id, time_filter)
    logger.info(f"Generated {len(filter_variations)} filter variations for {service_type_enum.value}")

    try:
        for i, log_filter in enumerate(filter_variations):
            logger.info(f"[Filter {i+1}/{len(filter_variations)}] Trying: {log_filter}")
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

        # If no logs found and we used the default 24-hour window, try 48 hours
        if auto_retry_48h:
            logger.info("No logs found in 24-hour window. Retrying with 48-hour window...")
            end = datetime.utcnow()
            start = end - timedelta(hours=48)
            time_filter_48h = f' AND timestamp >= "{start.isoformat()}Z" AND timestamp <= "{end.isoformat()}Z"'

            # Rebuild filter variations with 48h time window
            filter_variations_48h = build_filter_variations(config, service_name, project_id, time_filter_48h)

            for i, log_filter in enumerate(filter_variations_48h):
                logger.info(f"[48h Filter {i+1}/{len(filter_variations_48h)}] Trying: {log_filter}")
                entries = client.list_entries(
                    filter_=log_filter,
                    order_by=DESCENDING,
                    page_size=limit
                )
                log_entries = [str(entry) for i, entry in enumerate(entries) if i < limit]

                if log_entries:
                    logs = "\n".join(log_entries)
                    logger.info(f"✓ SUCCESS! Found {len(log_entries)} log entries in 48-hour window using filter variation {i+1}")
                    return logs, None, None
                else:
                    logger.warning(f"✗ No logs found with 48h filter variation {i+1}")

        # If no filter worked, return empty
        logger.error(f"FAILED: No logs found with any of the filter variations for service '{service_name}'")
        return "", None, None

    except Exception as e:
        logger.error(f"Error fetching logs: {e}", exc_info=True)
        return "", None, e