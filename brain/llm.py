# ============================================================
# LavOS 2026 — brain/llm.py  (LLM Gateway)
# Cloud-first: OpenCode Zen → Groq → Cerebras → NIM → Gemini.
# Rules engine for instant replies. Never-die chain.
# ============================================================

import json
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

# --- cloud chat (OpenAI-compatible) --------------------------------
def _cloud_chat(
    url: str,
    model: str,
    api_key: str,
    messages: list[dict],
    max_tokens: int = MAX_TOKENS_CHAT,
    vision: bool = False,
    images: Optional[list[str]] = None,
) -> dict:
    """Generic OpenAI-compatible chat. Returns {"text": ..., "engine": ...}."""
    if not api_key:
        return {"text": "", "engine": "cloud", "error": "no api key"}

    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False,
    }

    # Add images for vision models
    if vision and images:
        user_msg = messages[-1] if messages else {"role": "user", "content": ""}
        content = []
        for img_path in images:
            import base64
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
        return {"text": text, "engine": model}
    except Exception as e:
        return {"text": "", "engine": model, "error": str(e)}


# --- main chat entry point ------------------------------------------
def chat(
    user_text: str,
    context: Optional[dict] = None,
    tools: Optional[list[dict]] = None,
    images: Optional[list[str]] = None,
    system_prompt: Optional[str] = None,
) -> dict:
    """
    Full chat pipeline: rules → Zen → Groq → Cerebras → NIM → Gemini.
    Returns {"text": str, "tool_call": dict|None, "engine": str}.
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

    # 3. Try providers in order
    providers = [
        ("Zen", ZEN_URL, ZEN_VISION_MODEL if images else ZEN_TEXT_MODEL, ZEN_API_KEY, bool(images)),
        ("Groq", GROQ_URL, GROQ_MODEL, GROQ_API_KEY, False),
        ("Cerebras", CEREBRAS_URL, CEREBRAS_MODEL, CEREBRAS_API_KEY, False),
        ("NIM", NIM_URL, NIM_MODEL, NIM_API_KEY, bool(images)),
        ("Gemini", None, None, GEMINI_API_KEY, False),
    ]

    for name, url, model, key, vision in providers:
        if name == "Gemini":
            continue  # handled separately below
        result = _cloud_chat(url, model, key, messages, vision=vision, images=images)
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
        return {"text": text, "engine": "gemini"}
    except Exception as e:
        return {"text": "", "engine": "gemini", "error": str(e)}


# --- CLI test -------------------------------------------------------
if __name__ == "__main__":
    print("LavOS LLM Gateway — cloud-first mode")
    print(f"  primary: Zen ({ZEN_TEXT_MODEL})")
    print(f"  speed  : Groq ({GROQ_MODEL})")
    print(f"  bulk   : Cerebras ({CEREBRAS_MODEL})")
    print()

    tests = ["hello", "what is 2+2", "open notepad"]
    for q in tests:
        print(f"> {q}")
        r = chat(q)
        print(f"  [{r['engine']}] {r['text'][:120]}")
        print()
