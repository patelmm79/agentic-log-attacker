"""Debug script to check Cloud Run logging configuration."""
import os
import argparse
from datetime import datetime, timedelta
from google.cloud.logging import Client

# Parse command line arguments
parser = argparse.ArgumentParser(description='Debug Cloud Run logging configuration')
parser.add_argument('--hours', type=int, default=24, help='Number of hours to look back (default: 24)')
parser.add_argument('--days', type=int, help='Number of days to look back (overrides --hours)')
parser.add_argument('--service', type=str, required=True, help='Service name to query (required)')
args = parser.parse_args()

# Set up client
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not project_id:
    print("ERROR: GOOGLE_CLOUD_PROJECT environment variable not set")
    exit(1)

print(f"Project ID: {project_id}")
client = Client(project=project_id)

service_name = args.service

# Calculate time range
end_time = datetime.utcnow()
if args.days:
    start_time = end_time - timedelta(days=args.days)
    lookback_str = f"{args.days} day(s)"
else:
    start_time = end_time - timedelta(hours=args.hours)
    lookback_str = f"{args.hours} hour(s)"

time_filter = f' AND timestamp >= "{start_time.isoformat()}Z" AND timestamp <= "{end_time.isoformat()}Z"'
print(f"Service: {service_name}")
print(f"Time range: Last {lookback_str}")
print(f"  Start: {start_time.isoformat()}Z")
print(f"  End:   {end_time.isoformat()}Z")

# Test 1: Check if any Cloud Run logs exist (with time filter)
print("\n=== Test 1: Any Cloud Run logs (with time range) ===")
filter1 = f'resource.type = "cloud_run_revision"{time_filter}'
print(f"Filter: {filter1}")
entries1 = list(client.list_entries(filter_=filter1, page_size=5))
print(f"Found {len(entries1)} Cloud Run log entries")
if entries1:
    print("\nFirst entry resource labels:")
    print(entries1[0].resource.labels)
    print(f"First entry timestamp: {entries1[0].timestamp}")

# Test 2: Try the current filter with severity
print(f"\n=== Test 2: Current filter for {service_name} with severity ===")
filter2 = f'resource.type = "cloud_run_revision" AND resource.labels.service_name = "{service_name}" AND severity >= DEFAULT{time_filter}'
print(f"Filter: {filter2}")
entries2 = list(client.list_entries(filter_=filter2, page_size=5))
print(f"Found {len(entries2)} log entries")
if entries2:
    print(f"Latest log timestamp: {entries2[0].timestamp}")

# Test 3: Try with configuration_name (alternative label) with severity
print(f"\n=== Test 3: Try configuration_name label with severity ===")
filter3 = f'resource.type = "cloud_run_revision" AND resource.labels.configuration_name = "{service_name}" AND severity >= DEFAULT{time_filter}'
print(f"Filter: {filter3}")
entries3 = list(client.list_entries(filter_=filter3, page_size=5))
print(f"Found {len(entries3)} log entries")
if entries3:
    print(f"Latest log timestamp: {entries3[0].timestamp}")

# Test 4: List all unique service names from Cloud Run logs (with time filter)
print("\n=== Test 4: Available Cloud Run services (in time range) ===")
filter4 = f'resource.type = "cloud_run_revision"{time_filter}'
entries4 = list(client.list_entries(filter_=filter4, page_size=100))
service_names = set()
for entry in entries4:
    if 'service_name' in entry.resource.labels:
        service_names.add(entry.resource.labels['service_name'])
    if 'configuration_name' in entry.resource.labels:
        service_names.add(entry.resource.labels['configuration_name'])

print(f"Found services: {sorted(service_names)}")

# Test 5: Search by partial match (with time filter)
print(f"\n=== Test 5: Partial match search for 'vllm' or 'gemma' ===")
filter5 = f'resource.type = "cloud_run_revision"{time_filter}'
entries5 = list(client.list_entries(filter_=filter5, page_size=100))
matches = []
for entry in entries5:
    labels = entry.resource.labels
    for key, value in labels.items():
        if 'vllm' in value.lower() or 'gemma' in value.lower():
            matches.append({key: value})
            break

print(f"Found {len(matches)} matching entries")
if matches:
    print("Sample matches:")
    for match in matches[:5]:
        print(f"  {match}")
