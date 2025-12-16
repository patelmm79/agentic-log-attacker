import os
import sys
import re
import logging
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
import google.generativeai as genai
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AnyMessage, HumanMessage
from fastapi import FastAPI, Request, Depends, HTTPException
from pydantic import BaseModel

from src.agents.log_explorer import log_explorer_agent
from src.agents.issue_creation_agent import issue_creation_agent, Issue
from src.agents.github_issue_manager import github_issue_manager_agent
from src.agents.supervisor import supervisor_agent
from src.agents.code_fixer import code_fixer_agent
from src.agents.solutions_agent import solutions_agent
from src.models.a2a_models import A2ARequest, A2AResponse
from src.middleware.a2a_auth import authenticator
from src.middleware.rate_limiter import rate_limiter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
logger.info(f"CLOUD_RUN_REGION: {os.environ.get('CLOUD_RUN_REGION')}")
logger.info(f"GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
logger.info(f"GEMINI_MODEL_NAME: {os.environ.get('GEMINI_MODEL_NAME')}")

# Configure the generative AI model
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    logger.error("GEMINI_API_KEY environment variable is not set. The application will not function properly.")
    # Don't crash on startup, but the API won't work without it
else:
    genai.configure(api_key=gemini_api_key)
    logger.info("Gemini API configured successfully")

class AgentState(TypedDict):
    """Defines the state of the agentic workflow."""
    service_name: str  # Service name/ID (works for all service types)
    service_type: str  # Service type (cloud_run, cloud_build, etc.)
    git_repo_url: str
    messages: Annotated[list[AnyMessage], operator.add]
    issues: list[Issue]
    pull_requests: list
    orchestrator_history: Annotated[list, operator.add]
    log_reviewer_history: Annotated[list, operator.add]
    github_issue_manager_history: list
    suggested_fix: str
    next_agent: str

def supervisor_node(state: AgentState):
    """The entry point of the workflow.

    This node is responsible for coordinating the work of the other agents.
    """
    logger.info("--- Supervisor Node ---")
    user_query = state['messages'][-1].content
    conversation_history = state['messages']

    # Get service name and type from state (passed from API request)
    service_name = state.get("service_name")
    service_type = state.get("service_type", "cloud_run")  # Default to cloud_run

    # If not provided in state, attempt to extract from the user query as fallback
    if not service_name:
        # Try to match service type and name patterns
        # Pattern explanation: [a-zA-Z0-9._-]+ matches alphanumeric, dots, underscores, and hyphens
        # (?:['\"]|\s|,|$) ensures the name ends with a quote, whitespace, comma, or end of string
        # This prevents partial matches like "my" from "my@invalid"
        # This aligns with GCP naming conventions and our sanitization function
        service_patterns = [
            (r"cloud run service\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_run"),
            (r"cloud build\s+(?:logs for\s+)?['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_build"),
            (r"cloud function\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "cloud_functions"),
            (r"gce instance\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "gce"),
            (r"gke cluster\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "gke"),
            (r"app engine\s+['\"]?([a-zA-Z0-9._-]+)(?:['\"]|\s|,|$)", "app_engine"),
        ]

        for pattern, svc_type in service_patterns:
            match = re.search(pattern, user_query, re.IGNORECASE)
            if match:
                service_name = match.group(1)
                service_type = svc_type

                # Validate extracted service name matches expected format
                # This provides defense-in-depth before the sanitization step
                if not re.match(r'^[a-zA-Z0-9._-]+$', service_name):
                    logger.warning(
                        f"Extracted potentially invalid service name: '{service_name}'. "
                        f"Service names should only contain alphanumeric characters, dots, underscores, and hyphens."
                    )
                    continue  # Try next pattern

                logger.info(f"Extracted service name '{service_name}' and type '{service_type}' from query")
                break

        if not service_name:
            error_msg = "No service name specified. Please provide a service name in your query (e.g., 'cloud run service my-service', 'cloud build my-build') or in the API request."
            logger.error(error_msg)
            return {
                "messages": [HumanMessage(content=error_msg)],
                "next_agent": "END",
                "service_name": None,
                "service_type": "cloud_run"
            }
    else:
        logger.info(f"Using service name '{service_name}' and type '{service_type}' from request")

    response = supervisor_agent(user_query=user_query, conversation_history=conversation_history)

    # Extract next_agent and repo_url from the structured response
    next_agent = response["next_agent"]
    repo_url = response.get("repo_url")
    issue_content = response.get("issue_content") # Initialize issue_content here

    logger.info(f"Supervisor Agent decided next_agent: {next_agent}")
    if repo_url:
        logger.info(f"Supervisor Agent extracted repo_url: {repo_url}")

    # Return updates to the state
    updates = {
        "orchestrator_history": response['history'],
        "service_name": service_name,
        "service_type": service_type,
        "git_repo_url": repo_url,
        "next_agent": next_agent,
        "issue_content": issue_content
    }
    return updates

def log_explorer_node(state: AgentState):
    """Answers questions about logs and explores potential issues."""
    logger.info("--- Log Explorer Node ---")
    service_name = state.get('service_name')
    service_type = state.get('service_type', 'cloud_run')
    user_query = state['messages'][-1].content

    logger.info(f"Service Name: {service_name}")
    logger.info(f"Service Type: {service_type}")
    logger.info(f"User Query: {user_query}")

    result = log_explorer_agent(
        service_name=service_name,
        service_type=service_type,
        user_query=user_query,
        conversation_history=state['messages']
    )

    return {"log_reviewer_history": [result], "orchestrator_history": state['orchestrator_history'] + [result]}

def issue_creation_node(state: AgentState):
    """Analyzes log files and generates issues in every case."""
    logger.info("--- Issue Creation Node ---")
    service_name = state.get('service_name')
    repo_url = state.get('git_repo_url')

    logger.info(f"Service name: {service_name}")
    logger.info(f"Repo URL: {repo_url}")

    issues = issue_creation_agent(service_name=service_name, repo_url=repo_url)
    logger.info(f"Issue creation agent returned {len(issues)} issues")
    if issues:
        for i, issue in enumerate(issues):
            logger.info(f"Issue {i+1}: {issue.description} (Priority: {issue.priority})")
    else:
        logger.warning("No issues were created by issue_creation_agent")

    return {"issues": issues}

def github_issue_manager_node(state: AgentState):
    """Creates GitHub issues for the identified issues."""
    logger.info("--- GitHub Issue Manager Node ---")
    issues_to_create = state.get('issues', [])
    issue_content = state.get('issue_content')
    suggested_fix = state.get('suggested_fix')
    repo_url = state.get('git_repo_url')

    logger.info(f"Issues from state: {len(issues_to_create)}")
    logger.info(f"Repo URL: {repo_url}")
    logger.info(f"Issue content: {issue_content}")

    if issue_content and suggested_fix and not issues_to_create:
        # If issue_content and suggested_fix are present, use them to create the issue
        # issue_content will be the title/short description, suggested_fix will be the body
        new_issue = Issue(description=issue_content, priority="Medium", log_entries=[suggested_fix])
        issues_to_create = [new_issue]
        logger.info("Created issue from issue_content and suggested_fix")
    elif issue_content and not issues_to_create:
        # Fallback if only issue_content is present
        new_issue = Issue(description=issue_content, priority="Medium", log_entries=[])
        issues_to_create = [new_issue]
        logger.info("Created issue from issue_content only")

    if not issues_to_create:
        logger.warning("No issues to create!")
        return {"github_issue_manager_history": ["No issues to create"]}

    if not repo_url:
        logger.error("No repo_url provided!")
        return {"github_issue_manager_history": ["Error: No repository URL provided"]}

    logger.info(f"Calling github_issue_manager_agent with {len(issues_to_create)} issues")
    history = github_issue_manager_agent(issues=issues_to_create, repo_url=repo_url, user_query=state['messages'][-1].content)
    logger.info(f"GitHub issue manager result: {history}")
    return {"github_issue_manager_history": history['github_issue_manager_history']}

def code_fixer_node(state: AgentState):
    """Suggests and applies a code fix for the identified issues."""
    logger.info("Code fixer agent is running")
    # For now, just take the first issue
    # In the future, we can iterate over all issues
    if state.get('issues'):
        suggested_fix = code_fixer_agent(issue=state['issues'][0], repo_url=state['git_repo_url'])
        return {"suggested_fix": suggested_fix}
    return {}

def solutions_node(state: AgentState):
    """Provides a solution for the identified issues."""
    logger.info("--- Entering Solutions Node ---")
    logger.info(f"Issues in state: {state.get('issues')}")
    service_name = state.get('service_name')
    # Pass the first issue if available, otherwise an empty dict
    issue_to_process = state['issues'][0] if state.get('issues') else {}
    solution = solutions_agent(issue=issue_to_process, user_query=state['messages'][-1].content, service_name=service_name)
    logger.info(f"Solutions agent returned: {solution}")
    return {"suggested_fix": solution}

def ask_for_repo_url_node(state: AgentState):
    """Asks the user for the GitHub repository URL."""
    logger.info("--- Ask for Repo URL Node ---")
    return {"orchestrator_history": ["Please provide the full GitHub repository URL (e.g., https://github.com/owner/repo)."]}

# Define the graph
workflow = StateGraph(AgentState)

# Add the nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("log_explorer", log_explorer_node)
workflow.add_node("issue_creation", issue_creation_node)
workflow.add_node("github_issue_manager", github_issue_manager_node)
workflow.add_node("code_fixer", code_fixer_node)
workflow.add_node("solutions", solutions_node)
workflow.add_node("ask_for_repo_url", ask_for_repo_url_node)

def route_after_log_explorer(state: AgentState):
    """Determines if we should create issues after exploring logs."""
    logger.info("--- Routing after log_explorer ---")
    # Check if user wants to create GitHub issues (repo_url is set)
    if state.get('git_repo_url'):
        logger.info("Repo URL found, routing to issue_creation")
        return "issue_creation"
    else:
        logger.info("No repo URL, ending workflow")
        return "end"

workflow.set_entry_point("supervisor")
workflow.add_edge("supervisor", "log_explorer")

# After log_explorer, conditionally go to issue_creation if repo_url is provided
workflow.add_conditional_edges(
    "log_explorer",
    route_after_log_explorer,
    {
        "issue_creation": "issue_creation",
        "end": END
    }
)

# After issue_creation, go to github_issue_manager to create GitHub issues
workflow.add_edge("issue_creation", "github_issue_manager")

# Terminal nodes
workflow.add_edge("github_issue_manager", END)
workflow.add_edge("code_fixer", END)
workflow.add_edge("solutions", END)
workflow.add_edge("ask_for_repo_url", END)





# Compile the graph
memory = InMemorySaver()

full_workflow = workflow.compile(checkpointer=memory)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("FastAPI application starting up (A2A Integration v2.0)...")
    logger.info(f"PORT environment variable: {os.environ.get('PORT', '8080')}")
    logger.info("A2A A2A Skill: analyze_and_monitor_logs")
    logger.info("Application is ready to receive A2A requests from dev-nexus")
    logger.info("=" * 50)


@app.get("/health")
@app.get("/")
async def health_check():
    """Health check endpoint for A2A compatibility."""
    gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
    gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    github_token = bool(os.getenv("GITHUB_TOKEN"))

    status = "healthy" if (gemini_configured and gcp_project and github_token) else "degraded"

    return {
        "status": status,
        "service": "agentic-log-attacker",
        "version": "2.0.0-a2a",
        "gemini_configured": gemini_configured,
        "gcp_project": gcp_project,
        "github_configured": github_token,
        "available_skills": ["analyze_and_monitor_logs"],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/.well-known/agent.json")
async def agent_metadata():
    """Return A2A AgentCard for service discovery by dev-nexus."""
    return {
        "name": "agentic-log-attacker",
        "version": "2.0.0",
        "description": "AI-powered GCP log monitoring and issue management system with multi-agent workflow",
        "capabilities": [
            "log_analysis",
            "multi_service_support",
            "issue_detection",
            "github_integration",
            "automated_remediation"
        ],
        "supported_services": [
            "cloud_run",
            "cloud_build",
            "cloud_functions",
            "gce",
            "gke",
            "app_engine"
        ],
        "endpoints": {
            "execute": "/a2a/execute",
            "health": "/health"
        },
        "skills": [
            {
                "id": "analyze_and_monitor_logs",
                "name": "Analyze and Monitor GCP Logs",
                "description": "Full multi-agent workflow: queries GCP logs, analyzes with AI, detects issues, creates GitHub issues",
                "authentication": "service_account",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_query": {
                            "type": "string",
                            "description": "Natural language query about logs",
                            "required": True
                        },
                        "service_name": {
                            "type": "string",
                            "description": "GCP service name (optional, extracted from query if not provided)"
                        },
                        "service_type": {
                            "type": "string",
                            "enum": ["cloud_run", "cloud_build", "cloud_functions", "gce", "gke", "app_engine"],
                            "default": "cloud_run"
                        },
                        "repo_url": {
                            "type": "string",
                            "description": "GitHub repository URL for issue creation (optional)"
                        }
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "service_type": {"type": "string"},
                        "analysis": {"type": "string"},
                        "issues_identified": {"type": "integer"},
                        "issues_created": {"type": "integer"},
                        "github_issue_urls": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        ],
        "authentication": {
            "type": "service_account",
            "method": "bearer_token",
            "token_type": "google_identity_token",
            "allowed_service_accounts": [
                "ai-ap-service@globalbiting-dev.iam.gserviceaccount.com"
            ]
        },
        "rate_limiting": {
            "requests_per_minute": 100,
            "window_seconds": 60
        },
        "deployment": {
            "platform": "cloud_run",
            "region": "us-central1",
            "project": os.getenv("GOOGLE_CLOUD_PROJECT")
        },
        "integration": {
            "dev_nexus_url": "https://pattern-discovery-agent-665374072631.us-central1.run.app/"
        }
    }


@app.post("/a2a/execute")
async def a2a_execute(
    request: A2ARequest,
    caller: str = Depends(authenticator.verify_token)
):
    """
    Execute A2A skills via dev-nexus integration.

    Currently supports:
    - analyze_and_monitor_logs: Full workflow for log analysis and issue creation
    """
    start_time = time.time()

    # Rate limiting
    await rate_limiter.check_rate_limit(caller)

    # Validate skill ID
    if request.skill_id != "analyze_and_monitor_logs":
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{request.skill_id}' not found. Available skills: analyze_and_monitor_logs"
        )

    try:
        # Extract input parameters
        user_query = request.input.get("user_query")
        service_name = request.input.get("service_name")
        service_type = request.input.get("service_type", "cloud_run")
        repo_url = request.input.get("repo_url")

        if not user_query:
            raise HTTPException(status_code=400, detail="user_query is required")

        logger.info(f"[A2A] Executing workflow: caller={caller}, query_length={len(user_query)}")

        # Execute the LangGraph workflow (same as old /run_workflow)
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "service_name": service_name,
            "service_type": service_type,
            "git_repo_url": repo_url
        }

        thread_id = str(uuid.uuid4())

        result = full_workflow.invoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}}
        )

        # Format response for A2A
        execution_time = int((time.time() - start_time) * 1000)

        # Extract GitHub issue URLs from result
        github_issues = []
        if result.get('github_issue_manager_history'):
            for history_item in result['github_issue_manager_history']:
                if isinstance(history_item, str) and 'https://github.com' in history_item:
                    # Extract URLs from history text
                    urls = re.findall(r'https://github\.com/[^\s]+', history_item)
                    github_issues.extend(urls)

        analysis_text = None
        if result.get('log_reviewer_history'):
            analysis_text = result.get('log_reviewer_history')[-1]

        logger.info(
            f"[A2A] Workflow completed: issues_identified={len(result.get('issues', []))}, "
            f"issues_created={len(github_issues)}, execution_time={execution_time}ms"
        )

        return A2AResponse(
            success=True,
            result={
                "service_name": result.get('service_name'),
                "service_type": result.get('service_type'),
                "analysis": analysis_text,
                "issues_identified": len(result.get('issues', [])),
                "issues_created": len(github_issues),
                "github_issue_urls": github_issues,
                "orchestrator_history": result.get('orchestrator_history', [])
            },
            execution_time_ms=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[A2A] Workflow execution failed: {e}", exc_info=True)
        execution_time = int((time.time() - start_time) * 1000)

        return A2AResponse(
            success=False,
            error=str(e),
            execution_time_ms=execution_time
        )