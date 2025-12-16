"""
Simple in-memory rate limiter for A2A endpoint.

Implements token bucket rate limiting per service account.
"""

from fastapi import HTTPException
import time
from collections import defaultdict
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter using token bucket algorithm."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        logger.info(
            f"Rate limiter initialized: {max_requests} requests per {window_seconds} seconds"
        )

    async def check_rate_limit(self, caller: str):
        """
        Check if caller has exceeded rate limit.

        Args:
            caller: Service account email

        Raises:
            HTTPException: If rate limit exceeded
        """
        now = time.time()

        # Clean old requests outside the time window
        self.requests[caller] = [
            req_time for req_time in self.requests[caller]
            if now - req_time < self.window_seconds
        ]

        # Check if limit exceeded
        current_requests = len(self.requests[caller])
        if current_requests >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for {caller}: "
                f"{current_requests}/{self.max_requests} requests in last {self.window_seconds}s"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.max_requests} requests per {self.window_seconds}s"
            )

        # Record this request
        self.requests[caller].append(now)
        logger.debug(f"Rate limit check passed for {caller}: {current_requests + 1}/{self.max_requests}")


# Create singleton instance
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
