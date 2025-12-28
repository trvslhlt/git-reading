"""Rate limiting utilities for API clients."""

import time
from collections import deque
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class RateLimiter:
    """Token bucket rate limiter for API clients.

    This implementation uses a sliding window approach to track requests
    and ensures API rate limits are respected.

    Example:
        >>> limiter = RateLimiter(requests_per_period=60, period_seconds=60)
        >>> limiter.wait_if_needed()  # Blocks if rate limit would be exceeded
    """

    def __init__(self, requests_per_period: int, period_seconds: int):
        """Initialize rate limiter.

        Args:
            requests_per_period: Maximum number of requests allowed per period
            period_seconds: Time period in seconds for the rate limit window
        """
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.request_times: deque[float] = deque()

    def wait_if_needed(self) -> None:
        """Block execution if making another request would exceed the rate limit.

        This method should be called before each API request.
        It will sleep if necessary to stay within the rate limit.
        """
        now = time.time()

        # Remove requests outside the sliding window
        while self.request_times and self.request_times[0] < now - self.period_seconds:
            self.request_times.popleft()

        # If at limit, wait until oldest request expires
        if len(self.request_times) >= self.requests_per_period:
            sleep_time = (
                self.period_seconds - (now - self.request_times[0]) + 0.1
            )  # Add small buffer
            if sleep_time > 0:
                time.sleep(sleep_time)

            # Clean up again after sleeping
            now = time.time()
            while self.request_times and self.request_times[0] < now - self.period_seconds:
                self.request_times.popleft()

        # Record this request
        self.request_times.append(time.time())

    def reset(self) -> None:
        """Clear all tracked requests (useful for testing)."""
        self.request_times.clear()


def rate_limited(limiter: RateLimiter) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to apply rate limiting to a function.

    Args:
        limiter: RateLimiter instance to use

    Returns:
        Decorated function that respects rate limits

    Example:
        >>> limiter = RateLimiter(60, 60)
        >>> @rate_limited(limiter)
        ... def fetch_data():
        ...     return requests.get('https://api.example.com/data')
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            limiter.wait_if_needed()
            return func(*args, **kwargs)

        return wrapper

    return decorator
