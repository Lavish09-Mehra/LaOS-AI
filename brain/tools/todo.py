# ============================================================
# LavOS 2026 — brain/tools/todo.py  (Vision's task list)
# Local-first to-do store in JSON under storage/todos/.
# CRUD: list, add, complete, delete.
# ============================================================

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

TODOS_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "todos"
TODOS_FILE = TODOS_DIR / "todos.json"


def _load() -> list[dict]:
    """Load todos from JSON file."""
    TODOS_DIR.mkdir(parents=True, exist_ok=True)
    if TODOS_FILE.exists():
        try:
            return json.loads(TODOS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save(todos: list[dict]) -> None:
    """Save todos to JSON file."""
    TODOS_DIR.mkdir(parents=True, exist_ok=True)
    TODOS_FILE.write_text(json.dumps(todos, indent=2), encoding="utf-8")


def add_todo(text: str = "", **_) -> dict:
    """Add a new to-do item."""
    if not text.strip():
        return {"ok": False, "result": "Empty task", "data": {}}
    todos = _load()
    new_id = max((t.get("id", 0) for t in todos), default=0) + 1
    todo = {
        "id": new_id,
        "text": text.strip(),
        "done": False,
        "created": datetime.now().isoformat(),
    }
    todos.append(todo)
    _save(todos)
    return {
        "ok": True,
        "result": f"Added: {text.strip()}",
        "data": todo,
    }


def list_todos(**_) -> dict:
    """List all to-do items."""
    todos = _load()
    if not todos:
        return {"ok": True, "result": "No todos yet.", "data": {"todos": []}}
    lines = []
    for t in todos:
        mark = "done" if t.get("done") else "todo"
        lines.append(f"[{mark}] #{t['id']}: {t['text']}")
    return {
        "ok": True,
        "result": "\n".join(lines),
        "data": {"todos": todos},
    }


def complete_todo(id: int = 0, **_) -> dict:
    """Mark a to-do as completed."""
    todos = _load()
    for t in todos:
        if t.get("id") == id:
            t["done"] = True
            t["completed"] = datetime.now().isoformat()
            _save(todos)
            return {"ok": True, "result": f"Completed: {t['text']}", "data": t}
    return {"ok": False, "result": f"Todo #{id} not found", "data": {}}


def delete_todo(id: int = 0, **_) -> dict:
    """Delete a to-do item."""
    todos = _load()
    for i, t in enumerate(todos):
        if t.get("id") == id:
            removed = todos.pop(i)
            _save(todos)
            return {"ok": True, "result": f"Deleted: {removed['text']}", "data": removed}
    return {"ok": False, "result": f"Todo #{id} not found", "data": {}}
