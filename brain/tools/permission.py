# ============================================================
# LavOS 2026 — brain/tools/permission.py  (the trust layer)
# Gatekeeper: before Vision reads screen/files/searches the web,
# it asks permission. For the hackathon demo, this is synchronous
# (blocking) with a timeout. In production, async via Socket.io.
# ============================================================

import threading
from typing import Optional
from brain.config import ASK_BEFORE_SENSITIVE, ACTION_TIMEOUT_S

# Permission state — set by the UI via Socket.io
_pending: dict = {}
_lock = threading.Lock()
_events: dict[str, threading.Event] = {}


def _get_or_create_event(aid: str) -> threading.Event:
    """Get or create a per-request event for a given action ID."""
    with _lock:
        if aid not in _events:
            _events[aid] = threading.Event()
        return _events[aid]


def ask_permission(description: str, action_id: Optional[str] = None, **_) -> dict:
    """
    Ask user for permission. In demo mode, auto-approves after timeout.
    The UI pushes Yes/No via grant_permission() or deny_permission().
    """
    if not ASK_BEFORE_SENSITIVE:
        return {"ok": True, "result": "Auto-approved (permission gate disabled)", "data": {}}

    aid = action_id or f"perm_{id(description)}"
    event = _get_or_create_event(aid)
    event.clear()

    with _lock:
        _pending[aid] = {"description": description, "status": "pending"}

    # Block until user responds or timeout
    granted = event.wait(timeout=ACTION_TIMEOUT_S)

    with _lock:
        entry = _pending.pop(aid, {})
        _events.pop(aid, None)
        if not granted:
            return {"ok": False, "result": "Permission denied (timeout)", "data": {"id": aid}}

        status = entry.get("status", "denied")
        if status == "granted":
            return {"ok": True, "result": f"Approved: {description}", "data": {"id": aid}}
        return {"ok": False, "result": f"Denied: {description}", "data": {"id": aid}}


def grant_permission(action_id: str) -> None:
    """Called by the UI when user clicks Yes."""
    with _lock:
        if action_id in _pending:
            _pending[action_id]["status"] = "granted"
        event = _events.get(action_id)
    if event:
        event.set()


def deny_permission(action_id: str) -> None:
    """Called by the UI when user clicks No."""
    with _lock:
        if action_id in _pending:
            _pending[action_id]["status"] = "denied"
        event = _events.get(action_id)
    if event:
        event.set()


def get_pending() -> dict:
    """Return pending permission requests for the UI."""
    with _lock:
        return dict(_pending)
