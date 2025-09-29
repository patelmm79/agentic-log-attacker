
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()
print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
print(f"CLOUD_RUN_REGION: {os.environ.get('CLOUD_RUN_REGION')}")

from langgraph.graph import StateGraph, END
from pydantic import BaseModel
import google.generativeai as genai
from typing import TypedDict, Annotated
import operator

from src.agents.log_reviewer import log_reviewer_agent, Issue
from src.agents.github_issue_manager import github_issue_manager_agent
from src.agents.orchestrator import orchestrator_agent
from src.agents.code_fixer import code_fixer_agent

# Configure the generative AI model
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-pro-latest')

class AgentState(TypedDict):
    """Defines the state of the agentic workflow."""
    cloud_run_service: str
    git_repo_url: str
    issues: list[Issue]
    pull_requests: list
    orchestrator_history: list
    log_reviewer_history: list
    github_issue_manager_history: list
    suggested_fix: str

def orchestrator_node(state: AgentState):
    """The entry point of the workflow. 
    
    This node is responsible for coordinating the work of the other agents.
    """
    print("Orchestrator agent is running")
    history = orchestrator_agent()
    return {"orchestrator_history": history['orchestrator_history']}

def log_reviewer_node(state: AgentState):
    """Reviews the logs and identifies potential issues."""
    print("Log reviewer agent is running")
    issues = log_reviewer_agent(service_name=state['cloud_run_service'])
    return {"issues": issues, "log_reviewer_history": ["Log reviewer agent was called"]}

def github_issue_manager_node(state: AgentState):
    """Creates GitHub issues for the identified issues."""
    print("GitHub issue manager agent is running")
    history = github_issue_manager_agent(issues=state['issues'], repo_url=state['git_repo_url'])
    return {"github_issue_manager_history": history['github_issue_manager_history']}

def code_fixer_node(state: AgentState):
    """Suggests and applies a code fix for the identified issues."""
    print("Code fixer agent is running")
    # For now, just take the first issue
    # In the future, we can iterate over all issues
    if state['issues']:
        suggested_fix = code_fixer_agent(issue=state['issues'][0], repo_url=state['git_repo_url'])
        return {"suggested_fix": suggested_fix}
    return {}

# Define the graph
workflow = StateGraph(AgentState)

# Add the nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("log_reviewer", log_reviewer_node)
workflow.add_node("github_issue_manager", github_issue_manager_node)
workflow.add_node("code_fixer", code_fixer_node)

# Define the edges
workflow.set_entry_point("orchestrator")
workflow.add_edge("orchestrator", "log_reviewer")

def should_create_issues(state: AgentState):
    """Determines whether to create GitHub issues based on the identified issues."""
    if len(state["issues"]) > 0:
        return "github_issue_manager"
    else:
        return "end"

workflow.add_conditional_edges(
    "log_reviewer",
    should_create_issues,
    {
        "github_issue_manager": "github_issue_manager",
        "end": END,
    },
)
workflow.add_edge("github_issue_manager", "code_fixer")
workflow.add_edge("code_fixer", END)


# Compile the graph
app = workflow.compile()

# Run the graph (for testing)
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud-run-service", help="The name of the Cloud Run service to analyze.", required=True)
    parser.add_argument("--git-repo-url", help="The URL of the git repository.", required=True)
    args = parser.parse_args()

    inputs = {"cloud_run_service": args.cloud_run_service, "git_repo_url": args.git_repo_url, "issues": [], "pull_requests": []}
    for output in app.stream(inputs):
        for key, value in output.items():
            print(f"Output from node '{key}':")
            print("---")
            print(value)
        print("\n---\n")
