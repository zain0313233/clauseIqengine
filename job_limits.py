import asyncio
import os

from fastapi import HTTPException

_MAX_CONCURRENT = int(os.getenv("ENGINE_MAX_CONCURRENT_JOBS", "3"))

_job_semaphore = asyncio.Semaphore(_MAX_CONCURRENT)


def reject_if_queue_full() -> None:
    """Reject new background jobs when all worker slots are in use."""
    if _job_semaphore.locked():
        raise HTTPException(status_code=429, detail="Processing queue full")


class job_slot:
    """Limit concurrent embed/LLM background work per worker."""

    async def __aenter__(self):
        await _job_semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        _job_semaphore.release()
        return False
