# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered log monitoring and issue management system that uses LangGraph for orchestrating multiple agents. The system monitors logs from multiple GCP services (Cloud Run, Cloud Build, Cloud Functions, GCE, GKE, App Engine), analyzes them using the Gemini API, identifies issues, and can automatically create GitHub issues with suggested fixes.

### A2A Integration (v2.0)

The service is now A2A (Agent-to-Agent) protocol compatible and integrates with dev-nexus and other A2A agents. Key changes:

- **New Endpoint**: `/a2a/execute` (replaces old `/run_workflow`)
- **Authentication**: Required (Google Cloud service account tokens)
- **Single Skill**: `analyze_and_monitor_logs` (wraps the full LangGraph workflow)
- **Rate Limiting**: 100 requests/minute per service account
- **Region**: us-central1 (to match dev-nexus deployment)

New files for A2A support:
- `src/models/a2a_models.py` - Request/response models
- `src/middleware/a2a_auth.py` - Authentication middleware
- `src/middleware/rate_limiter.py` - Rate limiting middleware
- `scripts/setup_a2a_secrets.sh` - Secret Manager setup
- `scripts/test_a2a_endpoint.py` - Integration test script

## Development Commands

### Running the Application

```bash
# Run locally with FastAPI
uvicorn src.main:app --host 0.0.0.0 --port 8080

# Access the API documentation
# http://localhost:8080/docs
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_conversation.py

# Run with markers (integration tests)
pytest -m integration
```

### Deployment

```bash
# Deploy to Google Cloud Run via Cloud Build
gcloud builds submit --config cloudbuild.yaml .

# Authenticate with Google Cloud (required for log access)
gcloud auth application-default login
```

## Architecture

### Multi-Agent Workflow System

The application uses LangGraph's StateGraph to orchestrate multiple specialized agents. The workflow is defined in `src/main.py` and follows this pattern:

1. **Supervisor Node** (`supervisor_agent`) - Entry point that routes requests to appropriate agents based on user queries
2. **Log Explorer Node** (`log_explorer_agent`) - Queries GCP logs and answers questions about log content
3. **Issue Creation Node** (`issue_creation_agent`) - Analyzes logs to identify and structure issues
4. **Solutions Node** (`solutions_agent`) - Provides recommendations for identified issues
5. **GitHub Issue Manager Node** (`github_issue_manager_agent`) - Creates GitHub issues from identified problems
6. **Code Fixer Node** (`code_fixer_agent`) - Generates code fixes and creates pull requests

### State Management

The workflow state (`AgentState` in `src/main.py`) tracks:
- `service_name`: Target service name (works for all service types)
- `service_type`: Type of GCP service (cloud_run, cloud_build, cloud_functions, gce, gke, app_engine)
- `git_repo_url`: GitHub repository URL for issue creation
- `messages`: Conversation history (Annotated with operator.add)
- `issues`: List of identified issues (using Pydantic `Issue` model)
- `orchestrator_history`, `log_reviewer_history`, `github_issue_manager_history`: Agent-specific histories
- `suggested_fix`: Code fix suggestions
- `next_agent`: Routing decision from supervisor

### Agent Communication Pattern

Agents communicate through the shared state. Each agent:
1. Receives the current state
2. Performs its specialized task using Gemini API
3. Returns a dictionary with state updates
4. State updates are merged into the global state by LangGraph

### Key Components

**Supervisor Agent** (`src/agents/supervisor.py`):
- Uses few-shot prompting to route user queries
- Extracts service names and GitHub URLs from queries
- Returns structured JSON responses with `next_agent`, `repo_url`, and `issue_content`

**Log Explorer Agent** (`src/agents/log_explorer.py`):
- Fetches logs via `get_gcp_logs()` tool
- Automatically summarizes large log volumes (>200 lines)
- Maintains conversation context for follow-up queries

**GCP Logging Tool** (`src/tools/gcp_logging_tool.py`):
- Queries Google Cloud Logging API
- Supports multiple GCP service types via `service_type` parameter
- Uses service-specific filter variations from `src/models/service_types.py`
- Supports time-range filtering (max 48 hours with automatic retry)
- Returns logs in descending order (most recent first)
- Automatically tries multiple filter variations per service type

**GitHub Integration** (`src/tools/github_tool.py`, `src/agents/github_issue_manager.py`):
- Checks for duplicate issues before creation
- Skips issues already open or closed with "wontfix" label
- Extracts repo URLs from conversation history

## Environment Configuration

Required environment variables (see `.env.example`):
- `GEMINI_API_KEY`: Gemini API key for LLM inference
- `GEMINI_MODEL_NAME`: Model name (default: "gemini-2.5-flash")
- `GITHUB_TOKEN`: GitHub personal access token (for issue creation)
- `GITHUB_REPOSITORY`: Target GitHub repository
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `CLOUD_RUN_SERVICE_NAME`: Default Cloud Run service to monitor
- `CLOUD_RUN_REGION`: Cloud Run service region

## API Interface

FastAPI endpoints in `src/main.py`:
- `GET /health` / `GET /`: Health check endpoint (returns status of service dependencies)
- `GET /.well-known/agent.json`: A2A AgentCard for service discovery by dev-nexus
- `POST /a2a/execute`: Execute A2A skills (requires authentication via service account token)

### A2A Endpoint Details

**POST /a2a/execute** (Requires Authentication)

Request:
```json
{
  "skill_id": "analyze_and_monitor_logs",
  "input": {
    "user_query": "string (required)",
    "service_name": "string (optional)",
    "service_type": "string (optional, defaults to cloud_run)",
    "repo_url": "string (optional)"
  }
}
```

Response:
```json
{
  "success": true,
  "result": {
    "service_name": "string",
    "service_type": "string",
    "analysis": "string",
    "issues_identified": 3,
    "issues_created": 2,
    "github_issue_urls": ["array of urls"],
    "orchestrator_history": ["array"]
  },
  "execution_time_ms": 5432
}
```

Authentication: Bearer token (Google Cloud identity token)

## Important Implementation Details

### Multi-Service Support
The system supports multiple GCP service types defined in `src/models/service_types.py`:
- **ServiceType Enum**: Defines supported service types (cloud_run, cloud_build, cloud_functions, gce, gke, app_engine)
- **SERVICE_CONFIG**: Maps each service type to its GCP resource type and filter variations
- Each service type has multiple filter variations to maximize log retrieval success

Example service configurations:
- Cloud Run: Uses `service_name` and `configuration_name` labels
- Cloud Build: Uses `build_id`, `build_trigger_id`, and logName patterns
- Cloud Functions: Uses `function_name` and `region` labels

### Service Name and Type Extraction
The supervisor node (`src/main.py:supervisor_node`) extracts both service name and type from user queries using multiple regex patterns:
- Cloud Run: `r"cloud run service\s+['\"]?([\w-]+)['\"]?"`
- Cloud Build: `r"cloud build\s+(?:logs for\s+)?['\"]?([\w-]+)['\"]?"`
- Cloud Functions: `r"cloud function\s+['\"]?([\w-]+)['\"]?"`
- GCE: `r"gce instance\s+['\"]?([\w-]+)['\"]?"`
- GKE: `r"gke cluster\s+['\"]?([\w-]+)['\"]?"`
- App Engine: `r"app engine\s+['\"]?([\w-]+)['\"]?"`

Falls back to environment variable if not found. Defaults to "cloud_run" service type.

### JSON Response Parsing
Several agents expect JSON responses from Gemini. The code handles markdown-wrapped JSON (e.g., ` ```json ... ``` `) by stripping the markers before parsing.

### Issue Deduplication
The GitHub issue manager compares issue titles against existing issues (both open and closed) to prevent duplicates. It will skip creation if an issue is open or closed with "wontfix".

### Code Fixer Workflow
The code_fixer_agent:
1. Clones the repository to a temp directory
2. Uses LLM to identify relevant files from the full file list
3. Reads only the relevant files to reduce token usage
4. Generates a fix and creates a new branch
5. Commits changes and creates a pull request

### Workflow Graph Structure
The graph uses both static edges (`add_edge`) and conditional routing (`route_after_supervisor`). Currently, most edges are static, with supervisor routing logic commented out in the code.

## Testing Strategy

- Unit tests in `tests/` directory
- Integration tests marked with `@pytest.mark.integration`
- `test_workflow.py` provides example workflow invocations with different query types

## Dependencies

Core dependencies:
- `langchain_google_genai`: Gemini integration
- `langgraph`: Agent orchestration framework
- `fastapi` + `uvicorn`: Web API
- `google-cloud-logging`: GCP log access
- `PyGithub`: GitHub API client
- `pydantic`: Data validation for Issue model