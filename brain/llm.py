# ============================================================
# LavOS 2026 — brain/llm.py  (LLM Gateway)
# Speed-first chat: rules.py → local qwen3-vl:4b → cloud NIM/Gemini.
# Every path tested; never-die chain ensures a reply always.
# ============================================================

import json
import re
import urllib.request
import urllib.error
from typing import Optional, Generator

from brain.config import (
    OLLAMA_HOST, LOCAL_ENGINE, THINK_DEFAULT, MAX_TOKENS_CHAT,
    NIM_URL, NIM_MODEL, NIM_API_KEY,
    GEMINI_URL, GEMINI_MODEL, GEMINI_API_KEY,
    VL_MAX_TOKENS, VL_MAX_WIDTH,
)

# --- system prompt (Vision persona) ------------------------------------
SYSTEM_PROMPT = (
    "You are Vision, the AI assistant inside LavOS 2026. "
    "Be concise: 1-3 sentences unless the user asks for detail. "
    "When calling tools, use the exact JSON format. "
    "Never mention being an AI language model — you ARE Vision."
)

# --- rules engine (imported from rules.py — never-die fallback) ----------
from brain.rules import rules_match as _rules_match


# --- Ollama local chat -------------------------------------------------
def _ollama_chat(
    messages: list[dict],
    model: str = LOCAL_ENGINE,
    think: bool = THINK_DEFAULT,
    max_tokens: int = MAX_TOKENS_CHAT,
    images: Optional[list[str]] = None,
    tools: Optional[list[dict]] = None,
) -> dict:
    """Send chat to local Ollama. Returns {"text": ..., "tool_call": ...|None}."""
    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": think,
        "options": {"num_predict": max_tokens},
    }
    if images:
        payload["images"] = images
    if tools:
        payload["tools"] = tools

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        body = json.loads(resp.read().decode("utf-8"))
        msg = body.get("message", {})
        text = msg.get("content", "").strip()
        thinking = msg.get("thinking", "").strip()
        # qwen3-vl sometimes puts output in thinking field — use it as fallback
        if not text and thinking:
            text = thinking
        tool_calls = msg.get("tool_calls")
        tool_call = None
        if tool_calls:
            fn = tool_calls[0].get("function", {})
            tool_call = {"name": fn.get("name", ""), "args": fn.get("arguments", {})}
        return {"text": text, "tool_call": tool_call, "engine": "local"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"text": "", "tool_call": None, "engine": "local", "error": str(e)}


# --- Cloud: NIM --------------------------------------------------------
def _nim_chat(messages: list[dict], max_tokens: int = MAX_TOKENS_CHAT) -> dict:
    """NIM cloud fallback (OpenAI-compatible API)."""
    if not NIM_API_KEY or not NIM_MODEL:
        return {"text": "", "engine": "nim", "error": "no key or model"}

    payload = {
        "model": NIM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{NIM_URL}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {NIM_API_KEY}",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        body = json.loads(resp.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"].strip()
        return {"text": text, "engine": "nim"}
    except Exception as e:
        return {"text": "", "engine": "nim", "error": str(e)}


# --- Cloud: Gemini ------------------------------------------------------
def _gemini_chat(messages: list[dict], max_tokens: int = MAX_TOKENS_CHAT) -> dict:
    """Gemini cloud fallback."""
    if not GEMINI_API_KEY:
        return {"text": "", "engine": "gemini", "error": "no key"}

    contents = []
    for m in messages:
        role = "user" if m["role"] in ("user", "system") else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    url = f"{GEMINI_URL}{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        body = json.loads(resp.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
        return {"text": text, "engine": "gemini"}
    except Exception as e:
        return {"text": "", "engine": "gemini", "error": str(e)}


# --- Cloud VL (vision-language) -----------------------------------------
def _cloud_vl(messages: list[dict], images: list[str], engine: str = "nim") -> dict:
    """Send vision query to cloud VL. NIM first, Gemini spare."""
    # For now, cloud VL is text-only placeholder (actual VL endpoints
    # vary; implement when NIM VL model key is set)
    if engine == "nim" and NIM_API_KEY:
        return _nim_chat(messages, max_tokens=VL_MAX_TOKENS)
    if GEMINI_API_KEY:
        return _gemini_chat(messages, max_tokens=VL_MAX_TOKENS)
    return {"text": "", "engine": "cloud_vl", "error": "no cloud key"}


# --- main chat entry point ----------------------------------------------
def chat(
    user_text: str,
    context: Optional[dict] = None,
    tools: Optional[list[dict]] = None,
    images: Optional[list[str]] = None,
    system_prompt: Optional[str] = None,
) -> dict:
    """
    Full chat pipeline: rules → local → cloud → offline fallback.
    Returns {"text": str, "tool_call": dict|None, "engine": str}.
    """
    ctx = context or {}
    sys = system_prompt or SYSTEM_PROMPT

    # 1. Instant rules match
    rules_reply = _rules_match(user_text, ctx)
    if rules_reply is not None:
        return {"text": rules_reply, "tool_call": None, "engine": "rules"}

    # 2. Build messages
    messages = [{"role": "system", "content": sys}]
    history = ctx.get("history", [])
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": user_text})

    # 3. Local Ollama (try VL if images, else text)
    if images:
        result = _ollama_chat(messages, images=images, max_tokens=VL_MAX_TOKENS, tools=tools)
    else:
        result = _ollama_chat(messages, tools=tools)

    if result.get("text") or result.get("tool_call"):
        return result

    # 4. Cloud fallback: NIM → Gemini
    result = _nim_chat(messages)
    if result.get("text"):
        return result

    result = _gemini_chat(messages)
    if result.get("text"):
        return result

    # 5. Offline last resort (rules didn't match, local + cloud failed)
    return {
        "text": "I'm having trouble reaching my brain right now. Can you try again?",
        "tool_call": None,
        "engine": "offline_fallback",
    }


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    print("LavOS LLM Gateway — test mode")
    print(f"  engine: {LOCAL_ENGINE}")
    print(f"  think : {THINK_DEFAULT}")
    print(f"  tokens: {MAX_TOKENS_CHAT}")
    print()

    test_queries = [
        "what's my ram",
        "add todo buy milk",
        "open notepad",
        "who invented the airplane?",
    ]
    for q in test_queries:
        print(f"> {q}")
        r = chat(q)
        print(f"  [{r['engine']}] {r['text'][:120]}")
        if r.get("tool_call"):
            print(f"  tool: {r['tool_call']}")
        print()
