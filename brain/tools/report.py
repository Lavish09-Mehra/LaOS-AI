# ============================================================
# LavOS 2026 — brain/tools/report.py  (todo report generator)
# Generates a markdown report from the current todo list.
# Saved to storage/reports/ for local-first access.
# ============================================================

import json
from datetime import datetime
from pathlib import Path

TODOS_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "todos"
TODOS_FILE = TODOS_DIR / "todos.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "reports"


def report_todos(**_) -> dict:
    """Generate a markdown report from the current todo list."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load todos
    todos = []
    if TODOS_FILE.exists():
        try:
            todos = json.loads(TODOS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    done = [t for t in todos if t.get("done")]
    pending = [t for t in todos if not t.get("done")]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build markdown
    lines = [
        f"# LavOS Todo Report",
        f"Generated: {ts}",
        "",
        f"**Total:** {len(todos)} | **Done:** {len(done)} | **Pending:** {len(pending)}",
        "",
        "---",
        "",
    ]

    if pending:
        lines.append("## Pending")
        lines.append("")
        for t in pending:
            lines.append(f"- [ ] #{t['id']}: {t['text']}")
        lines.append("")

    if done:
        lines.append("## Completed")
        lines.append("")
        for t in done:
            completed = t.get("completed", "unknown")[:10]
            lines.append(f"- [x] #{t['id']}: {t['text']} ({completed})")
        lines.append("")

    if not todos:
        lines.append("_No todos yet._")
        lines.append("")

    # Save report
    ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{ts_file}.md"
    path = REPORTS_DIR / filename
    path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "ok": True,
        "result": f"Report saved: {path.name} ({len(pending)} pending, {len(done)} done)",
        "data": {"path": str(path), "pending": len(pending), "done": len(done)},
    }


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    print("Report test")
    r = report_todos()
    print(f"  {r['result']}")
    if r["ok"]:
        content = Path(r["data"]["path"]).read_text(encoding="utf-8")
        print(f"\n{content}")
