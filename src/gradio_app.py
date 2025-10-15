import os
import sys
import gradio as gr

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app, AgentState
from src.tools.conversation_logger import log_conversation

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def chat_session(message: str, history: list, state: dict):
    print("--- chat_session called ---")
    print(f"Message: {message}")
    print(f"Initial State: {state}")
    """Manages a single chat session, maintaining state between turns."""
    # If state is empty, initialize it
    if not state:
        state = {
            "cloud_run_service": os.environ.get("CLOUD_RUN_SERVICE"),
            "git_repo_url": os.environ.get("GIT_REPO_URL", "https://github.com/YOUR_GITHUB_USER/YOUR_GITHUB_REPO"), # IMPORTANT: Replace with your actual GitHub repo URL
            "user_query": "",
            "issues": [],
            "pull_requests": [],
            "orchestrator_history": [],
            "log_reviewer_history": [],
            "github_issue_manager_history": [],
            "suggested_fix": "",
            "conversation_history": []
        }

    # Update the state with the new user query
    state["user_query"] = message

    # Invoke the agentic workflow
    response = app.invoke(state)
    print(f"Response from app.invoke: {response}")

    # Get the latest response from the orchestrator history or the solution
    if response.get("suggested_fix"):
        bot_message = response["suggested_fix"]
    elif response.get("log_reviewer_history"):
        bot_message = response["log_reviewer_history"][-1]
    elif response.get("orchestrator_history"):
        bot_message = response["orchestrator_history"][-1]
    else:
        bot_message = "I'm sorry, I couldn't process that request."
    print(f"Bot Message: {bot_message}")

    # Log the conversation
    log_conversation(message, bot_message)

    # Update the conversation history in the state
    state["conversation_history"] = state.get("conversation_history", []) + [(message, bot_message)]

    # Update the state for the next turn
    new_state = response
    print(f"New State before returning: {new_state}")
    print(f"Final bot_message before returning: {bot_message}")

    return bot_message, new_state

with gr.Blocks() as demo:
    # The state object to hold the AgentState across calls
    state = gr.State({})

    gr.Markdown("<h1><center>Log Analysis Agent</center></h1>")
    gr.Markdown("Ask questions about the logs of your Cloud Run service.")

    chatbot = gr.Chatbot()

    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="Enter your message...")

    def on_submit(message, history, state):
        print("--- on_submit called ---")
        print(f"Message: {message}")
        print(f"History: {history}")
        print(f"State: {state}")
        bot_response, new_state = chat_session(message, history, state)
        print(f"Bot Response from chat_session: {bot_response}")
        print(f"New State from chat_session: {new_state}")
        updated_history = history + [(message, bot_response)]
        print(f"Updated History before returning: {updated_history}")
        return updated_history, new_state, ""

    txt.submit(on_submit, [txt, chatbot, state], [chatbot, state, txt])

if __name__ == "__main__":
    demo.launch(share=True)