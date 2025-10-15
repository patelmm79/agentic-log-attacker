import google.generativeai as genai
import json

def supervisor_agent(user_query: str, conversation_history: list):
    """A supervisor agent that routes requests to other agents using a few-shot prompting strategy."""

    history_str = "\n".join([f"User: {u}\nAgent: {a}" for u, a in conversation_history])

    prompt = f"""You are a supervisor agent. Your job is to route user requests to the correct agent.
    If the user wants to create a GitHub issue, you must also extract the GitHub repository URL from the user's query.
    If a full URL is not provided, assume the owner is 'example' and construct the full URL.
    If you cannot confidently determine the 'repo_url' for a GitHub issue creation request, return {{"next_agent": "ask_for_repo_url"}}.

    Here are the available agents and their capabilities:

    - **log_explorer**: Answers questions about logs and explores potential issues.
    - **github_issue_manager**: Creates GitHub issues. Requires a 'repo_url'.
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

    **User Query:** "please create a github issue to repository vllm-container-prewarm, as a feature request to enable the \"Caching Compiled Kernels\" option"
    **Response:** {{"next_agent": "github_issue_manager", "repo_url": "https://github.com/example/vllm-container-prewarm"}}

    **User Query:** "no, I want you to create the issue in Github"
    **Response:** {{"next_agent": "github_issue_manager", "repo_url": "https://github.com/example/vllm-container-prewarm"}}

    **User Query:** "create a github issue"
    **Response:** {{"next_agent": "ask_for_repo_url"}}

    {history_str}

    **User Query:** {user_query}
    **Response:**
    """

    model = genai.GenerativeModel('models/gemini-pro-latest')
    response = model.generate_content(prompt)
    response_text = response.text.strip()

    # Clean up any markdown formatting from the LLM response
    if response_text.startswith('```json') and response_text.endswith('```'):
        response_text = response_text[len('```json\n'):-len('\n```')]

    try:
        parsed_response = json.loads(response_text)
        next_agent = parsed_response.get("next_agent")
        repo_url = parsed_response.get("repo_url")
    except json.JSONDecodeError:
        # Fallback if LLM doesn't return valid JSON
        next_agent = response_text # Assume it's just the agent name
        repo_url = None

    return {"next_agent": next_agent, "repo_url": repo_url, "history": [f"Routing to {next_agent}"]}
