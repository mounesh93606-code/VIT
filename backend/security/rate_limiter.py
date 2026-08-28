import time
from collections import defaultdict
from fastapi import Request, HTTPException, status

class SimpleRateLimiter:
    """In-memory IP rate limiter to protect authentication and resource-intensive endpoints from brute-force & DoS attacks."""
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.ip_history = defaultdict(list)

    def check_rate_limit(self, request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        
        # Clean timestamps older than 60 seconds
        timestamps = [t for t in self.ip_history[client_ip] if now - t < 60]
        self.ip_history[client_ip] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Too many requests. Please try again later.",
                headers={"Retry-After": "60"}
            )
        
        self.ip_history[client_ip].append(now)

auth_rate_limiter = SimpleRateLimiter(requests_per_minute=100)
ai_rate_limiter = SimpleRateLimiter(requests_per_minute=100)
