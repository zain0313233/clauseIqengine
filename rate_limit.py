import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from starlette.responses import Response

_WINDOW_SEC = int(os.getenv("ENGINE_RATE_LIMIT_WINDOW_SEC", "60"))
_MAX_REQUESTS = int(os.getenv("ENGINE_RATE_LIMIT_MAX", "120"))

_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
  forwarded = request.headers.get("x-forwarded-for")
  if forwarded:
    return forwarded.split(",")[0].strip()
  if request.client:
    return request.client.host
  return "unknown"


async def rate_limit_middleware(request: Request, call_next) -> Response:
  if request.url.path == "/health":
    return await call_next(request)

  key = _client_key(request)
  now = time.monotonic()
  bucket = _buckets[key]

  while bucket and now - bucket[0] > _WINDOW_SEC:
    bucket.popleft()

  if len(bucket) >= _MAX_REQUESTS:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")

  bucket.append(now)
  return await call_next(request)
