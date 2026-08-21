# ============================================================
# LavOS 2026 — brain/wake.py  (helps Vision "wake up")
# On-device wake-word detection ("Hey Vision") so talking to the
# laptop feels natural. Runs silently in the background.
#
# Two modes:
#   1. Push-to-talk: hold F5 key while speaking (always works)
#   2. Wake word: say "Hey Vision" to activate (needs mic)
# ============================================================

import threading
import time
from typing import Callable, Optional

from brain.config import get_wake_word
from brain.stt import listen_once, listen_for_wake_word

# Config
PTT_KEY = "f5"                     # push-to-talk hotkey
STATUS_CALLBACK: Optional[Callable] = None  # fn(status: str) for UI
_listening = False
_stop_event = threading.Event()


def set_status_callback(callback: Callable) -> None:
    """Register a callback for status updates: idle, listening, thinking."""
    global STATUS_CALLBACK
    STATUS_CALLBACK = callback


def _emit(status: str) -> None:
    """Send status to UI callback."""
    if STATUS_CALLBACK:
        try:
            STATUS_CALLBACK(status)
        except Exception:
            pass


def wait_for_wakeword() -> dict:
    """
    Blocking: wait until wake word is heard or push-to-talk pressed.
    Returns {"ok": True, "text": "<command after wake>"} or
            {"ok": False, "text": "", "error": str}.
    """
    _emit("listening")
    wake = get_wake_word()

    # Try wake word detection via mic
    try:
        # Listen for wake word (blocking)
        detected = listen_for_wake_word(wake)
        if detected:
            _emit("thinking")
            # Now listen for the actual command
            result = listen_once(timeout=5, phrase_limit=10)
            if result["ok"]:
                return {"ok": True, "text": result["text"], "mode": "wake_word"}
            return {"ok": False, "text": "", "error": "Wake word heard but no command"}
    except Exception:
        pass

    # Fallback: push-to-talk (always works)
    return wait_for_ptt()


def wait_for_ptt() -> dict:
    """
    Blocking: wait for push-to-talk (F5 key held).
    Returns {"ok": True, "text": "<spoken command>"}.
    Falls back to keyboard input if pynput not available.
    """
    _emit("listening")
    try:
        import pynput.keyboard as kb
        pressed = threading.Event()

        def on_press(key):
            if hasattr(key, 'name') and key.name == PTT_KEY:
                pressed.set()

        listener = kb.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

        # Wait for key press
        pressed.wait(timeout=30)
        if not pressed.is_set():
            _emit("idle")
            return {"ok": False, "text": "", "error": "PTT timeout"}

        _emit("thinking")
        result = listen_once(timeout=5, phrase_limit=10)
        listener.stop()
        if result["ok"]:
            return {"ok": True, "text": result["text"], "mode": "ptt"}
        return {"ok": False, "text": "", "error": result.get("error", "No speech")}

    except ImportError:
        # No pynput — use simple input fallback
        _emit("idle")
        return {"ok": False, "text": "", "error": "pynput not installed — use CLI mode"}


def start_listening_loop(callback: Callable[[str], None]) -> None:
    """
    Background loop: continuously listen for wake word → command → callback.
    callback receives the recognized command text.
    Runs in a daemon thread. Call stop_listening() to halt.
    """
    global _listening
    _listening = True
    _stop_event.clear()

    def _loop():
        while not _stop_event.is_set():
            result = wait_for_wakeword()
            if result["ok"] and result["text"]:
                try:
                    callback(result["text"])
                except Exception:
                    pass
            _emit("idle")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def stop_listening() -> None:
    """Stop the background listening loop."""
    global _listening
    _listening = False
    _stop_event.set()


def is_listening() -> bool:
    return _listening


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    print("LavOS Wake Word test")
    print(f"  Wake word: {get_wake_word()}")
    print(f"  PTT key: {PTT_KEY}")
    print("  Say the wake word or press F5...")
    print()

    def on_command(text):
        print(f"  Command received: {text}")

    set_status_callback(lambda s: print(f"  Status: {s}"))
    result = wait_for_wakeword()
    if result["ok"]:
        print(f"  [{result.get('mode','?')}] Command: {result['text']}")
    else:
        print(f"  Error: {result['error']}")
