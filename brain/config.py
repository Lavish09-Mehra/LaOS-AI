# ============================================================
# LavOS 2026 — brain/config.py  (THE settings file)
# ONE place for everything: cloud providers, keys, paths.
# Cloud-first architecture. All free tiers. Ultra-safe limits.
# ============================================================

import json
import os
from pathlib import Path

# --- paths ----------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
TODOS_DIR = STORAGE_DIR / "todos"
REPORTS_DIR = STORAGE_DIR / "reports"
LOGS_DIR = STORAGE_DIR / "logs"
CONFIG_FILE = STORAGE_DIR / "config.json"
ENV_FILE = BASE_DIR / ".env"

# --- app identity ---------------------------------------------------
APP_NAME = "LavOS"
APP_VERSION = "2026"
MAX_TOKENS_CHAT = 150

# --- cloud providers (FREE ONLY) ------------------------------------
# Primary: Groq (truly free, fast, no card needed)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"

# Fallback 1: NVIDIA NIM (free with key)
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NIM_MODEL = "meta/llama-3.2-11b-vision-instruct"

# Fallback 2: OpenCode Zen (free models, rate limited)
ZEN_URL = "https://opencode.ai/zen/v1/chat/completions"
ZEN_VISION_MODEL = "mimo-v2.5-free"
ZEN_TEXT_MODEL = "big-pickle"

# Disabled: Cerebras (needs billing)
CEREBRAS_URL = ""
CEREBRAS_MODEL = ""
CEREBRAS_API_KEY = ""

# Disabled: Gemini (no key)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_MODEL = "gemini-2.0-flash"

# --- vision ---------------------------------------------------------
VL_PRIMARY_MODEL = ZEN_VISION_MODEL
VL_MAX_WIDTH = 768

# --- permissions ----------------------------------------------------
ASK_BEFORE_SENSITIVE = True
ACTION_TIMEOUT_S = 60

# --- .env loader ----------------------------------------------------
def _load_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() and key.strip() not in os.environ:
            os.environ[key.strip()] = value.strip().strip('"').strip("'")

_load_env()

ZEN_API_KEY = os.environ.get("OPENCODE_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_API_KEY = ""  # disabled
NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# --- user preferences -----------------------------------------------
def _read_user_config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

def get_ai_name() -> str:
    return _read_user_config().get("ai_name", "AI")

def get_wake_word() -> str:
    return _read_user_config().get("wake_word", "hey computer")


if __name__ == "__main__":
    print(f"{APP_NAME} {APP_VERSION} — settings")
    print(f"  ai_name      : {get_ai_name()}")
    print(f"  wake_word    : {get_wake_word()}")
    print(f"  Groq key     : {bool(GROQ_API_KEY)}")
    print(f"  NIM key      : {bool(NIM_API_KEY)}")
    print(f"  Zen key      : {bool(ZEN_API_KEY)}")
    print(f"  storage      : {STORAGE_DIR}")
