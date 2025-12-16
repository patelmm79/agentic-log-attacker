"""
A2A (Agent-to-Agent) protocol models for dev-nexus integration.

Defines the request and response formats for A2A skill execution.
"""

from pydantic import BaseModel
from typing import Any, Optional


class A2ARequest(BaseModel):
    """Request model for A2A skill execution."""

    skill_id: str
    input: dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "skill_id": "analyze_and_monitor_logs",
                "input": {
                    "user_query": "analyze logs for cloud run service my-service",
                    "service_name": "my-service",
                    "service_type": "cloud_run",
                    "repo_url": "https://github.com/owner/repo"
                }
            }
        }


class A2AResponse(BaseModel):
    """Response model for A2A skill execution."""

    success: bool
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "result": {
                    "service_name": "my-service",
                    "service_type": "cloud_run",
                    "analysis": "Summary of log analysis",
                    "issues_identified": 3,
                    "issues_created": 2,
                    "github_issue_urls": [
                        "https://github.com/owner/repo/issues/42",
                        "https://github.com/owner/repo/issues/43"
                    ],
                    "orchestrator_history": ["supervisor", "log_explorer", "issue_creation"]
                },
                "execution_time_ms": 5432
            }
        }
