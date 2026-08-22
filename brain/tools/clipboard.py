# ============================================================
# LavOS 2026 — brain/tools/clipboard.py  (copy/paste)
# Clipboard access via pyperclip. Works on Windows/macOS/Linux.
# ============================================================

import pyperclip


def set_clipboard(text: str = "", **_) -> dict:
    """Copy text to system clipboard."""
    if not text or not text.strip():
        return {"ok": False, "result": "Empty text", "data": {}}
    try:
        pyperclip.copy(text)
        return {
            "ok": True,
            "result": f"Copied to clipboard: {text[:80]}{'...' if len(text) > 80 else ''}",
            "data": {"text": text},
        }
    except Exception as e:
        return {"ok": False, "result": f"Clipboard error: {e}", "data": {}}


def get_clipboard(**_) -> dict:
    """Read current clipboard content."""
    try:
        text = pyperclip.paste()
        if not text or not text.strip():
            return {"ok": True, "result": "Clipboard is empty", "data": {"text": ""}}
        return {
            "ok": True,
            "result": f"Clipboard: {text[:200]}{'...' if len(text) > 200 else ''}",
            "data": {"text": text},
        }
    except Exception as e:
        return {"ok": False, "result": f"Clipboard read error: {e}", "data": {}}


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    print("Clipboard test")
    r = set_clipboard("Hello from LavOS Vision!")
    print(f"  set: {r['result']}")
    r = get_clipboard()
    print(f"  get: {r['result']}")
    print(f"  match: {r['data'].get('text') == 'Hello from LavOS Vision!'}")
