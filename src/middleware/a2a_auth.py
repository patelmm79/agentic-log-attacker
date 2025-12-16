"""
A2A Authentication middleware for Google Cloud service account tokens.

Handles bearer token validation and service account whitelist checking.
"""

from fastapi import Header, HTTPException, Depends
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
import logging

logger = logging.getLogger(__name__)


class A2AAuthenticator:
    """Authenticates A2A requests using Google Cloud identity tokens."""

    def __init__(self):
        """Initialize authenticator with allowed service accounts from environment."""
        allowed = os.getenv('ALLOWED_SERVICE_ACCOUNTS', '')
        self.allowed_service_accounts = set(
            account.strip() for account in allowed.split(',') if account.strip()
        )
        logger.info(f"Allowed service accounts initialized: {len(self.allowed_service_accounts)} account(s)")
        if not self.allowed_service_accounts:
            logger.warning(
                "No ALLOWED_SERVICE_ACCOUNTS configured. "
                "All authenticated A2A requests will be rejected."
            )

    async def verify_token(self, authorization: str = Header(None)) -> str:
        """
        Verify Google Cloud identity token and return service account email.

        Args:
            authorization: Authorization header value (e.g., "Bearer <token>")

        Returns:
            Service account email address

        Raises:
            HTTPException: If token is invalid, missing, or not whitelisted
        """
        if not authorization:
            logger.warning("A2A request missing authorization header")
            raise HTTPException(
                status_code=401,
                detail="Missing authorization header"
            )

        if not authorization.startswith("Bearer "):
            logger.warning("A2A request has invalid authorization format")
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization format. Expected 'Bearer <token>'"
            )

        token = authorization[7:]  # Remove "Bearer " prefix

        try:
            # Verify the token with Google's public keys
            request = google_requests.Request()
            id_info = id_token.verify_oauth2_token(token, request)

            # Extract service account email
            email = id_info.get('email')
            if not email:
                logger.warning("Token does not contain email claim")
                raise HTTPException(
                    status_code=401,
                    detail="Token missing email claim"
                )

            # Check whitelist
            if email not in self.allowed_service_accounts:
                logger.warning(f"Unauthorized service account attempted access: {email}")
                raise HTTPException(
                    status_code=403,
                    detail=f"Service account {email} not authorized for A2A access"
                )

            logger.info(f"Successfully authenticated A2A request from: {email}")
            return email

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token verification failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=401,
                detail=f"Token verification failed: {str(e)}"
            )


# Create singleton instance
authenticator = A2AAuthenticator()
