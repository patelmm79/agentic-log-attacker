"""
GitHub MCP (Model Context Protocol) Client

This module provides a client for connecting to GitHub's MCP server.
The MCP server exposes GitHub API functionality through a standardized protocol.

Authentication is done via GitHub Personal Access Token (PAT).
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents a tool available from the MCP server."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class GitHubMCPClient:
    """
    Client for connecting to GitHub's MCP server.

    The Model Context Protocol (MCP) is a standardized way for AI models to interact
    with external tools and services. This client connects to a remote MCP server
    that exposes GitHub API functionality.

    Authentication is performed using a GitHub Personal Access Token (PAT).
    """

    def __init__(
        self,
        server_url: str = "https://api.githubcopilot.com/mcp",
        github_token: Optional[str] = None
    ):
        """
        Initialize the GitHub MCP client.

        Args:
            server_url: The URL of the MCP server (default: GitHub Copilot MCP endpoint)
            github_token: GitHub Personal Access Token for authentication.
                         If not provided, will use GITHUB_TOKEN environment variable.
        """
        self.server_url = server_url.rstrip('/')
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")

        if not self.github_token:
            raise ValueError(
                "GitHub token is required. Provide it via github_token parameter "
                "or set GITHUB_TOKEN environment variable."
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.github_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        self._request_id = 0
        self._available_tools: Optional[List[MCPTool]] = None

        logger.info(f"Initialized GitHub MCP client for server: {self.server_url}")

    def _next_request_id(self) -> int:
        """Generate the next request ID for JSON-RPC."""
        self._request_id += 1
        return self._request_id

    def _make_jsonrpc_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a JSON-RPC 2.0 request to the MCP server.

        Args:
            method: The JSON-RPC method name
            params: Optional parameters for the method

        Returns:
            The result from the JSON-RPC response

        Raises:
            Exception: If the request fails or returns an error
        """
        request_payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }

        if params is not None:
            request_payload["params"] = params

        logger.debug(f"Making JSON-RPC request: {method}")

        try:
            response = self.session.post(
                self.server_url,
                json=request_payload,
                timeout=30
            )
            response.raise_for_status()

            response_data = response.json()

            if "error" in response_data:
                error = response_data["error"]
                raise Exception(
                    f"MCP server error: {error.get('message', 'Unknown error')} "
                    f"(code: {error.get('code')})"
                )

            return response_data.get("result", {})

        except requests.RequestException as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise Exception(f"MCP server connection failed: {e}")

    def initialize(self) -> Dict[str, Any]:
        """
        Initialize the MCP session.

        This should be called once when starting to use the client.
        It performs the MCP handshake and retrieves server capabilities.

        Returns:
            Server capabilities and initialization info
        """
        logger.info("Initializing MCP session...")

        result = self._make_jsonrpc_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "agentic-log-attacker",
                    "version": "1.0.0"
                }
            }
        )

        logger.info("MCP session initialized successfully")
        return result

    def list_tools(self) -> List[MCPTool]:
        """
        List all available tools from the MCP server.

        Returns:
            List of available tools with their schemas
        """
        logger.info("Fetching available tools from MCP server...")

        result = self._make_jsonrpc_request("tools/list")

        tools = []
        for tool_data in result.get("tools", []):
            tool = MCPTool(
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {})
            )
            tools.append(tool)

        self._available_tools = tools
        logger.info(f"Found {len(tools)} available tools")

        return tools

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            The result from the tool execution
        """
        logger.info(f"Calling tool: {tool_name}")
        logger.debug(f"Tool arguments: {arguments}")

        result = self._make_jsonrpc_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments
            }
        )

        # MCP returns results in a content array
        content = result.get("content", [])

        if not content:
            return None

        # Extract text content
        if len(content) == 1 and content[0].get("type") == "text":
            return content[0].get("text")

        # Return full content array if multiple items
        return content

    def get_available_tools(self) -> List[MCPTool]:
        """
        Get the list of available tools (cached).

        If tools haven't been fetched yet, this will fetch them.

        Returns:
            List of available tools
        """
        if self._available_tools is None:
            self.list_tools()

        return self._available_tools or []

    # Convenience methods for common GitHub operations

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue.

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: Optional list of label names
            assignees: Optional list of assignee usernames

        Returns:
            Created issue data
        """
        arguments = {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body
        }

        if labels:
            arguments["labels"] = labels
        if assignees:
            arguments["assignees"] = assignees

        return self.call_tool("create_issue", arguments)

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Dict[str, Any]:
        """
        Create a GitHub pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            body: PR body
            head: Branch name containing the changes
            base: Base branch to merge into (default: main)

        Returns:
            Created pull request data
        """
        return self.call_tool("create_pull_request", {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body,
            "head": head,
            "base": base
        })

    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open"
    ) -> List[Dict[str, Any]]:
        """
        List issues in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)

        Returns:
            List of issues
        """
        result = self.call_tool("list_issues", {
            "owner": owner,
            "repo": repo,
            "state": state
        })

        # Parse the result if it's JSON text
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return []

        return result if isinstance(result, list) else []

    def get_file_contents(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None
    ) -> str:
        """
        Get contents of a file from a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in the repository
            ref: Optional git reference (branch, tag, commit)

        Returns:
            File contents as string
        """
        arguments = {
            "owner": owner,
            "repo": repo,
            "path": path
        }

        if ref:
            arguments["ref"] = ref

        return self.call_tool("get_file_contents", arguments)

    def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update a file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in the repository
            content: File content (will be base64 encoded by the server)
            message: Commit message
            branch: Branch to commit to
            sha: Required if updating an existing file (current file SHA)

        Returns:
            Commit data
        """
        arguments = {
            "owner": owner,
            "repo": repo,
            "path": path,
            "content": content,
            "message": message,
            "branch": branch
        }

        if sha:
            arguments["sha"] = sha

        return self.call_tool("create_or_update_file", arguments)

    def search_code(
        self,
        query: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for code across GitHub.

        Args:
            query: Search query
            owner: Optional repository owner to limit search
            repo: Optional repository name to limit search

        Returns:
            List of search results
        """
        arguments = {"query": query}

        if owner and repo:
            arguments["query"] = f"{query} repo:{owner}/{repo}"

        result = self.call_tool("search_code", arguments)

        # Parse the result if it's JSON text
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return []

        return result if isinstance(result, list) else []

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("Closed GitHub MCP client session")

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_github_mcp_client(
    server_url: str = "https://api.githubcopilot.com/mcp",
    github_token: Optional[str] = None
) -> GitHubMCPClient:
    """
    Factory function to create and initialize a GitHub MCP client.

    Args:
        server_url: The URL of the MCP server
        github_token: GitHub Personal Access Token

    Returns:
        Initialized GitHubMCPClient instance
    """
    client = GitHubMCPClient(server_url=server_url, github_token=github_token)
    client.initialize()
    return client
