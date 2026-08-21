# ============================================================
# LavOS 2026 — brain/agent.py  (the controller loop)
# Heart of Vision. Loop: hear -> classify -> pick tool -> call ->
# validate -> narrate. Routing: web/big-thinking = cloud,
# computer tasks = local. v1 = chat-only.
# ============================================================

import json
import re
from typing import Optional

from brain.config import MAX_TOKENS_CHAT, get_ai_name
from brain.llm import chat, SYSTEM_PROMPT
from brain.tools import execute_tool, get_tool_schemas
from brain.tools.system import _get_ram, _get_battery, _get_uptime


def build_system_prompt() -> str:
    """Build system prompt with tool descriptions and current context."""
    ai_name = get_ai_name()
    tools_desc = "\n".join(
        f"- {s['function']['name']}: {s['function']['description']}"
        for s in get_tool_schemas()
    )
    return (
        f"You are {ai_name}, the AI assistant inside LavOS 2026. "
        f"Be concise: 1-3 sentences unless the user asks for detail. "
        f"When you need to do something, call the appropriate tool. "
        f"Never mention being an AI language model — you ARE {ai_name}.\n\n"
        f"Available tools:\n{tools_desc}\n\n"
        f"Respond naturally to greetings and small talk. "
        f"Only use tools when the user asks you to do something."
    )


def run_agent(
    user_text: str,
    context: Optional[dict] = None,
) -> dict:
    """
    Main agent loop for a single user utterance.
    Returns {"reply": str, "tool_call": dict|None, "engine": str}.
    """
    ctx = context or {}
    ctx.setdefault("history", [])

    # Inject live system info for rules engine
    ctx["ram"] = _get_ram()
    ctx["battery"] = _get_battery()
    ctx["uptime"] = _get_uptime()

    # Build system prompt with current context
    sys_prompt = build_system_prompt()

    # Call the LLM (rules → local → cloud → offline fallback)
    result = chat(
        user_text=user_text,
        context=ctx,
        tools=get_tool_schemas(),
        system_prompt=sys_prompt,
    )

    text = result.get("text", "")
    tool_call = result.get("tool_call")
    engine = result.get("engine", "unknown")

    # Rules engine returns tool JSON as text — detect and parse it
    if not tool_call and text.startswith("{"):
        try:
            parsed = json.loads(text)
            if "tool" in parsed:
                tool_call = {"name": parsed["tool"], "args": parsed.get("args", {})}
                text = ""
        except json.JSONDecodeError:
            pass

    # If the LLM called a tool, execute it
    if tool_call:
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})
        tool_result = execute_tool(tool_name, tool_args)

        if tool_result["ok"]:
            # For rules-based calls, skip narration (instant reply)
            if engine == "rules":
                text = tool_result["result"]
            else:
                # Feed result back to LLM for narration
                ollama_tool_call = [{
                    "function": {
                        "name": tool_call["name"],
                        "arguments": tool_call.get("args", {}),
                    }
                }]
                narration_msgs = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": "", "tool_calls": ollama_tool_call},
                    {"role": "tool", "content": json.dumps(tool_result)},
                ]
                narration = _ollama_chat_narrate(narration_msgs)
                text = narration or f"Done: {tool_result['result']}"
        else:
            text = f"Sorry, I couldn't do that: {tool_result['result']}"

    # Update conversation history (strip thinking tags to keep history clean)
    clean_reply = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    ctx["history"].append({"role": "user", "content": user_text})
    ctx["history"].append({"role": "assistant", "content": clean_reply})
    # Keep history short
    ctx["history"] = ctx["history"][-12:]

    return {"reply": text, "tool_call": tool_call, "engine": engine}


def _ollama_chat_narrate(messages: list[dict]) -> str:
    """Quick narration call to local Ollama after tool execution."""
    from brain.llm import _ollama_chat
    result = _ollama_chat(messages, max_tokens=100, think=False)
    return result.get("text", "")


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    print("LavOS Agent — test mode")
    print(f"  ai_name: {get_ai_name()}")
    print()

    tests = [
        "hello",
        "what's my ram",
        "add todo buy milk",
        "list my todos",
        "who invented the airplane?",
    ]
    ctx = {}
    for q in tests:
        print(f"> {q}")
        r = run_agent(q, ctx)
        print(f"  [{r['engine']}] {r['reply'][:120]}")
        if r.get("tool_call"):
            print(f"  tool: {r['tool_call']}")
        print()
