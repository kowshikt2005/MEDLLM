"""
Request cancellation manager — tracks active streaming requests and allows cancellation.

This enables users to stop long-running queries (especially reasoning mode)
without waiting for completion or having to reload the page.

Architecture:
  - Each request gets a unique ID (already done in chat.py)
  - A global dict tracks if each request should be cancelled
  - The event_generator checks this flag periodically
  - Frontend calls /api/cancel?request_id=X to trigger cancellation
  - Generator yields a "cancelled" event and stops early
"""

import asyncio
from typing import Set

# Track active requests and which active requests are marked cancelled.
_active_requests: Set[str] = set()
_cancelled_requests: Set[str] = set()
_cancellation_lock = asyncio.Lock()


async def register_active(request_id: str) -> None:
    """Register a request as active when streaming starts."""
    async with _cancellation_lock:
        _active_requests.add(request_id)


async def mark_cancelled(request_id: str) -> bool:
    """
    Mark a request as cancelled.
    
    Returns True only for active requests, False if request is unknown.
    """
    async with _cancellation_lock:
        if request_id not in _active_requests:
            return False
        _cancelled_requests.add(request_id)
        print(f"[Cancellation] Request {request_id} marked for cancellation")
        return True
 

async def is_active(request_id: str) -> bool:
    """Check if a request is currently active."""
    async with _cancellation_lock:
        return request_id in _active_requests


async def is_cancelled(request_id: str) -> bool:
    """Check if a request has been marked for cancellation."""
    async with _cancellation_lock:
        return request_id in _cancelled_requests


async def clear_cancellation(request_id: str) -> None:
    """Clean up active/cancelled tracking after request completion."""
    async with _cancellation_lock:
        _active_requests.discard(request_id)
        _cancelled_requests.discard(request_id)


def get_active_request_count() -> int:
    """Return number of currently active requests."""
    return len(_active_requests)


def get_cancelled_request_count() -> int:
    """Return number of requests currently marked cancelled."""
    return len(_cancelled_requests)
