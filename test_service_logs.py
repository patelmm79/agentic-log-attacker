"""Test script to diagnose log fetching for a specific service."""
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging to see everything
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Import after setting up logging
from src.tools.gcp_logging_tool import get_gcp_logs

# Test with your service
service_name = "vllm-gemma-3-1b-it"

print("=" * 70)
print(f"Testing log retrieval for service: {service_name}")
print("=" * 70)

logs, _, error = get_gcp_logs(service_name=service_name, limit=10)

print("\n" + "=" * 70)
print("RESULTS:")
print("=" * 70)

if error:
    print(f"❌ ERROR: {error}")
elif logs:
    print(f"✓ SUCCESS! Retrieved logs")
    print(f"\nFirst 500 characters of logs:\n{logs[:500]}")
    print(f"\n... (total length: {len(logs)} characters)")
else:
    print("❌ No logs found")
    print("\nPlease check the diagnostic output above to see which filters were tried.")
