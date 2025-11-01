# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered log monitoring and issue management system that uses LangGraph for orchestrating multiple agents. The system monitors Google Cloud Run service logs, analyzes them using the Gemini API, identifies issues, and can automatically create GitHub issues with suggested fixes.

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
- `cloud_run_service`: Target Cloud Run service name
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
- Filters by Cloud Run service name
- Supports time-range filtering (max 24 hours)
- Returns logs in descending order (most recent first)

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
- `GET /`: Health check endpoint
- `POST /run_workflow`: Execute the agent workflow with a JSON body containing `user_query`

## Important Implementation Details

### Service Name Extraction
The supervisor node attempts to extract Cloud Run service names from user queries using regex: `r"cloud run service\s+([\w-]+)"`. Falls back to environment variable if not found.

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