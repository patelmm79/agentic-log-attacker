import os
import google.generativeai as genai
from langchain_core.messages import HumanMessage, AIMessage

from src.tools.gcp_logging_tool import get_gcp_logs

def log_explorer_agent(service_name: str, user_query: str, service_type: str = "cloud_run", conversation_history: list = None, start_time: str = None, end_time: str = None) -> str:
    """Dynamically answers questions about log content and explores potential issues."""

    logs, _, error = get_gcp_logs(service_name=service_name, service_type=service_type, limit=1000, start_time=start_time, end_time=end_time)

    if error:
        return f"I couldn't fetch any logs. Please ensure the service name is correct and that I have the right permissions. Error: {error}"
    if not logs:
        service_type_display = service_type.replace('_', ' ').title()
        return f"""No logs found for {service_type_display} service '{service_name}'.

Possible reasons:
1. The service name might be incorrect (check for typos)
2. The service exists but has no recent logs
3. The logs might use a different label name (check server logs for filter attempts)
4. You may not have the correct permissions to access logs for this service

Debug information has been logged to the server console. Please check the uvicorn/FastAPI logs for detailed filter attempts."""

    # Pre-process logs for large volumes or specific queries
    processed_logs = logs
    if len(logs.splitlines()) > 200 or "summarize" in user_query.lower() or "summary" in user_query.lower():
        summarization_prompt = f"""The following are logs for a service. Summarize the key events, errors, or relevant information related to the user's question.

        User Question: {user_query}
        Logs:
        {logs}

        Provide a concise summary of the most relevant log entries. If the user asks for a summary, provide it in a structured format (e.g., bullet points or a brief paragraph).
        """
        summarization_model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
        summarization_response = summarization_model.generate_content(summarization_prompt)
        processed_logs = summarization_response.text

    # Format the conversation history
    formatted_history = ""
    if conversation_history:
        for msg in conversation_history:
            if isinstance(msg, HumanMessage):
                formatted_history += f"User: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                formatted_history += f"Bot: {msg.content}\n"

    prompt = f"""You are a helpful log analysis assistant. Answer the user's question based on the provided conversation history and the processed logs.

    Conversation History:
    {formatted_history}

    Processed Logs:
    {processed_logs}

    User Question: {user_query}

    If the user asks for a summary or specific structured information, provide it in a clear and concise structured format (e.g., bullet points, numbered list, or a brief JSON snippet if appropriate).
    """

    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
    response = model.generate_content(prompt)
    print(f"Log Explorer Agent Raw Response: {response}")
    print(f"Log Explorer Agent Response Text: {response.text}")
    return response.text
