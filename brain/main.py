# ============================================================
# LavOS 2026 — brain/main.py  (process entry point)
# Where Vision starts: load config, start the agent loop,
# expose a local HTTP/socket feed to the Node UI.
# ============================================================

import json
import sys
from pathlib import Path

from brain.config import APP_NAME, APP_VERSION, get_ai_name, get_wake_word
from brain.agent import run_agent


def run_cli():
    """Run Vision in CLI mode for testing."""
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
            print(f"{ai_name}: Goodbye!")
            break

        result = run_agent(user_input, ctx)
        print(f"{ai_name}: {result['reply']}")
        if result.get("tool_call"):
            print(f"  (tool: {result['tool_call']})")
        print()


def run_http(port: int = 8080):
    """Run Vision as an HTTP server for the Node UI."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class VisionHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path == "/chat":
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                data = json.loads(body)
                user_text = data.get("text", "")
                context = data.get("context", {})

                result = run_agent(user_text, context)
                response = json.dumps(result).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(response)
            else:
                self.send_response(404)
                self.end_headers()

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress HTTP logs

    server = HTTPServer(("127.0.0.1", port), VisionHandler)
    print(f"{APP_NAME} {APP_VERSION} — HTTP server on http://127.0.0.1:{port}")
    print("  POST /chat with {text, context} to chat")
    server.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        run_http(port)
    else:
        run_cli()
