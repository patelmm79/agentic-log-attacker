import os
import sys
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.tools.gcp_logging_tool import get_gcp_logs

if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(description="Test GCP Logging Tool")
    parser.add_argument("service_name", help="The name of the Cloud Run service.")
    args = parser.parse_args()

    print("--- Testing GCP Logging Tool ---")
    logs = get_gcp_logs(args.service_name)
    print("--- Logs ---")
    print(logs)
    print("--------------")