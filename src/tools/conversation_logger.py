import os
from datetime import datetime

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def log_conversation(user_message: str, bot_response: str):
    """Logs a user message and a bot response to a file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = os.path.join(LOG_DIR, "conversation_log.txt")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] User: {user_message}\n")
        f.write(f"[{timestamp}] Bot: {bot_response}\n")
        f.write("-" * 20 + "\n")

