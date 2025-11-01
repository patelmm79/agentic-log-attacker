import os
import sys
import gradio as gr
import uuid
from langchain_core.messages import HumanMessage

from src.main import app
from src.tools.conversation_logger import log_conversation

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def chat_session(message: str, history: list, thread_id: str):
    """Manages a single chat session, maintaining state between turns."""
    print("--- chat_session called ---")
    print(f"Message: {message}")
    print(f"Thread ID: {thread_id}")

    if thread_id is None:
        thread_id = str(uuid.uuid4())
        print(f"New Thread ID: {thread_id}")

    # Invoke the agentic workflow
    response = app.invoke(
        {"messages": [HumanMessage(content=message)]},
        {"configurable": {"thread_id": thread_id}}
    )
    print(f"Response from app.invoke: {response}")

    # Get the latest response from the agent
    next_agent = response.get('next_agent')
    if next_agent == "github_issue_manager" and 'github_issue_manager_history' in response and response['github_issue_manager_history']:
        bot_message = response['github_issue_manager_history'][-1]
    elif 'suggested_fix' in response and response['suggested_fix']:
        bot_message = response['suggested_fix']
    elif 'orchestrator_history' in response and response['orchestrator_history']:
        bot_message = response['orchestrator_history'][-1]
    else:
        bot_message = "I'm sorry, I couldn't process that request."
    print(f"Final bot_message before returning: {bot_message}")

    return bot_message, thread_id

with gr.Blocks() as demo:
    # The state object to hold the thread_id across calls
    state = gr.State({"thread_id": None})

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
        thread_id = state["thread_id"]
        bot_response, new_thread_id = chat_session(message, history, thread_id)
        print(f"Bot Response from chat_session: {bot_response}")
        print(f"New Thread ID from chat_session: {new_thread_id}")
        updated_history = history + [(message, bot_response)]
        print(f"Updated History before returning: {updated_history}")
        return updated_history, {"thread_id": new_thread_id}, ""

    txt.submit(on_submit, [txt, chatbot, state], [chatbot, state, txt])

if __name__ == "__main__":
    demo.launch(share=True)