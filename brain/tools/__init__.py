# ============================================================
# LavOS 2026 — brain/tools/__init__.py
# Tool registry: maps LLM tool-call names to Python handlers.
# Each tool returns {"ok": bool, "result": str, "data": dict}.
# ============================================================

from brain.tools.system import open_app, get_system_info, read_screen, capture_screen
from brain.tools.todo import add_todo, list_todos, complete_todo, delete_todo
from brain.tools.search import web_search
from brain.tools.permission import ask_permission
from brain.tools.clipboard import set_clipboard, get_clipboard
from brain.tools.audit import log_action, get_recent, clear_log
from brain.tools.report import report_todos

# Ollama tool schema — tells the LLM what tools exist
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the user's computer",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {
                        "type": "string",
                        "description": "Application name (notepad, calculator, browser, file_explorer)",
                    }
                },
                "required": ["app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get system information (RAM, battery, uptime, CPU usage)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What info to get: ram, battery, uptime, cpu, all",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "Add a new to-do item",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The task description"}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_todos",
            "description": "List all to-do items",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "Mark a to-do item as completed",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "The to-do item ID"}
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_todo",
            "description": "Delete a to-do item",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "The to-do item ID"}
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information (requires internet)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_screen",
            "description": "Take a screenshot and describe what's on screen (on-demand only)",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_clipboard",
            "description": "Copy text to system clipboard",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to copy to clipboard"}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "Read current clipboard content",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_todos",
            "description": "Generate a markdown report from the current todo list",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_actions",
            "description": "Show what Vision has recently done (audit trail)",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "description": "Number of recent actions to show (default 10)"}
                },
            },
        },
    },
]

# Tool registry: name -> handler function
TOOL_REGISTRY: dict = {
    "open_app": open_app,
    "get_system_info": get_system_info,
    "add_todo": add_todo,
    "list_todos": list_todos,
    "complete_todo": complete_todo,
    "delete_todo": delete_todo,
    "web_search": web_search,
    "read_screen": read_screen,
    "set_clipboard": set_clipboard,
    "get_clipboard": get_clipboard,
    "report_todos": report_todos,
    "get_recent_actions": get_recent,
}


def execute_tool(name: str, args: dict) -> dict:
    """Execute a tool by name with args. Returns standard result dict."""
    handler = TOOL_REGISTRY.get(name)
    if not handler:
        return {"ok": False, "result": f"Unknown tool: {name}", "data": {}}
    try:
        return handler(**args)
    except TypeError as e:
        return {"ok": False, "result": f"Bad args for {name}: {e}", "data": {}}
    except Exception as e:
        return {"ok": False, "result": f"Tool error: {e}", "data": {}}


def get_tool_schemas() -> list[dict]:
    """Return tool schemas for the LLM."""
    return TOOL_SCHEMAS
