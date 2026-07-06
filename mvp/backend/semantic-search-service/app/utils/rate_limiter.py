"""
Simple in-memory rate limiter for API endpoints.
"""

from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import asyncio


class RateLimiter:
    """
    Simple in-memory rate limiter.

    Tracks request timestamps per identifier (user_id or session_id).
    Automatically cleans up old entries.
    """

    def __init__(self, max_requests: int, window_minutes: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the time window
            window_minutes: Time window in minutes
        """
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self._requests: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_rate_limited(self, identifier: str) -> bool:
        """
        Check if identifier is rate limited.

        Args:
            identifier: User ID or session ID to check

        Returns:
            True if rate limited, False otherwise
        """
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.window

            # Get or create request list for this identifier
            requests = self._requests[identifier]

            # Remove old requests outside the window
            requests[:] = [req_time for req_time in requests if req_time > cutoff]

            # Check if limit exceeded BEFORE adding current request
            if len(requests) >= self.max_requests:
                return True

            # Only add timestamp if not rate limited
            requests.append(now)
            return False

    async def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for identifier.

        Args:
            identifier: User ID or session ID

        Returns:
            Number of remaining requests in current window
        """
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.window

            requests = self._requests.get(identifier, [])
            requests[:] = [req_time for req_time in requests if req_time > cutoff]

            return max(0, self.max_requests - len(requests))

    async def cleanup(self):
        """Remove all expired entries (for memory management)."""
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.window

            # Clean up old entries
            for identifier in list(self._requests.keys()):
                requests = self._requests[identifier]
                requests[:] = [req_time for req_time in requests if req_time > cutoff]

                # Remove empty lists
                if not requests:
                    del self._requests[identifier]


# Global rate limiters
# 5 reports per user/session per 15 minutes
report_rate_limiter = RateLimiter(max_requests=5, window_minutes=15)
