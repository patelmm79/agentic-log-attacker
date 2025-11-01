import os
import google.generativeai as genai
import json
from langchain_core.messages import HumanMessage, AIMessage

def supervisor_agent(user_query: str, conversation_history: list):
    """A supervisor agent that routes requests to other agents using a few-shot prompting strategy."""

    history_lines = []
    for msg in conversation_history:
        if isinstance(msg, HumanMessage):
            history_lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            history_lines.append(f"Agent: {msg.content}")
    history_str = "\n".join(history_lines)

    prompt = f"""You are a supervisor agent. Your job is to route user requests to the correct agent.
    If the user wants to create a GitHub issue, you must also extract the GitHub repository URL from the user's query.
    If a full URL is not provided, assume the owner is 'example' and construct the full URL.
    If you cannot confidently determine the 'repo_url' for a GitHub issue creation request, return {{"next_agent": "ask_for_repo_url"}}.

    When the user asks to create a GitHub issue containing info for "recommendation X" (where X is a number), you MUST find the full text of that recommendation from the `conversation_history` (which is provided as `history_str`) and include it in the `issue_content` field of your JSON response. Pay close attention to the numbering of the recommendations in the `history_str`.

    Here are the available agents and their capabilities:

    - **log_explorer**: Answers questions about logs and explores potential issues.
    - **github_issue_manager**: Interacts with GitHub to create new issues and review & manage existing issues. Requires a 'repo_url'.
    - **solutions_agent**: Provides solutions or recommendations for issues.

    Here are some examples of user queries and the correct agent to route to:

    **User Query:** "for cloud run service vllm-gemma-3-1b-it, can you tell if the performance has improved from yesterday's initial requests to today's?"
    **Response:** {{"next_agent": "log_explorer"}}

    **User Query:** "I need a solution for the high latency in my 'vllm-gemma' service."
    **Response:** {{"next_agent": "solutions_agent"}}

    **User Query:** "How can I optimize the cold start time for my Cloud Run service?"
    **Response:** {{"next_agent": "solutions_agent"}}

    **User Query:** "is there a way to execute or cache the \"Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): \" part during cloud build stage or during the first cold start, so that subsequent cold starts can be shorter?"
    **Response:** {{"next_agent": "solutions_agent"}}

    **User Query:** "please create a github issue to repository agentic-log-attacker, containing info for recommendation 6"
    **Response:** {{"next_agent": "github_issue_manager", "repo_url": "https://github.com/example/agentic-log-attacker", "issue_content": "Consider CUDA Compilation Configuration: Explicitly setting `TORCH_CUDA_ARCH_LIST` (if the GPU architecture is known) could lead to slightly faster compilation and more optimized kernels."}}

    **User Query:** "please create a github issue to repository vllm-container-prewarm, as a feature request to enable the \"Caching Compiled Kernels\" option"
    **Response:** {{"next_agent": "github_issue_manager", "repo_url": "https://github.com/example/vllm-container-prewarm"}}

    **User Query:** "no, I want you to create the issue in Github"
    **Response:** {{"next_agent": "github_issue_manager", "repo_url": "https://github.com/example/vllm-container-prewarm"}}

    **User Query:** "create a github issue"
    **Response:** {{"next_agent": "ask_for_repo_url"}}

    The conversation history is:
    {history_str}

    **User Query:** {user_query}
    **Response:**
    """

    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
    response = model.generate_content(prompt)
    response_text = response.text.strip()

    # Clean up any markdown formatting from the LLM response
    if response_text.startswith('```json') and response_text.endswith('```'):
        response_text = response_text[len('```json\n'):-len('\n```')]

    try:
        parsed_response = json.loads(response_text)
        next_agent = parsed_response.get("next_agent")
        repo_url = parsed_response.get("repo_url")
        issue_content = parsed_response.get("issue_content")
    except json.JSONDecodeError:
        # Fallback if LLM doesn't return valid JSON
        next_agent = response_text # Assume it's just the agent name
        repo_url = None

    return {"next_agent": next_agent, "repo_url": repo_url, "issue_content": issue_content, "history": [f"Routing to {next_agent}"]}
