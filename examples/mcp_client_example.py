"""
Example script demonstrating GitHub MCP client usage.

This script shows how to:
1. Initialize the MCP client
2. List available tools from the MCP server
3. Perform common GitHub operations (create issue, list issues, create PR)
4. Use the client with context manager

Before running this script:
1. Set GITHUB_TOKEN environment variable with your GitHub Personal Access Token
2. Optionally set GITHUB_MCP_SERVER_URL (defaults to https://api.githubcopilot.com/mcp)
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.clients.github_mcp_client import GitHubMCPClient, create_github_mcp_client

# Load environment variables
load_dotenv()


def example_basic_usage():
    """Example: Basic client initialization and usage."""
    print("=" * 60)
    print("Example 1: Basic Client Usage")
    print("=" * 60)

    # Create and initialize client
    server_url = os.environ.get(
        "GITHUB_MCP_SERVER_URL",
        "https://api.githubcopilot.com/mcp"
    )

    print(f"\nConnecting to MCP server: {server_url}")

    try:
        client = create_github_mcp_client(server_url=server_url)
        print("✓ Client initialized successfully")

        # Close the client
        client.close()
        print("✓ Client closed")

    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nNote: The remote MCP server may not be publicly accessible.")
        print("This is expected if the server requires special authentication")
        print("or is only available to GitHub Copilot.")


def example_list_tools():
    """Example: List available tools from the MCP server."""
    print("\n" + "=" * 60)
    print("Example 2: List Available Tools")
    print("=" * 60)

    try:
        client = create_github_mcp_client()

        print("\nFetching available tools from MCP server...")
        tools = client.list_tools()

        print(f"\n✓ Found {len(tools)} available tools:\n")

        for tool in tools:
            print(f"  • {tool.name}")
            print(f"    {tool.description}")
            print()

        client.close()

    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nNote: This may fail if the server is not accessible.")


def example_with_context_manager():
    """Example: Using the client with context manager."""
    print("\n" + "=" * 60)
    print("Example 3: Using Context Manager")
    print("=" * 60)

    try:
        print("\nInitializing client with context manager...")

        with GitHubMCPClient() as client:
            print("✓ Client initialized")

            # Example: List issues in a repository
            owner = "octocat"
            repo = "Hello-World"

            print(f"\nListing issues in {owner}/{repo}...")
            issues = client.list_issues(owner=owner, repo=repo, state="open")

            print(f"✓ Found {len(issues)} open issues")

            if issues:
                print("\nFirst issue:")
                print(json.dumps(issues[0], indent=2))

        print("\n✓ Client closed automatically")

    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nNote: This may fail if the server is not accessible")
        print("or if you don't have access to the repository.")


def example_create_issue():
    """Example: Create a GitHub issue."""
    print("\n" + "=" * 60)
    print("Example 4: Create GitHub Issue")
    print("=" * 60)

    # THIS IS A DRY RUN - uncomment to actually create an issue
    print("\n⚠️  This example is commented out to avoid creating real issues.")
    print("Uncomment the code in the script to test issue creation.")

    example_code = '''
    try:
        with GitHubMCPClient() as client:
            result = client.create_issue(
                owner="your-username",
                repo="your-repo",
                title="Test issue from MCP client",
                body="This issue was created using the GitHub MCP client.",
                labels=["bug", "test"]
            )

            print("✓ Issue created successfully")
            print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"✗ Error: {e}")
    '''

    print("\nExample code:")
    print(example_code)


def example_langchain_tools():
    """Example: Using LangChain tool wrappers."""
    print("\n" + "=" * 60)
    print("Example 5: LangChain Tool Wrappers")
    print("=" * 60)

    print("\nThe MCP client can be used with LangChain tools for agent integration.")
    print("\nAvailable tool wrappers (in src/tools/github_mcp_tools.py):")
    print("  • mcp_create_github_issue")
    print("  • mcp_list_github_issues")
    print("  • mcp_create_pull_request")
    print("  • mcp_get_file_contents")
    print("  • mcp_search_code")
    print("  • mcp_list_available_tools")

    print("\nExample usage with LangChain:")

    example_code = '''
    from src.tools.github_mcp_tools import ALL_MCP_TOOLS
    from langchain.agents import initialize_agent, AgentType
    from langchain_google_genai import ChatGoogleGenerativeAI

    # Initialize LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    # Create agent with MCP tools
    agent = initialize_agent(
        tools=ALL_MCP_TOOLS,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    # Use the agent
    result = agent.run(
        "List all open issues in the repository https://github.com/octocat/Hello-World"
    )
    '''

    print(example_code)


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("GitHub MCP Client Examples")
    print("=" * 60)

    # Check for required environment variables
    if not os.environ.get("GITHUB_TOKEN"):
        print("\n⚠️  WARNING: GITHUB_TOKEN environment variable is not set.")
        print("Some examples will fail without it.")
        print("\nTo set it:")
        print("  export GITHUB_TOKEN='your_github_personal_access_token'")
        print()

    # Run examples
    example_basic_usage()
    # example_list_tools()  # Uncomment to test
    # example_with_context_manager()  # Uncomment to test
    example_create_issue()
    example_langchain_tools()

    print("\n" + "=" * 60)
    print("Examples completed")
    print("=" * 60)

    print("\n\nIMPORTANT NOTES:")
    print("-" * 60)
    print("1. The remote MCP server at https://api.githubcopilot.com/mcp")
    print("   may not be publicly accessible or may require special authentication.")
    print()
    print("2. If you encounter connection errors, this is expected and indicates")
    print("   the server is not publicly available or requires GitHub Copilot")
    print("   subscription authentication.")
    print()
    print("3. The MCP client implementation follows the Model Context Protocol")
    print("   specification and will work with any MCP-compliant server.")
    print()
    print("4. For production use, you may need to:")
    print("   - Use a different MCP server URL")
    print("   - Set up local MCP server using @modelcontextprotocol/server-github")
    print("   - Implement additional authentication mechanisms")
    print()
    print("5. See README_MCP.md for more detailed documentation.")
    print("-" * 60)


if __name__ == "__main__":
    main()
