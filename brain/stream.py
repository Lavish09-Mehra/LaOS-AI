# ============================================================
# LavOS 2026 — brain/stream.py
# Privacy-respecting screen capture.
# Frames in memory only, never written to disk.
# User must manually start — never auto-captures.
# ============================================================

import base64
import io
import threading
import time

_capture_thread: threading.Thread | None = None
_capture_running = False
_latest_frame: str | None = None
_lock = threading.Lock()


def _capture_loop(fps: int = 1) -> None:
    global _latest_frame, _capture_running
    interval = 1.0 / max(fps, 1)
    while _capture_running:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            w, h = img.size
            max_w = 640
            if w > max_w:
                ratio = max_w / w
                img = img.resize((max_w, int(h * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            with _lock:
                _latest_frame = b64
        except Exception:
            with _lock:
                _latest_frame = None
        time.sleep(interval)


def start_capture(fps: int = 1) -> dict:
    global _capture_thread, _capture_running
    if _capture_running:
        return {"ok": True, "result": "already streaming"}
    _capture_running = True
    _capture_thread = threading.Thread(target=_capture_loop, args=(fps,), daemon=True)
    _capture_thread.start()
    return {"ok": True, "result": f"streaming at {fps} fps"}


def stop_capture() -> dict:
    global _capture_running, _latest_frame
    _capture_running = False
    with _lock:
        _latest_frame = None
    return {"ok": True, "result": "stopped"}


def get_frame() -> str | None:
    with _lock:
        return _latest_frame


def is_streaming() -> bool:
    return _capture_running
