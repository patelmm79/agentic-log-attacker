"""
LangChain tool wrappers for GitHub MCP client.

This module provides LangChain-compatible tool wrappers around the GitHub MCP client,
making GitHub operations available to LangGraph agents.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from langchain.tools import tool

from src.clients.github_mcp_client import create_github_mcp_client

logger = logging.getLogger(__name__)

# Global client instance (initialized lazily)
_mcp_client = None


def get_mcp_client():
    """Get or create the global MCP client instance."""
    global _mcp_client

    if _mcp_client is None:
        server_url = os.environ.get(
            "GITHUB_MCP_SERVER_URL",
            "https://api.githubcopilot.com/mcp"
        )
        github_token = os.environ.get("GITHUB_TOKEN")

        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN environment variable is required for MCP client"
            )

        logger.info(f"Initializing GitHub MCP client for server: {server_url}")
        _mcp_client = create_github_mcp_client(
            server_url=server_url,
            github_token=github_token
        )
        logger.info("GitHub MCP client initialized successfully")

    return _mcp_client


@tool
def mcp_create_github_issue(
    repo_url: str,
    title: str,
    body: str,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None
) -> str:
    """
    Create a GitHub issue using the MCP server.

    Args:
        repo_url: Full GitHub repository URL (e.g., "https://github.com/owner/repo")
        title: Issue title
        body: Issue body/description
        labels: Optional list of label names
        assignees: Optional list of assignee usernames

    Returns:
        JSON string with created issue data
    """
    try:
        # Parse owner and repo from URL
        repo_url = repo_url.replace("https://github.com/", "").rstrip("/")
        parts = repo_url.split("/")

        if len(parts) != 2:
            return f"Error: Invalid repository URL format: {repo_url}"

        owner, repo = parts

        client = get_mcp_client()
        result = client.create_issue(
            owner=owner,
            repo=repo,
            title=title,
            body=body,
            labels=labels,
            assignees=assignees
        )

        logger.info(f"Created issue via MCP: {title}")
        return str(result)

    except Exception as e:
        error_msg = f"Error creating issue via MCP: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def mcp_list_github_issues(repo_url: str, state: str = "open") -> str:
    """
    List GitHub issues using the MCP server.

    Args:
        repo_url: Full GitHub repository URL (e.g., "https://github.com/owner/repo")
        state: Issue state - "open", "closed", or "all" (default: "open")

    Returns:
        JSON string with list of issues
    """
    try:
        # Parse owner and repo from URL
        repo_url = repo_url.replace("https://github.com/", "").rstrip("/")
        parts = repo_url.split("/")

        if len(parts) != 2:
            return f"Error: Invalid repository URL format: {repo_url}"

        owner, repo = parts

        client = get_mcp_client()
        result = client.list_issues(owner=owner, repo=repo, state=state)

        logger.info(f"Listed issues via MCP: {len(result)} issues found")
        return str(result)

    except Exception as e:
        error_msg = f"Error listing issues via MCP: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def mcp_create_pull_request(
    repo_url: str,
    title: str,
    body: str,
    head: str,
    base: str = "main"
) -> str:
    """
    Create a GitHub pull request using the MCP server.

    Args:
        repo_url: Full GitHub repository URL (e.g., "https://github.com/owner/repo")
        title: Pull request title
        body: Pull request body/description
        head: Branch name containing the changes
        base: Base branch to merge into (default: "main")

    Returns:
        JSON string with created pull request data
    """
    try:
        # Parse owner and repo from URL
        repo_url = repo_url.replace("https://github.com/", "").rstrip("/")
        parts = repo_url.split("/")

        if len(parts) != 2:
            return f"Error: Invalid repository URL format: {repo_url}"

        owner, repo = parts

        client = get_mcp_client()
        result = client.create_pull_request(
            owner=owner,
            repo=repo,
            title=title,
            body=body,
            head=head,
            base=base
        )

        logger.info(f"Created pull request via MCP: {title}")
        return str(result)

    except Exception as e:
        error_msg = f"Error creating pull request via MCP: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def mcp_get_file_contents(
    repo_url: str,
    file_path: str,
    ref: Optional[str] = None
) -> str:
    """
    Get contents of a file from a GitHub repository using the MCP server.

    Args:
        repo_url: Full GitHub repository URL (e.g., "https://github.com/owner/repo")
        file_path: Path to the file in the repository
        ref: Optional git reference (branch, tag, commit SHA)

    Returns:
        File contents as string
    """
    try:
        # Parse owner and repo from URL
        repo_url = repo_url.replace("https://github.com/", "").rstrip("/")
        parts = repo_url.split("/")

        if len(parts) != 2:
            return f"Error: Invalid repository URL format: {repo_url}"

        owner, repo = parts

        client = get_mcp_client()
        result = client.get_file_contents(
            owner=owner,
            repo=repo,
            path=file_path,
            ref=ref
        )

        logger.info(f"Retrieved file contents via MCP: {file_path}")
        return result

    except Exception as e:
        error_msg = f"Error getting file contents via MCP: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def mcp_search_code(
    query: str,
    repo_url: Optional[str] = None
) -> str:
    """
    Search for code in GitHub repositories using the MCP server.

    Args:
        query: Search query
        repo_url: Optional repository URL to limit search to specific repo

    Returns:
        JSON string with search results
    """
    try:
        client = get_mcp_client()

        if repo_url:
            # Parse owner and repo from URL
            repo_url = repo_url.replace("https://github.com/", "").rstrip("/")
            parts = repo_url.split("/")

            if len(parts) != 2:
                return f"Error: Invalid repository URL format: {repo_url}"

            owner, repo = parts
            result = client.search_code(query=query, owner=owner, repo=repo)
        else:
            result = client.search_code(query=query)

        logger.info(f"Searched code via MCP: {len(result)} results found")
        return str(result)

    except Exception as e:
        error_msg = f"Error searching code via MCP: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def mcp_list_available_tools() -> str:
    """
    List all available tools from the GitHub MCP server.

    This is useful for discovering what GitHub operations are available
    through the MCP server.

    Returns:
        JSON string with list of available tools and their descriptions
    """
    try:
        client = get_mcp_client()
        tools = client.list_tools()

        tools_info = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in tools
        ]

        logger.info(f"Listed {len(tools_info)} available MCP tools")
        return str(tools_info)

    except Exception as e:
        error_msg = f"Error listing MCP tools: {e}"
        logger.error(error_msg)
        return error_msg


# List of all MCP tools for easy import
ALL_MCP_TOOLS = [
    mcp_create_github_issue,
    mcp_list_github_issues,
    mcp_create_pull_request,
    mcp_get_file_contents,
    mcp_search_code,
    mcp_list_available_tools,
]
