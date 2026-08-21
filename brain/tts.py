# ============================================================
# LavOS 2026 — brain/tts.py  (talking)
# Text-to-speech: Vision speaks replies out loud.
# Offline via pyttsx3 (SAPI5 on Windows) — no internet needed.
# ============================================================

import pyttsx3
import threading
from brain.config import get_ai_name

_engine = None
_lock = threading.Lock()
_muted = False


def _get_engine() -> pyttsx3.Engine:
    """Lazy-init TTS engine (thread-safe)."""
    global _engine
    with _lock:
        if _engine is None:
            _engine = pyttsx3.init()
            _engine.setProperty("rate", 175)    # speaking speed
            _engine.setProperty("volume", 0.9)  # 0.0 to 1.0
            # pick a voice (prefer female on Windows)
            voices = _engine.getProperty("voices")
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    _engine.setProperty("voice", v.id)
                    break
    return _engine


def speak(text: str, block: bool = True) -> dict:
    """
    Speak text aloud. Returns {"ok": bool, "result": str}.
    block=False runs in a background thread.
    """
    if _muted:
        return {"ok": True, "result": "Muted — skipping speech"}
    if not text or not text.strip():
        return {"ok": True, "result": "Nothing to say"}

    # Strip thinking tags and clean text for speech
    import re
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if not clean:
        return {"ok": True, "result": "Nothing to say"}

    # Cap length for snappy voice
    if len(clean) > 500:
        clean = clean[:500] + "..."

    def _do_speak():
        try:
            engine = _get_engine()
            engine.say(clean)
            engine.runAndWait()
        except Exception:
            pass  # never crash on TTS

    if block:
        _do_speak()
    else:
        threading.Thread(target=_do_speak, daemon=True).start()

    return {"ok": True, "result": f"Speaking: {clean[:80]}"}


def set_muted(muted: bool) -> None:
    """Mute/unmute voice output."""
    global _muted
    _muted = muted


def is_muted() -> bool:
    return _muted


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    ai = get_ai_name()
    print(f"{ai} TTS test — speaking in 2s...")
    import time
    time.sleep(2)
    r = speak(f"Hello! I'm {ai}, your LavOS assistant. Voice is working!", block=True)
    print(f"  result: {r['result']}")
    print("  Testing mute...")
    set_muted(True)
    r = speak("You should not hear this")
    print(f"  muted result: {r['result']}")
    set_muted(False)
    print("  Done!")
