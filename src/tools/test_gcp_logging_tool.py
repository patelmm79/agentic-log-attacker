
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.tools.gcp_logging_tool import get_gcp_logs

if __name__ == "__main__":
    load_dotenv()
    print("--- Testing GCP Logging Tool ---")
    logs = get_gcp_logs()
    print("--- Logs ---")
    print(logs)
    print("--------------")
