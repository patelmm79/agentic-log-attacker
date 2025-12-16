#!/usr/bin/env python3
"""
Test script for A2A endpoint integration with dev-nexus.

This script tests the A2A /execute endpoint by:
1. Getting an identity token from Google Cloud
2. Making an A2A skill request to the service
3. Verifying the response format
"""

import requests
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import json
import sys
import time


def get_identity_token(target_audience: str) -> str:
    """Get Google Cloud identity token for the current service account."""
    try:
        credentials, project = default()
        auth_req = Request()

        # Get ID token for the target audience
        token = id_token.fetch_id_token(auth_req, target_audience)
        return token
    except Exception as e:
        print(f"Error getting identity token: {e}")
        print("Make sure you have Application Default Credentials configured:")
        print("  gcloud auth application-default login")
        sys.exit(1)


def test_health_endpoint(service_url: str) -> bool:
    """Test the health check endpoint."""
    print("\n[1] Testing /health endpoint...")
    try:
        response = requests.get(f"{service_url}/health", timeout=10)
        response.raise_for_status()

        data = response.json()
        print(f"    Status: {data.get('status')}")
        print(f"    Version: {data.get('version')}")
        print(f"    Skills available: {data.get('available_skills')}")
        return True
    except Exception as e:
        print(f"    ✗ Health check failed: {e}")
        return False


def test_agent_metadata(service_url: str) -> bool:
    """Test the agent metadata endpoint."""
    print("\n[2] Testing /.well-known/agent.json endpoint...")
    try:
        response = requests.get(f"{service_url}/.well-known/agent.json", timeout=10)
        response.raise_for_status()

        data = response.json()
        print(f"    Agent name: {data.get('name')}")
        print(f"    Version: {data.get('version')}")
        print(f"    Skills: {[s['id'] for s in data.get('skills', [])]}")
        print(f"    Auth type: {data.get('authentication', {}).get('type')}")
        return True
    except Exception as e:
        print(f"    ✗ Agent metadata request failed: {e}")
        return False


def test_a2a_endpoint(service_url: str, token: str) -> bool:
    """Test the A2A /execute endpoint with authentication."""
    print("\n[3] Testing /a2a/execute endpoint with authentication...")

    payload = {
        "skill_id": "analyze_and_monitor_logs",
        "input": {
            "user_query": "review logs for cloud run service test-service",
            "service_name": "test-service",
            "service_type": "cloud_run",
            "repo_url": "https://github.com/test/repo"
        }
    }

    try:
        print(f"    Request: POST {service_url}/a2a/execute")
        print(f"    Skill: analyze_and_monitor_logs")
        print(f"    Service: test-service (cloud_run)")

        start_time = time.time()
        response = requests.post(
            f"{service_url}/a2a/execute",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=120
        )
        elapsed = time.time() - start_time

        print(f"    Response Status: {response.status_code}")
        print(f"    Response Time: {elapsed:.1f}s")

        if response.status_code == 200:
            data = response.json()
            print(f"    Success: {data.get('success')}")
            if data.get('success'):
                result = data.get('result', {})
                print(f"    Issues identified: {result.get('issues_identified', 0)}")
                print(f"    Issues created: {result.get('issues_created', 0)}")
                print(f"    Execution time: {data.get('execution_time_ms')}ms")
                return True
            else:
                print(f"    Error: {data.get('error')}")
                return False
        elif response.status_code == 401:
            print(f"    ✗ Unauthorized (401): Token validation failed")
            print(f"    Response: {response.json()}")
            return False
        elif response.status_code == 429:
            print(f"    ✗ Rate limit exceeded (429)")
            print(f"    Response: {response.json()}")
            return False
        else:
            print(f"    ✗ Request failed with status {response.status_code}")
            print(f"    Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"    ✗ Request timeout (120 seconds)")
        return False
    except Exception as e:
        print(f"    ✗ Request failed: {e}")
        return False


def test_unauthorized_access(service_url: str) -> bool:
    """Test that unauthorized requests are rejected."""
    print("\n[4] Testing unauthorized access rejection...")

    payload = {
        "skill_id": "analyze_and_monitor_logs",
        "input": {"user_query": "test"}
    }

    try:
        # Request without token
        response = requests.post(
            f"{service_url}/a2a/execute",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )

        if response.status_code == 401:
            print(f"    ✓ Correctly rejected unauthorized request (401)")
            return True
        else:
            print(f"    ✗ Expected 401, got {response.status_code}")
            return False

    except Exception as e:
        print(f"    ✗ Test failed: {e}")
        return False


def main():
    """Run all A2A endpoint tests."""
    print("=" * 50)
    print("A2A Endpoint Integration Tests")
    print("=" * 50)

    # Use default deployed URL or environment variable
    service_url = "https://agentic-log-attacker-665374072631.us-central1.run.app"
    print(f"\nTarget service: {service_url}")

    # Test 1: Health check (no auth required)
    health_ok = test_health_endpoint(service_url)

    # Test 2: Agent metadata (no auth required)
    metadata_ok = test_agent_metadata(service_url)

    # Test 3: Unauthorized access rejection
    unauth_ok = test_unauthorized_access(service_url)

    # Test 4: A2A endpoint with authentication
    print("\n[Getting authentication token...]")
    try:
        token = get_identity_token(service_url)
        print("    ✓ Successfully obtained identity token")
        a2a_ok = test_a2a_endpoint(service_url, token)
    except Exception as e:
        print(f"    ✗ Failed to get token: {e}")
        a2a_ok = False

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"Health check:        {'✓' if health_ok else '✗'}")
    print(f"Agent metadata:      {'✓' if metadata_ok else '✗'}")
    print(f"Auth rejection:      {'✓' if unauth_ok else '✗'}")
    print(f"A2A skill execution: {'✓' if a2a_ok else '✗'}")

    all_passed = all([health_ok, metadata_ok, unauth_ok, a2a_ok])

    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
