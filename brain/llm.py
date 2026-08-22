# ============================================================
# LavOS 2026 — brain/llm.py  (LLM Gateway)
# Cloud-first: Zen → Groq → Cerebras → NIM → Gemini.
# Rules engine for instant replies. Never-die chain.
# Built-in rate limiting to protect free tiers.
# ============================================================

import json
import time
import urllib.request
import urllib.error
from typing import Optional

from brain.config import (
    ZEN_URL, ZEN_VISION_MODEL, ZEN_TEXT_MODEL, ZEN_API_KEY,
    GROQ_URL, GROQ_MODEL, GROQ_API_KEY,
    CEREBRAS_URL, CEREBRAS_MODEL, CEREBRAS_API_KEY,
    NIM_URL, NIM_MODEL, NIM_API_KEY,
    GEMINI_URL, GEMINI_MODEL, GEMINI_API_KEY,
    MAX_TOKENS_CHAT,
)

from brain.rules import rules_match as _rules_match

# --- rate limiter (protects free tiers) ----------------------------
_rate_limits: dict[str, list[float]] = {}

# Free tier limits (conservative — 5 under actual caps for safety)
FREE_LIMITS = {
    "zen": {"rpm": 10, "rpd": 200},
    "groq": {"rpm": 25, "rpd": 14395},  # Actual: 30 RPM, 14400 RPD — we cap 5 under
    "cerebras": {"rpm": 4, "rpd": 100},
    "nim": {"rpm": 10, "rpd": 200},
    "gemini": {"rpm": 10, "rpd": 200},
}


def _check_rate_limit(provider: str) -> bool:
    """Check if provider is within free tier limits. Returns True if OK."""
    limits = FREE_LIMITS.get(provider, {"rpm": 30, "rpd": 1000})
    now = time.time()

    if provider not in _rate_limits:
        _rate_limits[provider] = []

    # Clean old entries (older than 24 hours)
    _rate_limits[provider] = [t for t in _rate_limits[provider] if now - t < 86400]

    # Check daily limit
    if len(_rate_limits[provider]) >= limits["rpd"]:
        return False

    # Check per-minute limit
    recent = [t for t in _rate_limits[provider] if now - t < 60]
    if len(recent) >= limits["rpm"]:
        return False

    return True


def _record_request(provider: str) -> None:
    """Record a successful request for rate limiting."""
    if provider not in _rate_limits:
        _rate_limits[provider] = []
    _rate_limits[provider].append(time.time())


# --- cloud chat (OpenAI-compatible) --------------------------------
def _cloud_chat(
    url: str,
    model: str,
    api_key: str,
    messages: list[dict],
    provider: str = "cloud",
    max_tokens: int = MAX_TOKENS_CHAT,
    vision: bool = False,
    images: Optional[list[str]] = None,
) -> dict:
    """Generic OpenAI-compatible chat with rate limiting."""
    if not api_key:
        return {"text": "", "engine": provider, "error": "no api key"}

    if not _check_rate_limit(provider):
        return {"text": "", "engine": provider, "error": "rate limited"}

    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False,
    }

    if vision and images:
        import base64
        user_msg = messages[-1] if messages else {"role": "user", "content": ""}
        content = []
        for img_path in images:
            try:
                with open(img_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})
            except FileNotFoundError:
                continue
        content.append({"type": "text", "text": user_msg.get("content", "")})
        messages = messages[:-1] + [{"role": "user", "content": content}]
        payload["messages"] = messages

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        resp = urllib.request.urlopen(req, timeout=60)
        body = json.loads(resp.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"].strip()
        _record_request(provider)
        return {"text": text, "engine": model}
    except urllib.error.HTTPError as e:
        return {"text": "", "engine": provider, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"text": "", "engine": provider, "error": str(e)}


# --- main chat entry point ------------------------------------------
def chat(
    user_text: str,
    context: Optional[dict] = None,
    tools: Optional[list[dict]] = None,
    images: Optional[list[str]] = None,
    system_prompt: Optional[str] = None,
) -> dict:
    """
    Full chat pipeline with rate limiting.
    Rules → Zen → Groq → Cerebras → NIM → Gemini → Offline.
    """
    ctx = context or {}

    # 1. Instant rules match
    rules_reply = _rules_match(user_text, ctx)
    if rules_reply is not None:
        return {"text": rules_reply, "tool_call": None, "engine": "rules"}

    # 2. Build messages
    sys = system_prompt or "You are Vision, the AI assistant inside LavOS 2026. Be concise."
    messages = [{"role": "system", "content": sys}]
    history = ctx.get("history", [])
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": user_text})

    # 3. Try providers in order (with rate limiting)
    providers = [
        ("zen", ZEN_URL, ZEN_VISION_MODEL if images else ZEN_TEXT_MODEL, ZEN_API_KEY, bool(images)),
        ("groq", GROQ_URL, GROQ_MODEL, GROQ_API_KEY, False),
        ("cerebras", CEREBRAS_URL, CEREBRAS_MODEL, CEREBRAS_API_KEY, False),
        ("nim", NIM_URL, NIM_MODEL, NIM_API_KEY, bool(images)),
    ]

    for name, url, model, key, vision in providers:
        result = _cloud_chat(url, model, key, messages, provider=name, vision=vision, images=images)
        if result.get("text"):
            return result

    # 4. Gemini (different API format)
    result = _gemini_chat(messages)
    if result.get("text"):
        return result

    # 5. Offline fallback
    return {
        "text": "I need internet to think. Please connect and try again.",
        "tool_call": None,
        "engine": "offline",
    }


# --- Gemini (non-OpenAI format) ------------------------------------
def _gemini_chat(messages: list[dict]) -> dict:
    if not GEMINI_API_KEY:
        return {"text": "", "engine": "gemini", "error": "no key"}

    if not _check_rate_limit("gemini"):
        return {"text": "", "engine": "gemini", "error": "rate limited"}

    contents = []
    for m in messages:
        role = "user" if m["role"] in ("user", "system") else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    url = f"{GEMINI_URL}{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": MAX_TOKENS_CHAT, "temperature": 0.3},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        body = json.loads(resp.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
        _record_request("gemini")
        return {"text": text, "engine": "gemini"}
    except Exception as e:
        return {"text": "", "engine": "gemini", "error": str(e)}


# --- rate limit status (for debugging) -----------------------------
def get_rate_status() -> dict:
    """Return current rate limit status for all providers."""
    now = time.time()
    status = {}
    for provider, limits in FREE_LIMITS.items():
        times = _rate_limits.get(provider, [])
        recent_min = len([t for t in times if now - t < 60])
        recent_day = len([t for t in times if now - t < 86400])
        status[provider] = {
            "rpm": f"{recent_min}/{limits['rpm']}",
            "rpd": f"{recent_day}/{limits['rpd']}",
        }
    return status


# --- CLI test -------------------------------------------------------
if __name__ == "__main__":
    print("LavOS LLM Gateway — cloud-first mode with rate limiting")
    print()

    tests = ["hello", "what is 2+2", "open notepad"]
    for q in tests:
        print(f"> {q}")
        r = chat(q)
        print(f"  [{r['engine']}] {r['text'][:120]}")
        print()

    print("Rate limit status:")
    for provider, status in get_rate_status().items():
        print(f"  {provider}: RPM {status['rpm']}, RPD {status['rpd']}")
