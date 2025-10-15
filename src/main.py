import os
import sys
import re
from dotenv import load_dotenv
from typing import TypedDict

from langgraph.graph import StateGraph, END
import google.generativeai as genai

from src.agents.log_explorer import log_explorer_agent
from src.agents.issue_creation_agent import issue_creation_agent, Issue
from src.agents.github_issue_manager import github_issue_manager_agent
from src.agents.supervisor import supervisor_agent
from src.agents.code_fixer import code_fixer_agent
from src.agents.solutions_agent import solutions_agent

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()
print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
print(f"CLOUD_RUN_REGION: {os.environ.get('CLOUD_RUN_REGION')}")

# Configure the generative AI model
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Configure the generative AI model
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

class AgentState(TypedDict):
    """Defines the state of the agentic workflow."""
    cloud_run_service: str
    git_repo_url: str
    user_query: str
    issues: list[Issue]
    pull_requests: list
    orchestrator_history: list
    log_reviewer_history: list
    github_issue_manager_history: list
    suggested_fix: str
    conversation_history: list
    next_agent: str

def supervisor_node(state: AgentState):
    """The entry point of the workflow. 
    
    This node is responsible for coordinating the work of the other agents.
    """
    print("--- Supervisor Node ---")
    user_query = state['user_query']
    conversation_history = state.get('conversation_history', [])
    
    # Attempt to extract the service name from the user query
    match_service = re.search(r"cloud run service\s+([\w-]+)", user_query, re.IGNORECASE)
    service_name = state.get("cloud_run_service") # Default to value from environment
    if match_service:
        service_name = match_service.group(1)
        print(f"Extracted service name from query: {service_name}")

    response = supervisor_agent(user_query=user_query, conversation_history=conversation_history)

    # Extract next_agent and repo_url from the structured response
    next_agent = response["next_agent"]
    repo_url = response.get("repo_url", state.get("git_repo_url")) # Use extracted or default

    print(f"Supervisor Agent decided next_agent: {next_agent}")
    if repo_url:
        print(f"Supervisor Agent extracted repo_url: {repo_url}")

    return {
        "orchestrator_history": response['history'],
        "cloud_run_service": service_name,
        "git_repo_url": repo_url, # Use the LLM extracted URL
        "next_agent": next_agent
    }

def log_explorer_node(state: AgentState):
    """Answers questions about logs and explores potential issues."""
    print("--- Log Explorer Node ---")
    service_name = state.get('cloud_run_service')
    user_query = state.get('user_query')

    print(f"Service Name: {service_name}")
    print(f"User Query: {user_query}")

    result = log_explorer_agent(
        service_name=service_name,
        user_query=user_query,
        conversation_history=state.get('conversation_history', [])
    )

    return {"log_reviewer_history": [result], "orchestrator_history": state['orchestrator_history'] + [result]}

def issue_creation_node(state: AgentState):
    """Analyzes log files and generates issues in every case."""
    print("--- Issue Creation Node ---")
    service_name = state.get('cloud_run_service')
    repo_url = state.get('git_repo_url')

    issues = issue_creation_agent(service_name=service_name, repo_url=repo_url)
    print(f"Issue creation agent returned: {issues}")
    return {"issues": issues}

def github_issue_manager_node(state: AgentState):
    """Creates GitHub issues for the identified issues."""
    print("GitHub issue manager agent is running")
    history = github_issue_manager_agent(issues=state.get('issues', []), repo_url=state['git_repo_url'], user_query=state.get('user_query'))
    return {"github_issue_manager_history": history['github_issue_manager_history']}

def code_fixer_node(state: AgentState):
    """Suggests and applies a code fix for the identified issues."""
    print("Code fixer agent is running")
    # For now, just take the first issue
    # In the future, we can iterate over all issues
    if state.get('issues'):
        suggested_fix = code_fixer_agent(issue=state['issues'][0], repo_url=state['git_repo_url'])
        return {"suggested_fix": suggested_fix}
    return {}

def solutions_node(state: AgentState):
    """Provides a solution for the identified issues."""
    print("--- Solutions Node ---")
    print(f"Issues in state: {state.get('issues')}")
    # Pass the first issue if available, otherwise an empty dict
    issue_to_process = state['issues'][0] if state.get('issues') else {}
    solution = solutions_agent(issue=issue_to_process, user_query=state.get('user_query'), service_name=state.get('cloud_run_service'))
    print(f"Solutions agent returned: {solution}")
    return {"suggested_fix": solution}

# Define the graph
workflow = StateGraph(AgentState)

# Add the nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("log_explorer", log_explorer_node)
workflow.add_node("issue_creation", issue_creation_node)
workflow.add_node("github_issue_manager", github_issue_manager_node)
workflow.add_node("code_fixer", code_fixer_node)
workflow.add_node("solutions", solutions_node)

# Define the edges
workflow.set_entry_point("supervisor")
def route_after_supervisor(state: AgentState):
    """Determines the next node to route to after the supervisor."""
    print("--- Routing after supervisor ---")
    next_agent = state.get("next_agent")
    if next_agent == "log_explorer":
        return "log_explorer"
    elif next_agent == "github_issue_manager":
        return "github_issue_manager"
    elif next_agent == "solutions_agent":
        return "solutions"
    else:
        return "end"

workflow.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "log_explorer": "log_explorer",
        "github_issue_manager": "github_issue_manager",
        "solutions": "solutions",
        "end": END,
    },
)

workflow.add_edge("code_fixer", END)

def route_after_issue_creation(state: AgentState):
    """Determines the next node to route to after issue creation."""
    print("--- Routing after issue creation ---")
    if state.get('issues'):
        return "github_issue_manager"
    else:
        return "end"

workflow.add_conditional_edges(
    "issue_creation",
    route_after_issue_creation,
    {
        "github_issue_manager": "github_issue_manager",
        "solutions": "solutions",
        "end": END,
    },
)

workflow.add_edge("solutions", END)


# Compile the graph
app = workflow.compile()