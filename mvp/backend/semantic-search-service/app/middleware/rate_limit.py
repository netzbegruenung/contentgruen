from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Tuple


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for content creation endpoints.
    Limits the number of requests per user within a time window.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 10,
        requests_per_hour: int = 100,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.request_counts: Dict[str, Dict[str, Tuple[int, datetime]]] = defaultdict(
            lambda: {"minute": (0, datetime.now()), "hour": (0, datetime.now())}
        )
        self.cleanup_task = None

    async def dispatch(self, request: Request, call_next):
        # Only apply rate limiting to POST endpoints for content creation
        if request.method == "POST" and any(
            path in str(request.url.path)
            for path in [
                "/addGenericText",
                "/addCommentary",
                "/addStatement",
                "/addReference",
                "/suggestCaption",
                # Der Fangkorb ist per Konstruktion schnell zu bedienen und
                # damit auch schnell zu fluten.
                "/addRawInput",
            ]
        ):
            # Extract user identifier from X-User header
            user_id = request.headers.get("X-User", "anonymous")

            # Check rate limits
            if not self._check_rate_limit(user_id):
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please wait before making another request.",
                        "error": "TOO_MANY_REQUESTS",
                    },
                )

        response = await call_next(request)

        # Start cleanup task if not running
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_old_entries())

        return response

    def _check_rate_limit(self, user_id: str) -> bool:
        """
        Check if the user has exceeded rate limits.
        Returns True if request is allowed, False if rate limit exceeded.
        """
        now = datetime.now()
        user_counts = self.request_counts[user_id]

        # Check minute limit
        minute_count, minute_start = user_counts["minute"]
        if now - minute_start > timedelta(minutes=1):
            # Reset minute counter
            user_counts["minute"] = (1, now)
        else:
            if minute_count >= self.requests_per_minute:
                return False
            user_counts["minute"] = (minute_count + 1, minute_start)

        # Check hour limit
        hour_count, hour_start = user_counts["hour"]
        if now - hour_start > timedelta(hours=1):
            # Reset hour counter
            user_counts["hour"] = (1, now)
        else:
            if hour_count >= self.requests_per_hour:
                return False
            user_counts["hour"] = (hour_count + 1, hour_start)

        return True

    async def _cleanup_old_entries(self):
        """
        Periodically clean up old entries from request_counts to prevent memory leak.
        """
        while True:
            await asyncio.sleep(3600)  # Run every hour
            now = datetime.now()
            users_to_remove = []

            for user_id, counts in self.request_counts.items():
                _, hour_start = counts["hour"]
                if now - hour_start > timedelta(hours=2):
                    users_to_remove.append(user_id)

            for user_id in users_to_remove:
                del self.request_counts[user_id]
