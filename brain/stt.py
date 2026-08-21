# ============================================================
# LavOS 2026 — brain/stt.py  (hearing)
# Speech-to-text: captures mic audio and transcribes to text.
# Online: Google Speech Recognition (free, no API key).
# Offline: Whisper (auto-downloads small model on first use).
# Push-to-talk: hold a key while speaking for clean capture.
# ============================================================

import threading
import tempfile
import os
from typing import Optional

import speech_recognition as sr

# Config
LISTEN_TIMEOUT_S = 5        # max seconds to wait for speech to start
PHRASE_TIME_LIMIT_S = 10    # max seconds of speech to capture
ENERGY_THRESHOLD = 300      # mic sensitivity (adjust for your mic)
PAUSE_THRESHOLD = 0.8       # seconds of silence to end phrase

_recognizer: Optional[sr.Recognizer] = None
_mic: Optional[sr.Microphone] = None
_lock = threading.Lock()


def _get_recognizer() -> sr.Recognizer:
    """Lazy-init recognizer with calibrated energy threshold."""
    global _recognizer, _mic
    with _lock:
        if _recognizer is None:
            _recognizer = sr.Recognizer()
            _recognizer.energy_threshold = ENERGY_THRESHOLD
            _recognizer.pause_threshold = PAUSE_THRESHOLD
            try:
                _mic = sr.Microphone()
                with _mic as source:
                    _recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except (OSError, AttributeError):
                _mic = None  # no mic available
    return _recognizer


def listen_once(timeout: float = LISTEN_TIMEOUT_S, phrase_limit: float = PHRASE_TIME_LIMIT_S) -> dict:
    """
    Listen for a single utterance from the mic.
    Returns {"ok": bool, "text": str, "error": str|None}.
    """
    recognizer = _get_recognizer()
    if _mic is None:
        return {"ok": False, "text": "", "error": "No microphone detected"}

    try:
        with _mic as source:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
    except sr.WaitTimeoutError:
        return {"ok": False, "text": "", "error": "No speech detected (timeout)"}
    except Exception as e:
        return {"ok": False, "text": "", "error": f"Mic error: {e}"}

    # Try Google first (online, free, fast)
    try:
        text = recognizer.recognize_google(audio)
        return {"ok": True, "text": text, "error": None, "engine": "google"}
    except (sr.UnknownValueError, sr.RequestError):
        pass

    # Fallback: Whisper offline (downloads small model if needed)
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio.get_wav_data())
            tmp_path = f.name
        try:
            text = recognizer.recognize_whisper(audio, model="small", language="en")
            return {"ok": True, "text": text or "", "error": None, "engine": "whisper"}
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        return {"ok": False, "text": "", "error": f"Transcription failed: {e}"}


def listen_for_wake_word(wake_word: str = "hey vision") -> bool:
    """
    Blocking: listen continuously until wake word is heard.
    Returns True when wake word detected, False on persistent error.
    """
    recognizer = _get_recognizer()
    if _mic is None:
        return False

    wake_lower = wake_word.lower()
    try:
        with _mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
    except Exception:
        pass

    while True:
        try:
            with _mic as source:
                audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT_S, phrase_time_limit=5)
            # Try Google
            try:
                text = recognizer.recognize_google(audio).lower()
            except Exception:
                text = ""
            if wake_lower in text:
                return True
        except sr.WaitTimeoutError:
            continue  # keep listening
        except Exception:
            return False  # mic died


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    print("LavOS STT test")
    print("  Say something (5s timeout)...")
    result = listen_once()
    if result["ok"]:
        print(f"  [{result.get('engine','?')}] Heard: {result['text']}")
    else:
        print(f"  Error: {result['error']}")
