# ============================================================
# LavOS 2026 — brain/config.py  (THE settings file)
# ONE place for everything tunable: engine, paths, provider keys.
# No external deps: secrets come from a .env file (home-made
# loader), AI name + wake word come from storage/config.json so
# users can rename Vision without touching code.
#
# Hackathon engine: local "qwen3-vl:4b" for computer/chat tasks,
# NVIDIA NIM (free cloud) for web tasks — Gemini spare. Change
# MODEL_LOCAL to 8b+ for production in ONE line.
# ============================================================

import json
import os
from pathlib import Path

# --- paths ----------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent        # project root
STORAGE_DIR = BASE_DIR / "storage"
TODOS_DIR = STORAGE_DIR / "todos"
REPORTS_DIR = STORAGE_DIR / "reports"
LOGS_DIR = STORAGE_DIR / "logs"
CONFIG_FILE = STORAGE_DIR / "config.json"
ENV_FILE = BASE_DIR / ".env"

# --- app identity ---------------------------------------------------
APP_NAME = "LavOS"
APP_VERSION = "2026"
LOCAL_ENGINE = "qwen3-vl:4b"                               # ONE-LINE SWITCH for prod (8b+)

# --- local Ollama ----------------------------------------------------
OLLAMA_HOST = "http://127.0.0.1:11434"                  # localhost only, never exposed
THINK_DEFAULT = False                                    # qwen3: false for fast replies; true only for deep reasoning
MAX_TOKENS_CHAT = 150                                    # keep answers short & punchy
STREAM_DEFAULT = True                                    # stream replies to UI for perceived speed

# --- cloud providers (ONLINE ONLY — used for web tasks) ---------------
NIM_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL = ""                                          # pick on build.nvidia.com
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_MODEL = "gemini-2.0-flash"

# --- vision (screen reading) -------------------------------------------
VL_ONLINE_PRIMARY = "nim"                                # when online: "nim" or "gemini"
VL_LOCAL_MODEL = LOCAL_ENGINE                            # local fallback (qwen3-vl:4b)
VL_MAX_TOKENS = 200                                      # vision replies can be slightly longer
VL_MAX_WIDTH = 768                                        # downscale screenshots to this width

# --- permissions ------------------------------------------------------
ASK_BEFORE_SENSITIVE = True      # every read of screen/files/web asks first
ACTION_TIMEOUT_S = 60            # auto-deny if user doesn't answer

# --- tiny .env loader (secrets never commit; no pip dep needed) --------
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

NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# --- user preferences (rename-able AI, from storage/config.json) --------
def _read_user_config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

def get_ai_name() -> str:
    """The agent's name. Users rename Vision via storage/config.json."""
    return _read_user_config().get("ai_name", "Vision")

def get_wake_word() -> str:
    """Wake phrase, follows the ai_name. Default: 'hey Vision'."""
    return _read_user_config().get("wake_word", "hey Vision")


if __name__ == "__main__":
    print(f"{APP_NAME} {APP_VERSION} — settings")
    print(f"  ai_name      : {get_ai_name()}")
    print(f"  wake_word    : {get_wake_word()}")
    print(f"  local engine : {LOCAL_ENGINE}")
    print(f"  ollama       : {OLLAMA_HOST}")
    print(f"  NIM key set  : {bool(NIM_API_KEY)}")
    print(f"  gemini set   : {bool(GEMINI_API_KEY)}")
    print(f"  storage      : {STORAGE_DIR}")