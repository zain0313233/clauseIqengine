import os

from fastapi import Header, HTTPException

_ENGINE_SECRET: str | None = None


def get_engine_secret() -> str:
    global _ENGINE_SECRET
    if _ENGINE_SECRET is None:
        secret = os.environ.get("ENGINE_API_SECRET")
        if not secret:
            raise RuntimeError("ENGINE_API_SECRET environment variable is required")
        _ENGINE_SECRET = secret
    return _ENGINE_SECRET


async def verify_engine_auth(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.removeprefix("Bearer ").strip()
    if token != get_engine_secret():
        raise HTTPException(status_code=401, detail="Unauthorized")
