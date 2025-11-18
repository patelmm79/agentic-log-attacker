import os
import sys
import re
import logging
import uuid
from dotenv import load_dotenv
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
import google.generativeai as genai
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AnyMessage, HumanMessage
from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.agents.log_explorer import log_explorer_agent
from src.agents.issue_creation_agent import issue_creation_agent, Issue
from src.agents.github_issue_manager import github_issue_manager_agent
from src.agents.supervisor import supervisor_agent
from src.agents.code_fixer import code_fixer_agent
from src.agents.solutions_agent import solutions_agent

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
    cloud_run_service: str  # Service name/ID
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
    service_name = state.get("cloud_run_service")
    service_type = state.get("service_type", "cloud_run")  # Default to cloud_run

    # If not provided in state, attempt to extract from the user query as fallback
    if not service_name:
        # Try to match service type and name patterns
        service_patterns = [
            (r"cloud run service\s+['\"]?([\w-]+)['\"]?", "cloud_run"),
            (r"cloud build\s+(?:logs for\s+)?['\"]?([\w-]+)['\"]?", "cloud_build"),
            (r"cloud function\s+['\"]?([\w-]+)['\"]?", "cloud_functions"),
            (r"gce instance\s+['\"]?([\w-]+)['\"]?", "gce"),
            (r"gke cluster\s+['\"]?([\w-]+)['\"]?", "gke"),
            (r"app engine\s+['\"]?([\w-]+)['\"]?", "app_engine"),
        ]

        for pattern, svc_type in service_patterns:
            match = re.search(pattern, user_query, re.IGNORECASE)
            if match:
                service_name = match.group(1)
                service_type = svc_type
                logger.info(f"Extracted service name '{service_name}' and type '{service_type}' from query")
                break

        if not service_name:
            error_msg = "No service name specified. Please provide a service name in your query (e.g., 'cloud run service my-service', 'cloud build my-build') or in the API request."
            logger.error(error_msg)
            return {
                "messages": [HumanMessage(content=error_msg)],
                "next_agent": "END",
                "cloud_run_service": None,
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
        "cloud_run_service": service_name,
        "service_type": service_type,
        "git_repo_url": repo_url,
        "next_agent": next_agent,
        "issue_content": issue_content
    }
    return updates

def log_explorer_node(state: AgentState):
    """Answers questions about logs and explores potential issues."""
    logger.info("--- Log Explorer Node ---")
    service_name = state.get('cloud_run_service')
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
    service_name = state.get('cloud_run_service')
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
    service_name = state.get('cloud_run_service')
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
    logger.info("FastAPI application starting up...")
    logger.info(f"PORT environment variable: {os.environ.get('PORT', '8080')}")
    logger.info("Application is ready to receive requests")
    logger.info("=" * 50)

class Query(BaseModel):
    user_query: str
    service_name: str = None  # Optional, can be extracted from query if not provided
    service_type: str = "cloud_run"  # Optional, defaults to cloud_run for backward compatibility
    repo_url: str = None  # Optional, GitHub repository URL for issue creation

@app.get("/")
async def read_root():
    logger.info("Health check endpoint called")
    return {"message": "Agentic Log Attacker API is running!"}

@app.post("/run_workflow")
async def run_workflow(query: Query):
    # Initial state for the workflow
    initial_state = {
        "messages": [HumanMessage(content=query.user_query)],
        "cloud_run_service": query.service_name,
        "service_type": query.service_type,
        "git_repo_url": query.repo_url
    }

    # Generate a unique thread_id for this workflow execution
    thread_id = str(uuid.uuid4())

    # Run the workflow with the required config for the checkpointer
    result = full_workflow.invoke(
        initial_state,
        config={"configurable": {"thread_id": thread_id}}
    )

    return {"result": result}