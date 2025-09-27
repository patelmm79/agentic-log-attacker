import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
import google.generativeai as genai
from typing import TypedDict, Annotated
import operator

from src.agents.log_reviewer import log_reviewer_agent, Issue
from src.agents.github_issue_manager import github_issue_manager_agent
from src.agents.orchestrator import orchestrator_agent
from src.agents.code_fixer import code_fixer_agent

# Load environment variables
load_dotenv()

# Configure the generative AI model
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-pro')

class AgentState(TypedDict):
    """Defines the state of the agentic workflow."""
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
    issues = log_reviewer_agent()
    return {"issues": issues, "log_reviewer_history": ["Log reviewer agent was called"]}

def github_issue_manager_node(state: AgentState):
    """Creates GitHub issues for the identified issues."""
    print("GitHub issue manager agent is running")
    history = github_issue_manager_agent(state['issues'])
    return {"github_issue_manager_history": history['github_issue_manager_history']}

def code_fixer_node(state: AgentState):
    """Suggests and applies a code fix for the identified issues."""
    print("Code fixer agent is running")
    # For now, just take the first issue
    # In the future, we can iterate over all issues
    if state['issues']:
        suggested_fix = code_fixer_agent(state['issues'][0])
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
    inputs = {"issues": [], "pull_requests": []}
    for output in app.stream(inputs):
        for key, value in output.items():
            print(f"Output from node '{key}':")
            print("---")
            print(value)
        print("\n---\n")
