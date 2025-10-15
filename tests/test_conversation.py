
import os
import sys
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app

# Note: This is an integration test that runs against live APIs.
# It requires a configured environment with API keys and permissions.

@pytest.mark.integration
def test_full_conversation_flow():
    """Simulates a full conversation to test state management and conversational memory."""

    # Initial state
    state = {
        "cloud_run_service": os.environ.get("CLOUD_RUN_SERVICE"),
        "git_repo_url": os.environ.get("GIT_REPO_URL"),
        "user_query": "",
        "issues": [],
        "pull_requests": [],
        "orchestrator_history": [],
        "log_reviewer_history": [],
        "github_issue_manager_history": [],
        "suggested_fix": "",
        "conversation_history": []
    }

    # Turn 1: Initial performance question
    print("\n--- Turn 1: Initial Performance Question ---")
    state["user_query"] = "for cloud run service vllm-gemma-3-1b-it, can you tell if the performance has improved from yesterday's initial requests to today's?"
    response_state = app.invoke(state)
    assert response_state["cloud_run_service"] == "vllm-gemma-3-1b-it"
    response_text = response_state["orchestrator_history"][-1].lower()
    assert "cold start" in response_text
    assert "warm instance" in response_text
    assert "233" in response_text
    assert "222" in response_text
    state = response_state

    # Turn 2: Follow-up question about cold starts
    print("\n--- Turn 2: Follow-up on Cold Starts ---")
    state["user_query"] = "how about subsequent cold starts today after the first request? any improvements over time?"
    response_state = app.invoke(state)
    assert response_state["cloud_run_service"] == "vllm-gemma-3-1b-it" # Should remember from turn 1
    assert "cold start" in response_state["orchestrator_history"][-1].lower()
    state = response_state

    # Turn 3: Introduce GitHub context
    print("\n--- Turn 3: Introduce GitHub Context ---")
    state["user_query"] = "in github project https://github.com/patelmm79/vllm-container-prewarm, I created pull request https://github.com/patelmm79/vllm-container-prewarm/pull/29 to address a repeating issue having to do with missing TORCH_CUDA_ARCH_LIST. Did the pull request address the issue?"
    response_state = app.invoke(state)
    assert response_state["git_repo_url"] == "https://github.com/patelmm79/vllm-container-prewarm"
    assert "did not address the issue" in response_state["orchestrator_history"][-1].lower()
    state = response_state

    # Turn 4: Ask the agent to act on the GitHub context
    print("\n--- Turn 4: Ask Agent to Act on GitHub Context ---")
    state["user_query"] = "Are you able to re-open the associated github issue and indicate that the pull request did not work?"
    response_state = app.invoke(state)
    # The key assertion: The agent should now have the context to answer differently
    assert "I cannot re-open any GitHub issues" not in response_state["orchestrator_history"][-1]
    # A better response would be to confirm its ability and ask for the issue number, or attempt the action.
    # For now, we assert it doesn't give the old canned response.
    state = response_state

    # Turn 5: Check conversational memory explicitly
    print("\n--- Turn 5: Check Conversational Memory ---")
    state["user_query"] = "I just provided you with the github repository, the information is there"
    response_state = app.invoke(state)
    assert "I do not have access to" not in response_state["orchestrator_history"][-1]
    assert "Based on the logs provided, there is no mention" not in response_state["orchestrator_history"][-1]
    state = response_state

