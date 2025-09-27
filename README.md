
# Agentic Log Attacker

This project is a Python-based application that uses AI agents to monitor logs from a Google Cloud Run service, identify potential issues, and automatically create pull requests with suggested fixes.

## Features

- **Log Monitoring:** Monitors logs from a configurable Google Cloud Run service.
- **Issue Detection:** Uses the Gemini API to analyze logs and identify potential issues.
- **GitHub Integration:** Creates GitHub issues for identified problems.
- **Automated Code Fixes:** Generates code fixes using the Gemini API.
- **Automated Pull Requests:** Creates pull requests with the suggested fixes.

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set up your environment variables:**

   Create a `.env` file in the root of the project and add the following:

   ```
   GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
   GITHUB_REPOSITORY="YOUR_GITHUB_REPOSITORY"
   GOOGLE_CLOUD_PROJECT="YOUR_GOOGLE_CLOUD_PROJECT"
   CLOUD_RUN_SERVICE_NAME="YOUR_CLOUD_RUN_SERVICE_NAME"
   CLOUD_RUN_REGION="YOUR_CLOUD_RUN_REGION"
   ```

3. **Authenticate with Google Cloud:**

   ```bash
   gcloud auth application-default login
   ```

## Usage

To run the application, simply execute the following command:

```bash
python3 src/main.py
```
