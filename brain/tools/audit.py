# ============================================================
# LavOS 2026 — brain/tools/audit.py  (security audit trail)
# Logs every action Vision takes — what it looked at, searched,
# opened, copied. Append-only JSONL under storage/logs/.
# ============================================================

import json
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "logs"
AUDIT_FILE = LOGS_DIR / "audit.jsonl"

# Max entries to keep (FIFO — oldest trimmed)
MAX_ENTRIES = 500


def _ensure_dir():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log_action(action: str = "", detail: str = "", engine: str = "", **_) -> dict:
    """
    Append an audit entry.
    action: what happened (e.g. "screen_read", "web_search", "clipboard_set", "app_opened")
    detail: human-readable description
    engine: which brain answered (rules, local, nim, etc.)
    """
    if not action.strip():
        return {"ok": False, "result": "Empty action", "data": {}}

    _ensure_dir()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action.strip(),
        "detail": detail.strip(),
        "engine": engine.strip(),
    }

    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Trim if too many entries
        _trim_if_needed()

        return {"ok": True, "result": f"Logged: {action}", "data": entry}
    except Exception as e:
        return {"ok": False, "result": f"Audit write error: {e}", "data": {}}


def get_recent(n: int = 20, **_) -> dict:
    """Return the last N audit entries."""
    if not AUDIT_FILE.exists():
        return {"ok": True, "result": "No audit entries yet", "data": {"entries": []}}

    try:
        lines = AUDIT_FILE.read_text(encoding="utf-8").strip().splitlines()
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        entries.reverse()  # newest first

        text = "\n".join(
            f"[{e.get('ts','?')[:19]}] {e.get('action','?')}: {e.get('detail','?')}"
            for e in entries
        )
        return {"ok": True, "result": text or "No entries", "data": {"entries": entries}}
    except Exception as e:
        return {"ok": False, "result": f"Audit read error: {e}", "data": {}}


def clear_log(**_) -> dict:
    """Clear all audit entries (privacy reset)."""
    _ensure_dir()
    try:
        AUDIT_FILE.write_text("", encoding="utf-8")
        return {"ok": True, "result": "Audit log cleared", "data": {}}
    except Exception as e:
        return {"ok": False, "result": f"Clear error: {e}", "data": {}}


def _trim_if_needed():
    """Keep only the last MAX_ENTRIES entries."""
    try:
        if not AUDIT_FILE.exists():
            return
        lines = AUDIT_FILE.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) > MAX_ENTRIES:
            trimmed = lines[-MAX_ENTRIES:]
            AUDIT_FILE.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
    except Exception:
        pass  # never crash on trim


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    print("Audit log test")
    log_action("screen_read", "Read VS Code screenshot", "nim")
    log_action("web_search", "Search: python tutorial", "local")
    log_action("clipboard_set", "Copied: Hello world", "rules")
    r = get_recent(5)
    print(f"  recent entries:\n{r['result']}")
