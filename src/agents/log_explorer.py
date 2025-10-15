import google.generativeai as genai

from src.tools.gcp_logging_tool import get_gcp_logs

def log_explorer_agent(service_name: str, user_query: str, conversation_history: list = None, start_time: str = None, end_time: str = None) -> str:
    """Dynamically answers questions about log content and explores potential issues."""
    
    logs, _, error = get_gcp_logs(service_name=service_name, limit=1000, start_time=start_time, end_time=end_time)

    if error:
        return f"I couldn't fetch any logs. Please ensure the service name is correct and that I have the right permissions. Error: {error}"
    if not logs:
        return "No logs found for the specified service and time range."

    # Format the conversation history
    formatted_history = ""
    if conversation_history:
        for user, bot in conversation_history:
            formatted_history += f"User: {user}\nBot: {bot}\n"

    prompt = f"""You are a helpful log analysis assistant. Answer the user's question based on the provided conversation history and the latest logs.

    Conversation History:
    {formatted_history}

    Latest Logs:
    {logs}

    User Question: {user_query}
    """

    model = genai.GenerativeModel('models/gemini-pro-latest')
    response = model.generate_content(prompt)
    return response.text
