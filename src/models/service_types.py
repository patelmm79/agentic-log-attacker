"""Service type definitions and configurations for GCP log monitoring."""

from enum import Enum
from typing import Dict, List


class ServiceType(str, Enum):
    """Enum for supported GCP service types."""
    CLOUD_RUN = "cloud_run"
    CLOUD_BUILD = "cloud_build"
    CLOUD_FUNCTIONS = "cloud_functions"
    GCE = "gce"
    GKE = "gke"
    APP_ENGINE = "app_engine"


# Mapping to GCP resource types and label fields
SERVICE_CONFIG: Dict[ServiceType, Dict[str, any]] = {
    ServiceType.CLOUD_RUN: {
        "resource_type": "cloud_run_revision",
        "filter_variations": [
            'resource.labels.service_name = "{service_name}"',
            'resource.labels.configuration_name = "{service_name}"'
        ]
    },
    ServiceType.CLOUD_BUILD: {
        "resource_type": "build",
        "filter_variations": [
            'resource.labels.build_id = "{service_name}"',
            'resource.labels.build_trigger_id = "{service_name}"',
            'logName="projects/{project_id}/logs/cloudbuild"'
        ]
    },
    ServiceType.CLOUD_FUNCTIONS: {
        "resource_type": "cloud_function",
        "filter_variations": [
            'resource.labels.function_name = "{service_name}"'
        ]
    },
    ServiceType.GCE: {
        "resource_type": "gce_instance",
        "filter_variations": [
            'resource.labels.instance_id = "{service_name}"',
            'labels.instance_name = "{service_name}"'
        ]
    },
    ServiceType.GKE: {
        "resource_type": "k8s_container",
        "filter_variations": [
            'resource.labels.cluster_name = "{service_name}"',
            'resource.labels.namespace_name = "{service_name}"',
            'resource.labels.pod_name = "{service_name}"'
        ]
    },
    ServiceType.APP_ENGINE: {
        "resource_type": "gae_app",
        "filter_variations": [
            'resource.labels.module_id = "{service_name}"',
            'resource.labels.version_id = "{service_name}"'
        ]
    }
}
