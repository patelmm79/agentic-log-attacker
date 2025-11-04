# GitHub MCP Client Documentation

This document describes the GitHub MCP (Model Context Protocol) client implementation for connecting to remote MCP servers.

## Overview

The GitHub MCP client enables this application to interact with GitHub's API through a standardized MCP server. The Model Context Protocol (MCP) provides a uniform way for AI agents to access external tools and services.

## Architecture

```
┌─────────────────────┐
│   LangGraph Agent   │
│                     │
│  (Your AI Agents)   │
└──────────┬──────────┘
           │
           │ Uses LangChain Tools
           ▼
┌─────────────────────┐
│  MCP Tool Wrappers  │
│                     │
│ (github_mcp_tools)  │
└──────────┬──────────┘
           │
           │ Calls
           ▼
┌─────────────────────┐      JSON-RPC 2.0       ┌─────────────────────┐
│  GitHubMCPClient    │◄─────over HTTPS────────►│   Remote MCP        │
│                     │                          │   Server            │
│ (github_mcp_client) │      Authentication      │                     │
└─────────────────────┘      via GitHub PAT      └─────────────────────┘
```

## Components

### 1. GitHubMCPClient (`src/clients/github_mcp_client.py`)

The core MCP client that handles:
- Connection to remote MCP server via HTTPS
- JSON-RPC 2.0 protocol implementation
- Authentication using GitHub Personal Access Token (PAT)
- Tool discovery and execution
- Error handling and logging

**Key Features:**
- Context manager support for automatic cleanup
- Lazy initialization of tools
- Convenience methods for common GitHub operations
- Full JSON-RPC 2.0 compliance

### 2. LangChain Tool Wrappers (`src/tools/github_mcp_tools.py`)

LangChain-compatible tool wrappers that make MCP operations available to agents:
- `mcp_create_github_issue` - Create GitHub issues
- `mcp_list_github_issues` - List issues in a repository
- `mcp_create_pull_request` - Create pull requests
- `mcp_get_file_contents` - Read file contents from repositories
- `mcp_search_code` - Search code across GitHub
- `mcp_list_available_tools` - Discover available MCP tools

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# GitHub Personal Access Token (required)
GITHUB_TOKEN=ghp_your_github_personal_access_token

# GitHub repository (optional, for default operations)
GITHUB_REPOSITORY=owner/repo

# Remote MCP Server URL (optional, defaults to GitHub Copilot endpoint)
GITHUB_MCP_SERVER_URL=https://api.githubcopilot.com/mcp
```

### GitHub Personal Access Token (PAT)

The MCP client authenticates using a GitHub PAT. To create one:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes based on your needs:
   - `repo` - Full control of private repositories
   - `public_repo` - Access public repositories
   - `read:org` - Read org and team membership
   - `workflow` - Update GitHub Action workflows
4. Copy the token and set it as `GITHUB_TOKEN` environment variable

**Security Note:** Keep your token secure and never commit it to version control.

## Usage

### Basic Usage

```python
from src.clients.github_mcp_client import create_github_mcp_client

# Create and initialize client
client = create_github_mcp_client()

# List available tools
tools = client.list_tools()
for tool in tools:
    print(f"{tool.name}: {tool.description}")

# Create an issue
result = client.create_issue(
    owner="octocat",
    repo="Hello-World",
    title="Bug report",
    body="Something is broken",
    labels=["bug"]
)

# Clean up
client.close()
```

### Using Context Manager

```python
from src.clients.github_mcp_client import GitHubMCPClient

with GitHubMCPClient() as client:
    # Client is automatically initialized
    issues = client.list_issues(
        owner="octocat",
        repo="Hello-World",
        state="open"
    )
    print(f"Found {len(issues)} open issues")
# Client is automatically closed
```

### Integration with LangGraph Agents

```python
from src.tools.github_mcp_tools import ALL_MCP_TOOLS
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# Create agent with MCP tools
agent = create_react_agent(
    llm,
    tools=ALL_MCP_TOOLS
)

# Use the agent
result = agent.invoke({
    "messages": [
        ("user", "List all open issues in https://github.com/octocat/Hello-World")
    ]
})
```

### Example Script

Run the comprehensive example:

```bash
python examples/mcp_client_example.py
```

This demonstrates:
- Client initialization
- Listing available tools
- Creating issues and PRs
- Integration with LangChain

## Available Operations

The MCP client provides access to GitHub operations including:

### Issues
- Create issues with title, body, labels, and assignees
- List issues (open, closed, or all)
- Add comments to issues
- Update issue status

### Pull Requests
- Create pull requests
- List pull requests
- Add reviews and comments
- Merge pull requests

### Repository Operations
- Get file contents
- Create or update files
- Search code
- List branches and commits

### Advanced Operations
The exact set of available operations depends on the MCP server. Use `client.list_tools()` to discover all available tools.

## Remote MCP Server

### Default Server: GitHub Copilot MCP Endpoint

The default server URL is `https://api.githubcopilot.com/mcp`.

**Important Notes:**
1. This endpoint may not be publicly accessible
2. It may require GitHub Copilot subscription
3. Special authentication beyond GitHub PAT may be needed
4. The endpoint is not officially documented for external use

### Testing Connectivity

If you encounter connection errors when using the default endpoint:

```python
try:
    client = create_github_mcp_client()
    tools = client.list_tools()
    print(f"Connected! Found {len(tools)} tools")
except Exception as e:
    print(f"Connection failed: {e}")
    print("The remote server may not be publicly accessible")
```

### Alternative: Local MCP Server

If the remote endpoint is not accessible, you can run a local MCP server:

1. Install the official GitHub MCP server:
   ```bash
   npm install -g @modelcontextprotocol/server-github
   ```

2. Run the server:
   ```bash
   mcp-server-github --token YOUR_GITHUB_TOKEN
   ```

3. Update your `.env`:
   ```bash
   GITHUB_MCP_SERVER_URL=http://localhost:3000
   ```

## Protocol Details

### JSON-RPC 2.0

The MCP client uses JSON-RPC 2.0 for communication:

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_issue",
    "arguments": {
      "owner": "octocat",
      "repo": "Hello-World",
      "title": "Bug report",
      "body": "Description"
    }
  }
}
```

**Response Format:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"number\": 123, \"url\": \"...\"}"
      }
    ]
  }
}
```

### Authentication

Authentication is done via HTTP Authorization header:

```
Authorization: Bearer ghp_your_github_token
```

### Available Methods

- `initialize` - Initialize MCP session
- `tools/list` - List available tools
- `tools/call` - Execute a tool

## Error Handling

The client handles various error scenarios:

```python
from src.clients.github_mcp_client import GitHubMCPClient

try:
    with GitHubMCPClient() as client:
        result = client.create_issue(
            owner="invalid",
            repo="nonexistent",
            title="Test",
            body="Test"
        )
except ValueError as e:
    print(f"Configuration error: {e}")
except ConnectionError as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"MCP server error: {e}")
```

## Troubleshooting

### Connection Refused / Timeout

**Problem:** Can't connect to the MCP server

**Solutions:**
1. Verify the server URL is correct
2. Check if the server is publicly accessible
3. Try using a local MCP server instead
4. Verify network connectivity and firewall settings

### Authentication Failed

**Problem:** 401 Unauthorized error

**Solutions:**
1. Verify `GITHUB_TOKEN` is set correctly
2. Check token has required scopes
3. Ensure token hasn't expired
4. Try generating a new token

### Tool Not Found

**Problem:** MCP server doesn't recognize a tool

**Solutions:**
1. List available tools: `client.list_tools()`
2. Check if the server supports the operation
3. Verify MCP server version compatibility

### Invalid Repository URL

**Problem:** Error parsing repository URL

**Solution:** Use format `https://github.com/owner/repo` or `owner/repo`

## Integration with Existing Code

### Migrating from PyGithub

The MCP client can work alongside your existing PyGithub code:

```python
# Old PyGithub code (keep as fallback)
from github import Github
g = Github(token)
repo = g.get_repo("owner/repo")

# New MCP client code
from src.clients.github_mcp_client import create_github_mcp_client
mcp = create_github_mcp_client()
```

### Using in Agents

Update your agents to use MCP tools:

```python
from src.tools.github_mcp_tools import (
    mcp_create_github_issue,
    mcp_list_github_issues
)

# In your agent setup
tools = [
    mcp_create_github_issue,
    mcp_list_github_issues,
    # ... other tools
]
```

## Performance Considerations

1. **Connection Pooling:** The client reuses HTTP connections via `requests.Session`
2. **Lazy Initialization:** Tools are only fetched when needed
3. **Timeout:** Default 30-second timeout per request
4. **Caching:** Tool list is cached after first fetch

## Security Best Practices

1. **Token Security:**
   - Never commit tokens to version control
   - Use environment variables or secret management
   - Rotate tokens regularly
   - Use minimal required scopes

2. **Input Validation:**
   - Validate repository URLs before passing to client
   - Sanitize user input in issue bodies and comments

3. **Error Messages:**
   - Avoid exposing tokens in error messages
   - Log errors securely without sensitive data

## Testing

### Unit Tests

```python
import pytest
from src.clients.github_mcp_client import GitHubMCPClient

def test_client_initialization():
    client = GitHubMCPClient(github_token="test_token")
    assert client.github_token == "test_token"

# Add more tests...
```

### Integration Tests

Mark integration tests that require real MCP server:

```python
@pytest.mark.integration
def test_list_tools():
    client = create_github_mcp_client()
    tools = client.list_tools()
    assert len(tools) > 0
```

Run with: `pytest -m integration`

## Future Enhancements

Potential improvements:
1. Async/await support for better performance
2. Retry logic with exponential backoff
3. Rate limit handling
4. Webhook support
5. GraphQL query support
6. Streaming responses for large operations

## Resources

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [GitHub API Documentation](https://docs.github.com/en/rest)
- [LangChain Tools Documentation](https://python.langchain.com/docs/modules/agents/tools/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review example scripts in `examples/`
3. Check application logs for detailed error messages
4. Open an issue on the repository

## License

This MCP client implementation follows the same license as the main project.
