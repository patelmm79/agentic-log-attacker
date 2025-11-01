import re
import os
from src.tools.gcp_logging_tool import get_gcp_logs
import google.generativeai as genai

def solutions_agent(issue: dict, user_query: str, service_name: str):
    print("--- Solutions Agent called ---")
    issue_title = issue.get('title', user_query)
    print(f"Solutions agent is providing a solution for: {issue_title}")

    # Use the provided service_name directly
    logs, _, error = get_gcp_logs(service_name=service_name, limit=100)

    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))

    if error:
        solution_text = f"Could not fetch logs for service '{service_name}' due to an error: {error}. Please check the service name and permissions."
    elif not logs:
        solution_text = f"No logs found for service '{service_name}'. It's difficult to propose a solution without logs. Consider checking if the service is running or if the logs are being exported correctly. Based on your query: '{user_query}', a potential solution could involve optimizing the cold start process by pre-warming the service or caching frequently used resources."
    else:
        # Use the LLM to analyze the logs in the context of the user query
        log_analysis_prompt = f"""You are an expert in analyzing Google Cloud Run logs and providing solutions for performance optimization, especially related to cold starts and specific technical issues like CUDA graph capturing.

Here is a user's query: "{user_query}"

Here are the recent logs for the service '{service_name}':
{logs}

Based on the user's query and the provided logs, please provide a detailed solution or set of recommendations in a numbered list format. Focus on: 
1. Identifying any relevant information in the logs related to the query.
2. Explaining how this information relates to the query.
3. Proposing concrete, actionable steps to address the user's concern, especially regarding cold start optimization, CUDA graph caching, or build stage improvements. If the logs don't directly address the query, provide general but detailed best practices for the mentioned topics.

Your response should be comprehensive, easy to understand, and clearly numbered for each recommendation."""
        print("--- Calling LLM for log analysis ---")
        response = model.generate_content(log_analysis_prompt)
        print("--- LLM call returned ---")
        if response.text:
            solution_text = response.text
        else:
            solution_text = "The model did not return a solution. This might be due to safety settings or an empty response. Please try rephrasing your query."

    print(f"Solutions agent final solution_text: {solution_text}")
    return solution_text
    return solution_text
