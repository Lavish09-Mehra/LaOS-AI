# ============================================================
# LavOS 2026 — brain/rules.py  (never-die fallback)
# Hardcoded keyword→intent matching for demo commands.
# Works even if every LLM/network path fails.
# Returns tool JSON or template string. agent.py is blind
# to which brain answered. This file saves the demo.
# ============================================================

import re
from typing import Optional

# Each rule: (compiled_regex, reply_template)
# Templates can use {ram}, {battery}, {time}, {uptime} from context
# or {1}, {2}... for regex capture groups.
_RULES: list[tuple[re.Pattern, str]] = [
    # --- System info ---
    (re.compile(r"\b(what('?s| is) )?(my |the )?(ram|memory|mem)\b", re.I),
     "RAM: {ram}"),
    (re.compile(r"\b(what('?s| is) )?(my |the )?(battery|power|charge)\b", re.I),
     "Battery: {battery}"),
    (re.compile(r"\b(what('?s| is) )?(my |the )?time\b", re.I),
     "It's {time}."),
    (re.compile(r"\b(what('?s| is) )?(the )?(uptime|up time|how long)\b", re.I),
     "Uptime: {uptime}"),

    # --- Open apps ---
    (re.compile(r"\b(open|launch|start|run)\s+(notepad|editor|text\s*edit)", re.I),
     '{"tool":"open_app","args":{"app":"notepad"}}'),
    (re.compile(r"\b(open|launch|start|run)\s+(calc|calculator)", re.I),
     '{"tool":"open_app","args":{"app":"calculator"}}'),
    (re.compile(r"\b(open|launch|start|run)\s+(chrome|browser|firefox|edge)", re.I),
     '{"tool":"open_app","args":{"app":"browser"}}'),
    (re.compile(r"\b(open|launch|start|run)\s+(file|explorer|folder)", re.I),
     '{"tool":"open_app","args":{"app":"file_explorer"}}'),
    (re.compile(r"\b(open|launch|start|run)\s+(paint|drawing)", re.I),
     '{"tool":"open_app","args":{"app":"paint"}}'),

    # --- Todo CRUD ---
    (re.compile(r"\b(add|create|make)\s+(a )?(todo|task|reminder|note)[\s:]+(.+)", re.I),
     '{"tool":"add_todo","args":{"text":"{4}"}}'),
    (re.compile(r"\b(list|show|see|get|read)\s+(my |the )?(todos?|tasks?|reminders?)", re.I),
     '{"tool":"list_todos","args":{}}'),
    (re.compile(r"\b(complete|done|finish|mark)\s+(todo |task )?#?(\d+)", re.I),
     '{"tool":"complete_todo","args":{"id":3}}'),
    (re.compile(r"\b(delete|remove|drop)\s+(todo |task )?#?(\d+)", re.I),
     '{"tool":"delete_todo","args":{"id":3}}'),

    # --- Web search ---
    (re.compile(r"\b(search|look up|google|find)\s+(.+)", re.I),
     '{"tool":"web_search","args":{"query":"{2}"}}'),

    # --- Screen reading ---
    (re.compile(r"\b(what('?s| is) )?(on |my )?(screen|display|monitor)", re.I),
     '{"tool":"read_screen","args":{}}'),
    (re.compile(r"\b(read|describe|what do you see)\s+(on )?(the )?(screen|display)", re.I),
     '{"tool":"read_screen","args":{}}'),

    # --- Greetings ---
    (re.compile(r"\b(hi|hello|hey|howdy|good\s*(morning|afternoon|evening))\b", re.I),
     "Hello! I'm Vision, your LavOS assistant. How can I help?"),

    # --- Status ---
    (re.compile(r"\b(how are you|how('?s| is) it going|what('?s| is) up)\b", re.I),
     "I'm running great! All systems online. How can I help?"),
    (re.compile(r"\b(who are you|what are you|your name)\b", re.I),
     "I'm Vision, your AI assistant built into LavOS 2026."),
    (re.compile(r"\b(thank|thanks)\b", re.I),
     "You're welcome! Anything else I can help with?"),
]


def rules_match(query: str, ctx: Optional[dict] = None) -> Optional[str]:
    """
    Try to match the query against instant rules.
    Returns reply string if matched, None if no match.
    ctx provides live system info (ram, battery, time, uptime).
    Only matches SHORT simple commands (<=6 words for action queries).
    Complex multi-step tasks go to the LLM agent.
    """
    ctx = ctx or {}
    # Skip rules for long/complex queries — let LLM agent handle them
    words = query.strip().split()
    if len(words) > 8:
        return None
    for pattern, reply_tpl in _RULES:
        m = pattern.search(query)
        if m:
            result = reply_tpl
            # Replace system info placeholders
            result = result.replace("{ram}", ctx.get("ram", "unknown"))
            result = result.replace("{battery}", ctx.get("battery", "unknown"))
            result = result.replace("{time}", ctx.get("time", "unknown"))
            result = result.replace("{uptime}", ctx.get("uptime", "unknown"))
            # Replace regex capture groups {1}, {2}, ...
            for i in range(1, 10):
                try:
                    val = m.group(i)
                    if val:
                        result = result.replace("{" + str(i) + "}", val)
                except IndexError:
                    break
            return result
    return None


# --- CLI test -----------------------------------------------------------
if __name__ == "__main__":
    test_queries = [
        "what's my ram",
        "hello",
        "open notepad",
        "add todo buy milk",
        "list my todos",
        "complete task 1",
        "search python tutorial",
        "what time is it",
        "what's on my screen",
        "who are you",
        "thanks",
    ]
    ctx = {"ram": "6.2/15.3 GB (41%)", "battery": "85% (On battery)", "time": "14:30", "uptime": "2h 15m"}
    for q in test_queries:
        r = rules_match(q, ctx)
        status = "MATCH" if r else "MISS"
        print(f"  [{status}] {q:30s} → {r}")
