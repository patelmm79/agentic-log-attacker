import os
import sys
import uuid
from langchain_core.messages import HumanMessage

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.main import app

# Load environment variables (if needed for agents like gcp_logging_tool)
from dotenv import load_dotenv
load_dotenv()

def run_test_workflow(user_query: str):
    print(f"\n--- Running workflow for query: {user_query} ---")

    # Generate a unique thread_id for the conversation
    thread_id = str(uuid.uuid4())
    print(f"Thread ID: {thread_id}")

    # Invoke the agentic workflow
    final_state = app.invoke(
        {"messages": [HumanMessage(content=user_query)]},
        {"configurable": {"thread_id": thread_id}}
    )

    print("\n--- Final Agent State ---")
    # The final state is the response from app.invoke
    for key, value in final_state.items():
        print(f"{key}: {value}")

    # Extract and print the solution if available
    if "solution" in final_state:
        print(f"\n--- Extracted Solution ---")
        print(final_state["solution"])

if __name__ == "__main__":
    # Example user query for log explorer
    query_log_explorer = "for cloud run service vllm-gemma-3-1b-it, can you tell if the performance has improved from yesterday's initial requests to today's?"
    run_test_workflow(query_log_explorer)

    # Example user query that should route to solutions_agent
    query_solution = "for cloud run service vllm-gemma-3-1b-it, is there a way to execute or cache the \"Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): \" part during cloud build stage or during the first cold start, so that subsequent cold starts can be shorter?"
    run_test_workflow(query_solution)

    # Example user query for github issue manager
    query_github = "please create a github issue to repository vllm-container-prewarm, as a feature request to enable the \"Caching Compiled Kernels\" option"
    run_test_workflow(query_github)
