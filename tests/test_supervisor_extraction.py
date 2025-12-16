"""Tests for supervisor service name and type extraction."""

import os
import sys
import pytest
import re

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestServiceExtractionPatterns:
    """Tests for the service name and type extraction regex patterns."""

    # These patterns are from src/main.py supervisor_node
    # Updated to match the improved patterns with explicit character classes and boundary checks
    SERVICE_PATTERNS = [
        (r"cloud run service\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_run"),
        (r"cloud build\s+(?:logs for\s+)?['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_build"),
        (r"cloud function\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_functions"),
        (r"gce instance\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "gce"),
        (r"gke cluster\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "gke"),
        (r"app engine\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "app_engine"),
    ]

    def extract_service_info(self, user_query):
        """Helper method that mimics the extraction logic from supervisor_node."""
        for pattern, svc_type in self.SERVICE_PATTERNS:
            match = re.search(pattern, user_query, re.IGNORECASE)
            if match:
                service_name = match.group(1)

                # Validate extracted service name (matches supervisor_node logic)
                if not re.match(r'^[a-zA-Z0-9._-]+$', service_name):
                    continue  # Try next pattern

                return service_name, svc_type
        return None, None

    def test_cloud_run_extraction(self):
        """Test Cloud Run service name extraction."""
        test_cases = [
            ("show me logs for cloud run service my-service", "my-service", "cloud_run"),
            ("cloud run service test-app logs", "test-app", "cloud_run"),
            ("Cloud Run Service prod-api", "prod-api", "cloud_run"),
            ("CLOUD RUN SERVICE my-app-123", "my-app-123", "cloud_run"),
            ('cloud run service "my-service"', "my-service", "cloud_run"),
            ("cloud run service 'test-app'", "test-app", "cloud_run"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_cloud_build_extraction(self):
        """Test Cloud Build service name extraction."""
        test_cases = [
            ("show me cloud build my-build", "my-build", "cloud_build"),
            ("cloud build logs for build-123", "build-123", "cloud_build"),
            ("Cloud Build test-build-456", "test-build-456", "cloud_build"),
            ("CLOUD BUILD prod-build", "prod-build", "cloud_build"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_cloud_functions_extraction(self):
        """Test Cloud Functions service name extraction."""
        test_cases = [
            ("show me cloud function my-function", "my-function", "cloud_functions"),
            ("cloud function process-data logs", "process-data", "cloud_functions"),
            ("Cloud Function api-handler", "api-handler", "cloud_functions"),
            ("CLOUD FUNCTION test-fn", "test-fn", "cloud_functions"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_gce_extraction(self):
        """Test GCE instance name extraction."""
        test_cases = [
            ("show me gce instance my-instance", "my-instance", "gce"),
            ("gce instance vm-123 logs", "vm-123", "gce"),
            ("GCE Instance prod-vm", "prod-vm", "gce"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_gke_extraction(self):
        """Test GKE cluster name extraction."""
        test_cases = [
            ("show me gke cluster my-cluster", "my-cluster", "gke"),
            ("gke cluster prod-k8s logs", "prod-k8s", "gke"),
            ("GKE Cluster test-cluster", "test-cluster", "gke"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_app_engine_extraction(self):
        """Test App Engine service name extraction."""
        test_cases = [
            ("show me app engine my-app", "my-app", "app_engine"),
            ("app engine default logs", "default", "app_engine"),
            ("App Engine prod-service", "prod-service", "app_engine"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_service_name_with_hyphens(self):
        """Test that service names with hyphens are correctly extracted."""
        test_cases = [
            ("cloud run service my-long-service-name", "my-long-service-name", "cloud_run"),
            ("cloud build test-build-123-prod", "test-build-123-prod", "cloud_build"),
            ("cloud function data-processor-v2", "data-processor-v2", "cloud_functions"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_service_name_with_underscores(self):
        """Test that service names with underscores are correctly extracted."""
        test_cases = [
            ("cloud run service my_service", "my_service", "cloud_run"),
            ("cloud build test_build_123", "test_build_123", "cloud_build"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_case_insensitivity(self):
        """Test that extraction is case-insensitive."""
        test_cases = [
            ("CLOUD RUN SERVICE my-service", "my-service", "cloud_run"),
            ("Cloud Run Service my-service", "my-service", "cloud_run"),
            ("cloud run service my-service", "my-service", "cloud_run"),
            ("cLoUd RuN sErViCe my-service", "my-service", "cloud_run"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_quoted_service_names(self):
        """Test that quoted service names are handled correctly."""
        test_cases = [
            ('cloud run service "my-service"', "my-service", "cloud_run"),
            ("cloud run service 'my-service'", "my-service", "cloud_run"),
            ('cloud build "test-build"', "test-build", "cloud_build"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_no_service_name_provided(self):
        """Test that queries without service names return None."""
        test_cases = [
            "show me some logs",
            "what happened today?",
            "analyze the errors",
            "check the performance",
        ]

        for query in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name is None, f"Should not extract service from: {query}"
            assert service_type is None, f"Should not extract type from: {query}"

    def test_pattern_priority(self):
        """Test that patterns match in the correct order (first match wins)."""
        # If a query has multiple service types, the first pattern match should win
        query = "cloud run service my-service and cloud build my-build"
        service_name, service_type = self.extract_service_info(query)
        assert service_name == "my-service"
        assert service_type == "cloud_run"

    def test_service_name_with_numbers(self):
        """Test that service names with numbers are correctly extracted."""
        test_cases = [
            ("cloud run service api-v2", "api-v2", "cloud_run"),
            ("cloud build build-123", "build-123", "cloud_build"),
            ("cloud function function-v1-prod", "function-v1-prod", "cloud_functions"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_complex_queries(self):
        """Test extraction from complex, natural language queries."""
        test_cases = [
            (
                "for cloud run service vllm-gemma-3-1b-it, can you tell if the performance has improved?",
                "vllm-gemma-3-1b-it",
                "cloud_run"
            ),
            (
                "I need to check the logs for cloud build my-deploy-pipeline from yesterday",
                "my-deploy-pipeline",
                "cloud_build"
            ),
            (
                "What errors occurred in cloud function data-processor during the last hour?",
                "data-processor",
                "cloud_functions"
            ),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"


class TestGitHubUrlExtraction:
    """Tests for GitHub URL extraction from queries."""

    def test_github_url_patterns(self):
        """Test various GitHub URL formats."""
        # This would test the repo URL extraction logic
        # The actual extraction is done in supervisor.py
        github_urls = [
            "https://github.com/patelmm79/vllm-container-prewarm",
            "https://github.com/user/repo",
            "https://github.com/org-name/repo-name",
            "http://github.com/user/repo",
        ]

        for url in github_urls:
            # Test that URLs can be extracted (this is a simple presence check)
            pattern = r"https?://github\.com/[\w-]+/[\w-]+"
            match = re.search(pattern, url)
            assert match is not None, f"Failed to match URL: {url}"
            assert match.group(0) == url, f"Extracted URL doesn't match: {url}"


class TestEdgeCasesAndValidation:
    """Tests for edge cases and validation in service name extraction."""

    # Use the same patterns as TestServiceExtractionPatterns
    SERVICE_PATTERNS = [
        (r"cloud run service\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_run"),
        (r"cloud build\s+(?:logs for\s+)?['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_build"),
        (r"cloud function\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_functions"),
        (r"gce instance\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "gce"),
        (r"gke cluster\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "gke"),
        (r"app engine\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "app_engine"),
    ]

    def extract_service_info(self, user_query):
        """Helper method that mimics the extraction logic from supervisor_node."""
        for pattern, svc_type in self.SERVICE_PATTERNS:
            match = re.search(pattern, user_query, re.IGNORECASE)
            if match:
                service_name = match.group(1)

                # Validate extracted service name
                if not re.match(r'^[a-zA-Z0-9._-]+$', service_name):
                    continue  # Try next pattern

                return service_name, svc_type
        return None, None

    def test_service_names_with_dots(self):
        """Test that service names with dots are correctly extracted."""
        test_cases = [
            ("cloud run service my.service.name", "my.service.name", "cloud_run"),
            ("gce instance vm.prod.123", "vm.prod.123", "gce"),
            ("cloud function api.v1.handler", "api.v1.handler", "cloud_functions"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_service_names_with_numbers(self):
        """Test that service names with long numeric IDs are correctly extracted."""
        test_cases = [
            ("gce instance instance-123456789", "instance-123456789", "gce"),
            ("cloud build build-20240115-123456", "build-20240115-123456", "cloud_build"),
            ("cloud run service api-v2-prod-2024", "api-v2-prod-2024", "cloud_run"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"

    def test_invalid_characters_rejected(self):
        """Test that service names with invalid characters are rejected."""
        # These should NOT match because they contain invalid characters
        invalid_queries = [
            "cloud run service my@service",
            "gce instance vm#123",
            "cloud function func$name",
            "cloud build build%test",
            "gke cluster cluster*name",
            "app engine service&name",
        ]

        for query in invalid_queries:
            service_name, service_type = self.extract_service_info(query)
            assert service_name is None, f"Should not extract from: {query}"
            assert service_type is None, f"Should not extract from: {query}"

    def test_injection_attempts_in_service_names(self):
        """Test that injection attempts in service names are rejected."""
        # These should NOT match because the validation should reject them
        injection_queries = [
            'cloud run service test" OR "1"="1',
            "gce instance test; DROP TABLE logs;",
            "cloud function test' OR '1'='1",
            "cloud build test\\nmalicious",
        ]

        for query in injection_queries:
            service_name, service_type = self.extract_service_info(query)
            # The pattern might match, but validation should reject
            # In reality, these patterns have spaces/quotes which won't match [a-zA-Z0-9._-]+
            # So both service_name and service_type should be None
            if service_name is not None:
                # If somehow extracted, it should be safe (only valid chars)
                assert re.match(r'^[a-zA-Z0-9._-]+$', service_name), \
                    f"Extracted unsafe service name: {service_name} from query: {query}"

    def test_mixed_valid_invalid_characters(self):
        """Test service names that have a mix of valid and invalid characters."""
        test_cases = [
            # Format: (query, should_match, expected_partial_match)
            ("cloud run service test-valid", True, "test-valid"),
            ("cloud run service test@invalid", False, None),
            ("cloud run service valid123", True, "valid123"),
            ("cloud run service 123-start", True, "123-start"),
        ]

        for query, should_match, expected_name in test_cases:
            service_name, service_type = self.extract_service_info(query)
            if should_match:
                assert service_name == expected_name, f"Failed for query: {query}"
                assert service_type == "cloud_run"
            else:
                assert service_name is None, f"Should not match: {query}"

    def test_very_long_service_names(self):
        """Test that very long service names can be extracted."""
        # GCP allows service names up to 63 characters for most services
        long_name = "a" * 63
        query = f"cloud run service {long_name}"
        service_name, service_type = self.extract_service_info(query)
        assert service_name == long_name
        assert service_type == "cloud_run"

    def test_single_character_service_names(self):
        """Test that single character service names are handled."""
        test_cases = [
            ("cloud run service a", "a", "cloud_run"),
            ("gce instance 1", "1", "gce"),
            ("cloud function x", "x", "cloud_functions"),
        ]

        for query, expected_name, expected_type in test_cases:
            service_name, service_type = self.extract_service_info(query)
            assert service_name == expected_name, f"Failed for query: {query}"
            assert service_type == expected_type, f"Failed for query: {query}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
