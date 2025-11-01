
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

### Running Locally (FastAPI)

To run the FastAPI application locally:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

The API will be available at `http://localhost:8080`. You can access the interactive API documentation at `http://localhost:8080/docs`.

To trigger the agent workflow, send a POST request to `/run_workflow` with a JSON body containing your query:

```json
{
  "user_query": "Your query here, e.g., 'review logs for cloud run service my-service'"
}
```

## Deployment to Google Cloud Run

This project can be deployed to Google Cloud Run using Google Cloud Build. A `cloudbuild.yaml` file is provided for this purpose.

1.  **Ensure you have Google Cloud SDK installed and authenticated.**
2.  **Submit the build to Cloud Build:**

    ```bash
    gcloud builds submit --config cloudbuild.yaml .
    ```

    This command will build the Docker image, push it to Google Container Registry, and deploy it to Cloud Run. The service will be named `agentic-log-attacker` in the `us-central1` region (these can be customized in `cloudbuild.yaml`).

## Workflow

![Workflow Visualization](workflow.png)
