# ============================================================
# LavOS 2026 — brain/main.py
# Entry point: CLI + HTTP server with full REST API.
# Endpoints: /chat, /settings, /todos, /audit, /stream, /status
# ============================================================

import json
import sys
import uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from http.server import HTTPServer


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
from urllib.parse import urlparse, parse_qs

from brain.config import (
    APP_NAME, APP_VERSION, get_ai_name, get_wake_word,
    CONFIG_FILE, STORAGE_DIR, TODOS_DIR, LOGS_DIR,
    GROQ_API_KEY, GROQ_MODEL, NIM_API_KEY, NIM_MODEL,
    ZEN_API_KEY,
)
from brain.agent import run_agent
from brain.tools.todo import add_todo, list_todos, complete_todo, delete_todo
from brain.tools.audit import log_action, get_recent, clear_log


# ===== Session store ==================================================
_sessions: dict[str, dict] = {}


# ===== CLI mode ========================================================
def run_cli():
    ai_name = get_ai_name()
    print(f"{APP_NAME} {APP_VERSION} — {ai_name} CLI")
    print(f"  wake word: {get_wake_word()}")
    print(f"  type 'quit' to exit\n")

    ctx = {}
    while True:
        try:
            user_input = input(f"{ai_name.lower()}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{ai_name}: Goodbye!")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break
        result = run_agent(user_input, ctx)
        print(f"{ai_name}: {result['reply']}")
        if result.get("tool_call"):
            print(f"  (tool: {result['tool_call']})")
        print()


# ===== Settings helpers ================================================
def _load_settings() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_settings(data: dict) -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _default_settings() -> dict:
    return {
        "ai_name": get_ai_name(),
        "wake_word": get_wake_word(),
        "voice_output": False,
        "voice_engine": "browser",
        "stream_enabled": False,
        "stream_fps": 1,
        "groq_api_key": GROQ_API_KEY,
        "groq_model": GROQ_MODEL,
        "nim_api_key": NIM_API_KEY,
        "nim_model": NIM_MODEL,
        "zen_api_key": ZEN_API_KEY,
        "ollama_enabled": False,
        "ollama_url": "http://127.0.0.1:11434",
        "ollama_chat_model": "",
        "ollama_vision_model": "",
        "permissions": "always",
    }


# ===== HTTP server =====================================================
def run_http(port: int = 8080):

    class Handler(BaseHTTPRequestHandler):

        def _json(self, code, data):
            body = json.dumps(data).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()

        def _read_body(self):
            length = int(self.headers.get("Content-Length", 0))
            return self.rfile.read(length) if length else b""

        # ---------- GET ----------
        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/health":
                self._json(200, {"status": "ok", "version": APP_VERSION, "name": get_ai_name()})

            elif path == "/status":
                ram = "unknown"
                battery = "unknown"
                uptime = "unknown"
                try:
                    from brain.tools.system import _get_ram, _get_battery, _get_uptime
                    ram = _get_ram()
                    battery = _get_battery()
                    uptime = _get_uptime()
                except Exception:
                    pass
                self._json(200, {
                    "ok": True,
                    "sessions": len(_sessions),
                    "engine": "cloud",
                    "ram": ram,
                    "battery": battery,
                    "uptime": uptime,
                })

            elif path == "/settings":
                s = _default_settings()
                s.update(_load_settings())
                self._json(200, {"ok": True, "data": s})

            elif path == "/todos":
                result = list_todos()
                self._json(200, {"ok": result["ok"], "data": result.get("data", {}).get("todos", [])})

            elif path == "/audit":
                result = get_recent(30)
                self._json(200, {"ok": result["ok"], "data": result.get("data", {})})

            elif path == "/stream/frame":
                try:
                    from brain.stream import get_frame
                    frame = get_frame()
                    if frame:
                        self._json(200, {"ok": True, "image": frame})
                    else:
                        self._json(200, {"ok": False, "error": "no frame"})
                except ImportError:
                    self._json(200, {"ok": False, "error": "stream module not found"})

            else:
                self._json(404, {"error": "not found"})

        # ---------- POST ----------
        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path
            raw = self._read_body()
            body = json.loads(raw) if raw else {}

            if path == "/chat":
                user_text = body.get("text", "")
                session_id = body.get("session_id")
                if not session_id or session_id not in _sessions:
                    session_id = str(uuid.uuid4())
                    _sessions[session_id] = {}
                ctx = _sessions[session_id]
                result = run_agent(user_text, ctx)
                result["session_id"] = session_id
                self._json(200, result)

            elif path == "/settings":
                existing = _load_settings()
                existing.update(body)
                _save_settings(existing)
                self._json(200, {"ok": True})

            elif path == "/todos":
                text = body.get("text", "")
                if text:
                    result = add_todo(text)
                    self._json(200, result)
                else:
                    self._json(400, {"ok": False, "error": "text required"})

            elif path.startswith("/todos/") and path.endswith("/complete"):
                todo_id = path.split("/")[2]
                try:
                    result = complete_todo(int(todo_id))
                    self._json(200, result)
                except (ValueError, IndexError):
                    self._json(400, {"ok": False, "error": "bad id"})

            elif path == "/audit/clear":
                result = clear_log()
                self._json(200, result)

            elif path == "/stream/start":
                try:
                    from brain.stream import start_capture
                    fps = body.get("fps", 1)
                    result = start_capture(fps=fps)
                    self._json(200, result)
                except ImportError:
                    self._json(200, {"ok": False, "error": "stream module not found"})

            elif path == "/stream/stop":
                try:
                    from brain.stream import stop_capture
                    result = stop_capture()
                    self._json(200, result)
                except ImportError:
                    self._json(200, {"ok": False, "error": "stream module not found"})

            else:
                self._json(404, {"error": "not found"})

        # ---------- DELETE ----------
        def do_DELETE(self):
            parsed = urlparse(self.path)
            path = parsed.path

            if path.startswith("/todos/"):
                todo_id = path.split("/")[2]
                try:
                    result = delete_todo(int(todo_id))
                    self._json(200, result)
                except (ValueError, IndexError):
                    self._json(400, {"ok": False, "error": "bad id"})
            else:
                self._json(404, {"error": "not found"})

        # ---------- OPTIONS ----------
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"{APP_NAME} {APP_VERSION} — http://127.0.0.1:{port}")
    server.serve_forever()


# ===== Entry point =====================================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        run_http(port)
    else:
        run_cli()
