"""
Basic test to validate MCP client structure.
This doesn't require actual connection to the remote server.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from src.clients.github_mcp_client import GitHubMCPClient, create_github_mcp_client
        print("✓ MCP client imports successful")
    except ImportError as e:
        print(f"✗ Failed to import MCP client: {e}")
        return False

    try:
        from src.tools.github_mcp_tools import (
            mcp_create_github_issue,
            mcp_list_github_issues,
            mcp_create_pull_request,
            mcp_get_file_contents,
            mcp_search_code,
            mcp_list_available_tools,
            ALL_MCP_TOOLS
        )
        print("✓ MCP tools imports successful")
    except ImportError as e:
        print(f"✗ Failed to import MCP tools: {e}")
        return False

    return True


def test_client_initialization():
    """Test client can be initialized (without connecting)."""
    print("\nTesting client initialization...")

    try:
        from src.clients.github_mcp_client import GitHubMCPClient

        # Test with dummy token (won't connect)
        client = GitHubMCPClient(
            server_url="https://api.githubcopilot.com/mcp",
            github_token="test_token_12345"
        )

        print("✓ Client object created successfully")
        print(f"  Server URL: {client.server_url}")
        print(f"  Has token: {bool(client.github_token)}")
        print(f"  Session configured: {bool(client.session)}")

        return True

    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        return False


def test_tool_structure():
    """Test that tools have correct structure."""
    print("\nTesting tool structure...")

    try:
        from src.tools.github_mcp_tools import ALL_MCP_TOOLS

        print(f"✓ Found {len(ALL_MCP_TOOLS)} tools")

        for tool in ALL_MCP_TOOLS:
            print(f"  • {tool.name}")
            # Check tool has required attributes
            assert hasattr(tool, 'name'), f"Tool missing 'name' attribute"
            assert hasattr(tool, 'description'), f"Tool missing 'description' attribute"

        print("✓ All tools have correct structure")
        return True

    except Exception as e:
        print(f"✗ Failed to validate tools: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Client Basic Structure Tests")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Client Initialization", test_client_initialization()))
    results.append(("Tool Structure", test_tool_structure()))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nNote: These tests only validate structure.")
        print("Actual connectivity requires a running MCP server")
        print("and valid GitHub token.")
    else:
        print("✗ Some tests failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
