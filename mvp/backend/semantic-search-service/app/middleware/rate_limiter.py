"""
Rate limiting middleware for API endpoints
"""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.
    For production, consider using Redis-based solution.
    """

    def __init__(self, requests_per_minute: int = 60, window_minutes: int = 1):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_minutes * 60
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()

    def _clean_old_requests(self, user_requests: deque, current_time: float) -> None:
        """Remove requests older than the window"""
        cutoff_time = current_time - self.window_seconds
        while user_requests and user_requests[0] < cutoff_time:
            user_requests.popleft()

    def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if the identifier has exceeded the rate limit.
        Returns True if within limit, False if exceeded.
        """
        current_time = time.time()

        with self.lock:
            user_requests = self.requests[identifier]
            self._clean_old_requests(user_requests, current_time)

            if len(user_requests) >= self.requests_per_minute:
                return False

            user_requests.append(current_time)
            return True

    def get_reset_time(self, identifier: str) -> Optional[int]:
        """Get the time in seconds until the rate limit resets for this identifier"""
        with self.lock:
            user_requests = self.requests.get(identifier)
            if not user_requests:
                return None

            oldest_request = user_requests[0]
            reset_time = int(oldest_request + self.window_seconds - time.time())
            return max(0, reset_time)


# Global rate limiters for different operations
reference_creation_limiter = RateLimiter(requests_per_minute=30, window_minutes=1)
reference_search_limiter = RateLimiter(requests_per_minute=60, window_minutes=1)
voting_limiter = RateLimiter(
    requests_per_minute=30, window_minutes=1
)  # Prevent vote spam


async def check_reference_creation_rate_limit(request: Request):
    """
    Dependency to check rate limit for reference creation.
    Uses X-User header as identifier.
    """
    user = request.headers.get("X-User", "anonymous")

    if not reference_creation_limiter.check_rate_limit(user):
        reset_time = reference_creation_limiter.get_reset_time(user)
        logger.warning(f"Rate limit exceeded for user {user} on reference creation")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please try again in {reset_time} seconds.",
            headers={"Retry-After": str(reset_time)},
        )


async def check_reference_search_rate_limit(request: Request):
    """
    Dependency to check rate limit for reference searches.
    Uses X-User header as identifier.
    """
    user = request.headers.get("X-User", "anonymous")

    if not reference_search_limiter.check_rate_limit(user):
        reset_time = reference_search_limiter.get_reset_time(user)
        logger.warning(f"Rate limit exceeded for user {user} on reference search")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please try again in {reset_time} seconds.",
            headers={"Retry-After": str(reset_time)},
        )


async def check_voting_rate_limit(request: Request):
    """
    Dependency to check rate limit for voting operations.
    Uses X-User header as identifier.
    """
    user = request.headers.get("X-User", "anonymous")

    if not voting_limiter.check_rate_limit(user):
        reset_time = voting_limiter.get_reset_time(user)
        logger.warning(f"Rate limit exceeded for user {user} on voting")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please try again in {reset_time} seconds.",
            headers={"Retry-After": str(reset_time)},
        )
