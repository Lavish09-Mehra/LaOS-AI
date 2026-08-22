# ============================================================
# LavOS 2026 — brain/agent.py  (the controller loop)
# Heart of Vision. Loop: hear -> classify -> pick tool -> call ->
# validate -> narrate. Cloud-first architecture.
# ============================================================

import json
import re
from typing import Optional

from brain.config import MAX_TOKENS_CHAT, get_ai_name
from brain.llm import chat
from brain.tools import execute_tool, get_tool_schemas
from brain.tools.system import _get_ram, _get_battery, _get_uptime


def build_system_prompt() -> str:
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


def run_agent(user_text: str, context: Optional[dict] = None) -> dict:
    ctx = context or {}
    ctx.setdefault("history", [])
    ctx["ram"] = _get_ram()
    ctx["battery"] = _get_battery()
    ctx["uptime"] = _get_uptime()

    sys_prompt = build_system_prompt()

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

    # Detect tool patterns in text (for models without native tool calling)
    if not tool_call:
        tool_call = _detect_tool_in_text(text)

    # If the LLM called a tool, execute it
    if tool_call:
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})
        tool_result = execute_tool(tool_name, tool_args)

        if tool_result["ok"]:
            if engine == "rules":
                text = tool_result["result"]
            else:
                # Feed result back to LLM for narration
                narration_msgs = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": f"[Tool {tool_name} executed]"},
                    {"role": "user", "content": f"Tool result: {json.dumps(tool_result['result'])[:500]}. Summarize briefly."},
                ]
                narration = chat(
                    user_text=f"Tool result: {json.dumps(tool_result['result'])[:500]}. Summarize briefly.",
                    context={"history": narration_msgs[:-1]},
                    system_prompt="Summarize the tool result in 1-2 sentences.",
                )
                text = narration.get("text") or f"Done: {tool_result['result']}"
        else:
            text = f"Sorry, I couldn't do that: {tool_result['result']}"

    # Update conversation history
    clean_reply = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    ctx["history"].append({"role": "user", "content": user_text})
    ctx["history"].append({"role": "assistant", "content": clean_reply})
    ctx["history"] = ctx["history"][-12:]

    return {"reply": text, "tool_call": tool_call, "engine": engine}


def _detect_tool_in_text(text: str) -> Optional[dict]:
    text_lower = text.lower()

    for pattern in [r'"tool"\s*:\s*"(\w+)"', r'tool:\s*(\w+)', r'calling:\s*(\w+)']:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            tool_name = m.group(1)
            args = {}
            args_match = re.search(r'"args"\s*:\s*(\{[^}]+\})', text)
            if args_match:
                try:
                    args = json.loads(args_match.group(1))
                except json.JSONDecodeError:
                    pass
            return {"name": tool_name, "args": args}

    keyword_map = {
        r'screenshot|capture screen|take screenshot': ('read_screen', {}),
        r'read screen|what.?s on screen|read the screen': ('read_screen', {}),
        r'open notepad': ('open_app', {'app_name': 'notepad'}),
        r'open (\w+)': ('open_app', {'app_name': None}),
        r'search for (.+)': ('web_search', {'query': None}),
        r'web search (.+)': ('web_search', {'query': None}),
        r'add todo (.+)': ('add_todo', {'task': None}),
        r'list (my )?todos': ('list_todos', {}),
        r'what.?s my (ram|memory|battery|system)': ('get_system_info', {}),
        r'set clipboard (.+)': ('set_clipboard', {'text': None}),
        r'get clipboard': ('get_clipboard', {}),
        r'report': ('report_todos', {}),
        r'recent (actions|history)': ('get_recent_actions', {}),
    }

    for pattern, (tool_name, default_args) in keyword_map.items():
        m = re.search(pattern, text_lower)
        if m:
            args = dict(default_args)
            if tool_name == 'open_app' and m.group(1):
                args['app_name'] = m.group(1)
            elif tool_name in ('web_search', 'add_todo', 'set_clipboard') and m.group(1):
                key = 'query' if 'search' in tool_name else ('task' if 'todo' in tool_name else 'text')
                args[key] = m.group(1).strip()
            return {"name": tool_name, "args": args}

    return None


if __name__ == "__main__":
    print("LavOS Agent — cloud-first mode")
    tests = ["hello", "what's my ram", "add todo buy milk", "list my todos"]
    ctx = {}
    for q in tests:
        print(f"> {q}")
        r = run_agent(q, ctx)
        print(f"  [{r['engine']}] {r['reply'][:120]}")
        if r.get("tool_call"):
            print(f"  tool: {r['tool_call']}")
        print()
