"""Debug script to check Cloud Run logging configuration."""
import os
from google.cloud.logging import Client

# Set up client
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not project_id:
    print("ERROR: GOOGLE_CLOUD_PROJECT environment variable not set")
    exit(1)

print(f"Project ID: {project_id}")
client = Client(project=project_id)

service_name = "vllm-gemma-3-1b-it"

# Test 1: Check if any Cloud Run logs exist
print("\n=== Test 1: Any Cloud Run logs ===")
filter1 = 'resource.type = "cloud_run_revision"'
print(f"Filter: {filter1}")
entries1 = list(client.list_entries(filter_=filter1, page_size=5))
print(f"Found {len(entries1)} Cloud Run log entries")
if entries1:
    print("\nFirst entry resource labels:")
    print(entries1[0].resource.labels)

# Test 2: Try the current filter
print(f"\n=== Test 2: Current filter for {service_name} ===")
filter2 = f'resource.type = "cloud_run_revision" AND resource.labels.service_name = "{service_name}"'
print(f"Filter: {filter2}")
entries2 = list(client.list_entries(filter_=filter2, page_size=5))
print(f"Found {len(entries2)} log entries")

# Test 3: Try with configuration_name (alternative label)
print(f"\n=== Test 3: Try configuration_name label ===")
filter3 = f'resource.type = "cloud_run_revision" AND resource.labels.configuration_name = "{service_name}"'
print(f"Filter: {filter3}")
entries3 = list(client.list_entries(filter_=filter3, page_size=5))
print(f"Found {len(entries3)} log entries")

# Test 4: List all unique service names from Cloud Run logs
print("\n=== Test 4: Available Cloud Run services ===")
filter4 = 'resource.type = "cloud_run_revision"'
entries4 = list(client.list_entries(filter_=filter4, page_size=100))
service_names = set()
for entry in entries4:
    if 'service_name' in entry.resource.labels:
        service_names.add(entry.resource.labels['service_name'])
    if 'configuration_name' in entry.resource.labels:
        service_names.add(entry.resource.labels['configuration_name'])

print(f"Found services: {sorted(service_names)}")

# Test 5: Search by partial match
print(f"\n=== Test 5: Partial match search for 'vllm' or 'gemma' ===")
filter5 = 'resource.type = "cloud_run_revision"'
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
