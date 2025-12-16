"""Tests for service type definitions and multi-service support."""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.service_types import ServiceType, SERVICE_CONFIG
from src.tools.gcp_logging_tool import get_gcp_logs, sanitize_identifier, build_filter_variations


class TestServiceTypeEnum:
    """Tests for the ServiceType enum."""

    def test_service_type_values(self):
        """Test that all expected service types exist with correct values."""
        assert ServiceType.CLOUD_RUN.value == "cloud_run"
        assert ServiceType.CLOUD_BUILD.value == "cloud_build"
        assert ServiceType.CLOUD_FUNCTIONS.value == "cloud_functions"
        assert ServiceType.GCE.value == "gce"
        assert ServiceType.GKE.value == "gke"
        assert ServiceType.APP_ENGINE.value == "app_engine"

    def test_service_type_count(self):
        """Test that we have exactly 6 service types."""
        assert len(ServiceType) == 6

    def test_service_type_string_conversion(self):
        """Test that service types can be created from strings."""
        assert ServiceType("cloud_run") == ServiceType.CLOUD_RUN
        assert ServiceType("cloud_build") == ServiceType.CLOUD_BUILD
        assert ServiceType("cloud_functions") == ServiceType.CLOUD_FUNCTIONS
        assert ServiceType("gce") == ServiceType.GCE
        assert ServiceType("gke") == ServiceType.GKE
        assert ServiceType("app_engine") == ServiceType.APP_ENGINE

    def test_invalid_service_type(self):
        """Test that invalid service type strings raise ValueError."""
        with pytest.raises(ValueError):
            ServiceType("invalid_service")


class TestServiceConfig:
    """Tests for the SERVICE_CONFIG dictionary."""

    def test_all_service_types_have_config(self):
        """Ensure all service types have configurations."""
        for service_type in ServiceType:
            assert service_type in SERVICE_CONFIG, f"Missing config for {service_type}"

    def test_config_structure(self):
        """Test that each config has required fields."""
        for service_type, config in SERVICE_CONFIG.items():
            assert "resource_type" in config, f"Missing resource_type for {service_type}"
            assert "filter_variations" in config, f"Missing filter_variations for {service_type}"
            assert isinstance(config["resource_type"], str), f"resource_type must be string for {service_type}"
            assert isinstance(config["filter_variations"], list), f"filter_variations must be list for {service_type}"
            assert len(config["filter_variations"]) > 0, f"filter_variations cannot be empty for {service_type}"

    def test_cloud_run_config(self):
        """Test Cloud Run specific configuration."""
        config = SERVICE_CONFIG[ServiceType.CLOUD_RUN]
        assert config["resource_type"] == "cloud_run_revision"
        assert len(config["filter_variations"]) == 2
        assert 'resource.labels.service_name = "{service_name}"' in config["filter_variations"]
        assert 'resource.labels.configuration_name = "{service_name}"' in config["filter_variations"]

    def test_cloud_build_config(self):
        """Test Cloud Build specific configuration."""
        config = SERVICE_CONFIG[ServiceType.CLOUD_BUILD]
        assert config["resource_type"] == "build"
        assert len(config["filter_variations"]) == 3
        assert any("build_id" in var for var in config["filter_variations"])

    def test_cloud_functions_config(self):
        """Test Cloud Functions specific configuration."""
        config = SERVICE_CONFIG[ServiceType.CLOUD_FUNCTIONS]
        assert config["resource_type"] == "cloud_function"
        assert any("function_name" in var for var in config["filter_variations"])

    def test_gce_config(self):
        """Test GCE specific configuration."""
        config = SERVICE_CONFIG[ServiceType.GCE]
        assert config["resource_type"] == "gce_instance"
        assert any("instance_id" in var for var in config["filter_variations"])

    def test_gke_config(self):
        """Test GKE specific configuration."""
        config = SERVICE_CONFIG[ServiceType.GKE]
        assert config["resource_type"] == "k8s_container"
        assert any("cluster_name" in var for var in config["filter_variations"])

    def test_app_engine_config(self):
        """Test App Engine specific configuration."""
        config = SERVICE_CONFIG[ServiceType.APP_ENGINE]
        assert config["resource_type"] == "gae_app"
        assert any("module_id" in var for var in config["filter_variations"])

    def test_filter_placeholders(self):
        """Test that filter variations contain expected placeholders."""
        for service_type, config in SERVICE_CONFIG.items():
            for filter_var in config["filter_variations"]:
                # Most filters should have {service_name} placeholder
                # Some Cloud Build filters might only have {project_id}
                assert "{service_name}" in filter_var or "{project_id}" in filter_var, \
                    f"Filter variation missing placeholders for {service_type}: {filter_var}"


class TestSanitizeIdentifier:
    """Tests for the sanitize_identifier function."""

    def test_valid_identifiers(self):
        """Test that valid identifiers pass through unchanged."""
        valid_identifiers = [
            "my-service",
            "my_service",
            "my-service-123",
            "my.service.name",
            "project-123",
            "test123",
            "a-b_c.d",
        ]
        for identifier in valid_identifiers:
            assert sanitize_identifier(identifier) == identifier

    def test_injection_attempts_rejected(self):
        """Test that SQL/filter injection attempts are rejected."""
        malicious_inputs = [
            'malicious" OR resource.labels.service_name != "',
            'test; DROP TABLE logs;--',
            'test" AND 1=1--',
            "test' OR '1'='1",
            'test" OR ""="',
            'test;--',
            'test OR 1=1',
            'test" OR resource.type != "',
            'test\\nAND severity >= ERROR',
            'test WHERE 1=1',
            'test) OR (1=1',
            'test"; system("rm -rf /")',
        ]
        for malicious_input in malicious_inputs:
            with pytest.raises(ValueError, match="Invalid"):
                sanitize_identifier(malicious_input)

    def test_empty_identifier_rejected(self):
        """Test that empty identifiers are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_identifier("")

    def test_whitespace_rejected(self):
        """Test that identifiers with spaces are rejected."""
        with pytest.raises(ValueError):
            sanitize_identifier("my service")
        with pytest.raises(ValueError):
            sanitize_identifier("my\tservice")
        with pytest.raises(ValueError):
            sanitize_identifier("my\nservice")

    def test_special_characters_rejected(self):
        """Test that special characters are rejected."""
        invalid_chars = ['@', '#', '$', '%', '^', '&', '*', '(', ')', '=', '+', '[', ']', '{', '}', '|', '\\', '/', '?', '<', '>', ',', ':', ';', '"', "'"]
        for char in invalid_chars:
            with pytest.raises(ValueError):
                sanitize_identifier(f"test{char}service")

    def test_length_limit(self):
        """Test that excessively long identifiers are rejected."""
        long_identifier = "a" * 256
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_identifier(long_identifier)

    def test_max_valid_length(self):
        """Test that identifiers at the maximum length are accepted."""
        max_length_identifier = "a" * 255
        assert sanitize_identifier(max_length_identifier) == max_length_identifier

    def test_custom_identifier_type_in_error(self):
        """Test that custom identifier_type appears in error messages."""
        with pytest.raises(ValueError, match="custom_field"):
            sanitize_identifier("", "custom_field")


class TestGetGcpLogsMultiService:
    """Tests for get_gcp_logs with different service types."""

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_cloud_run_service_type(self, mock_client_class):
        """Test get_gcp_logs with Cloud Run service type."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_entries.return_value = [Mock(payload="test log entry")]

        logs, page_token, error = get_gcp_logs("my-service", service_type="cloud_run", limit=10)

        assert error is None
        assert mock_client.list_entries.called
        call_filter = mock_client.list_entries.call_args[1]['filter_']
        assert "cloud_run_revision" in call_filter
        assert "my-service" in call_filter

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_cloud_build_service_type(self, mock_client_class):
        """Test get_gcp_logs with Cloud Build service type."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_entries.return_value = [Mock(payload="test log entry")]

        logs, page_token, error = get_gcp_logs("my-build", service_type="cloud_build", limit=10)

        assert error is None
        call_filter = mock_client.list_entries.call_args[1]['filter_']
        assert "build" in call_filter

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_cloud_functions_service_type(self, mock_client_class):
        """Test get_gcp_logs with Cloud Functions service type."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_entries.return_value = [Mock(payload="test log entry")]

        logs, page_token, error = get_gcp_logs("my-function", service_type="cloud_functions", limit=10)

        assert error is None
        call_filter = mock_client.list_entries.call_args[1]['filter_']
        assert "cloud_function" in call_filter

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    def test_invalid_service_type(self):
        """Test that invalid service type returns error."""
        logs, page_token, error = get_gcp_logs("my-service", service_type="invalid_type", limit=10)

        assert logs == ""
        assert error is not None
        assert "Unsupported service type" in str(error)

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    def test_malicious_service_name_rejected(self):
        """Test that malicious service names are rejected."""
        malicious_name = 'test" OR resource.type != "'

        logs, page_token, error = get_gcp_logs(malicious_name, service_type="cloud_run", limit=10)

        assert logs == ""
        assert error is not None
        assert "Invalid service_name" in str(error)

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_filter_variations_tried(self, mock_client_class):
        """Test that multiple filter variations are tried if first fails."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # First call returns empty, second call returns logs
        mock_client.list_entries.side_effect = [
            [],  # First variation returns nothing
            [Mock(payload="test log entry")]  # Second variation succeeds
        ]

        logs, page_token, error = get_gcp_logs("my-service", service_type="cloud_run", limit=10)

        assert error is None
        assert logs != ""
        assert mock_client.list_entries.call_count == 2

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_all_service_types_supported(self, mock_client_class):
        """Test that all service types from enum are supported."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_entries.return_value = [Mock(payload="test log entry")]

        for service_type in ServiceType:
            logs, page_token, error = get_gcp_logs(
                "test-service",
                service_type=service_type.value,
                limit=10
            )
            assert error is None, f"Service type {service_type.value} failed"


class TestServiceTypeIntegration:
    """Integration tests for service type functionality (require mocking)."""

    @pytest.mark.parametrize("service_type,expected_resource", [
        ("cloud_run", "cloud_run_revision"),
        ("cloud_build", "build"),
        ("cloud_functions", "cloud_function"),
        ("gce", "gce_instance"),
        ("gke", "k8s_container"),
        ("app_engine", "gae_app"),
    ])
    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_resource_type_in_filter(self, mock_client_class, service_type, expected_resource):
        """Test that correct resource type appears in generated filters."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_entries.return_value = [Mock(payload="test")]

        get_gcp_logs("test-service", service_type=service_type, limit=10)

        call_filter = mock_client.list_entries.call_args[1]['filter_']
        assert f'resource.type = "{expected_resource}"' in call_filter


class TestReturnTypeScenarios:
    """Tests for return type correctness and Optional handling."""

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_successful_return_types(self, mock_client_class):
        """Test that successful call returns correct types: (str, None, None)."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Create mock entries with proper __str__ method
        mock_entry1 = Mock()
        mock_entry1.__str__ = Mock(return_value="log entry 1")
        mock_entry2 = Mock()
        mock_entry2.__str__ = Mock(return_value="log entry 2")

        mock_client.list_entries.return_value = [mock_entry1, mock_entry2]

        logs, page_token, error = get_gcp_logs("my-service", service_type="cloud_run", limit=10)

        # Verify types
        assert isinstance(logs, str), "Logs should be a string"
        assert page_token is None, "Page token should be None for successful call without pagination"
        assert error is None, "Error should be None for successful call"
        assert "log entry 1" in logs
        assert "log entry 2" in logs

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    def test_error_return_types_invalid_service_type(self):
        """Test that error call returns correct types: (str, None, Exception)."""
        logs, page_token, error = get_gcp_logs("my-service", service_type="invalid", limit=10)

        # Verify types
        assert isinstance(logs, str), "Logs should be a string (empty on error)"
        assert logs == "", "Logs should be empty string on error"
        assert page_token is None, "Page token should be None on error"
        assert error is not None, "Error should not be None"
        assert isinstance(error, ValueError), "Error should be ValueError for invalid service type"

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    def test_error_return_types_invalid_service_name(self):
        """Test that sanitization error returns correct types: (str, None, ValueError)."""
        malicious_name = 'test" OR 1=1'

        logs, page_token, error = get_gcp_logs(malicious_name, service_type="cloud_run", limit=10)

        # Verify types
        assert isinstance(logs, str), "Logs should be a string"
        assert logs == "", "Logs should be empty on error"
        assert page_token is None, "Page token should be None on error"
        assert error is not None, "Error should not be None"
        assert isinstance(error, ValueError), "Error should be ValueError for invalid service name"
        assert "Invalid service_name" in str(error)

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_no_logs_found_return_types(self, mock_client_class):
        """Test that no logs found returns correct types: (str, None, None)."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        # Return empty list for all filter attempts (including 48h retry)
        mock_client.list_entries.return_value = []

        logs, page_token, error = get_gcp_logs("my-service", service_type="cloud_run", limit=10)

        # Verify types
        assert isinstance(logs, str), "Logs should be a string"
        assert logs == "", "Logs should be empty string when no logs found"
        assert page_token is None, "Page token should be None when no logs found"
        assert error is None, "Error should be None when no logs found (not an error condition)"

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_exception_during_fetch_return_types(self, mock_client_class):
        """Test that exception during fetch returns correct types: (str, None, Exception)."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        # Simulate an exception during log fetching
        mock_client.list_entries.side_effect = Exception("GCP API error")

        logs, page_token, error = get_gcp_logs("my-service", service_type="cloud_run", limit=10)

        # Verify types
        assert isinstance(logs, str), "Logs should be a string"
        assert logs == "", "Logs should be empty on exception"
        assert page_token is None, "Page token should be None on exception"
        assert error is not None, "Error should not be None"
        assert isinstance(error, Exception), "Error should be an Exception"
        assert "GCP API error" in str(error)

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch('src.tools.gcp_logging_tool.Client')
    def test_optional_parameters_accepted(self, mock_client_class):
        """Test that Optional parameters can be None."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_entries.return_value = [Mock(payload="test")]

        # Call with all optional parameters as None (explicit)
        logs, page_token, error = get_gcp_logs(
            "my-service",
            service_type="cloud_run",
            limit=10,
            page_token=None,
            start_time=None,
            end_time=None
        )

        assert error is None, "Should accept None for optional parameters"
        assert isinstance(logs, str)


class TestBuildFilterVariations:
    """Tests for the build_filter_variations helper function."""

    def test_build_single_filter_variation(self):
        """Test building a filter with a single variation."""
        config = {
            "resource_type": "cloud_run_revision",
            "filter_variations": [
                'resource.labels.service_name = "{service_name}"'
            ]
        }
        time_filter = ' AND timestamp >= "2024-01-01T00:00:00Z" AND timestamp <= "2024-01-01T23:59:59Z"'

        filters = build_filter_variations(config, "my-service", "my-project", time_filter)

        assert len(filters) == 1
        assert 'resource.type = "cloud_run_revision"' in filters[0]
        assert 'resource.labels.service_name = "my-service"' in filters[0]
        assert 'severity >= DEFAULT' in filters[0]
        assert time_filter.strip() in filters[0]

    def test_build_multiple_filter_variations(self):
        """Test building filters with multiple variations."""
        config = {
            "resource_type": "cloud_run_revision",
            "filter_variations": [
                'resource.labels.service_name = "{service_name}"',
                'resource.labels.configuration_name = "{service_name}"'
            ]
        }
        time_filter = ' AND timestamp >= "2024-01-01T00:00:00Z"'

        filters = build_filter_variations(config, "my-service", "my-project", time_filter)

        assert len(filters) == 2
        assert 'service_name = "my-service"' in filters[0]
        assert 'configuration_name = "my-service"' in filters[1]
        # Both should have the same resource type
        for f in filters:
            assert 'resource.type = "cloud_run_revision"' in f
            assert 'severity >= DEFAULT' in f

    def test_build_filters_with_project_id_placeholder(self):
        """Test building filters that use project_id placeholder."""
        config = {
            "resource_type": "build",
            "filter_variations": [
                'logName="projects/{project_id}/logs/cloudbuild"'
            ]
        }
        time_filter = ''

        filters = build_filter_variations(config, "my-build", "test-project", time_filter)

        assert len(filters) == 1
        assert 'logName="projects/test-project/logs/cloudbuild"' in filters[0]
        assert 'resource.type = "build"' in filters[0]

    def test_build_filters_with_empty_time_filter(self):
        """Test building filters with empty time filter."""
        config = {
            "resource_type": "cloud_function",
            "filter_variations": [
                'resource.labels.function_name = "{service_name}"'
            ]
        }

        filters = build_filter_variations(config, "my-function", "my-project", "")

        assert len(filters) == 1
        # Should end with DEFAULT (no time filter)
        assert filters[0].endswith('severity >= DEFAULT')

    def test_build_filters_for_all_service_types(self):
        """Test building filters for all configured service types."""
        for service_type, config in SERVICE_CONFIG.items():
            time_filter = ' AND timestamp >= "2024-01-01T00:00:00Z"'

            filters = build_filter_variations(config, "test-service", "test-project", time_filter)

            # Should have at least one filter
            assert len(filters) > 0, f"No filters generated for {service_type}"
            assert len(filters) == len(config["filter_variations"]), \
                f"Filter count mismatch for {service_type}"

            # All filters should contain the resource type
            for f in filters:
                assert f'resource.type = "{config["resource_type"]}"' in f
                assert 'severity >= DEFAULT' in f
                assert time_filter.strip() in f

    def test_filter_format_consistency(self):
        """Test that all generated filters follow the expected format."""
        config = SERVICE_CONFIG[ServiceType.CLOUD_RUN]
        time_filter = ' AND timestamp >= "2024-01-01T00:00:00Z"'

        filters = build_filter_variations(config, "my-service", "my-project", time_filter)

        for f in filters:
            # Check format: resource.type = "..." AND ... AND severity >= DEFAULT AND timestamp ...
            assert 'resource.type =' in f
            assert ' AND ' in f
            assert 'severity >= DEFAULT' in f
            # Verify no placeholder remains
            assert '{service_name}' not in f
            assert '{project_id}' not in f


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
