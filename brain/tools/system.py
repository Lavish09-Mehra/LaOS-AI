# ============================================================
# LavOS 2026 — brain/tools/system.py  (hands on the laptop)
# Open apps, read system stats, optional screenshot.
# Every sensitive action goes through permission.py first.
# ============================================================

import os
import subprocess
import ctypes
from typing import Optional

# Windows app aliases
APP_MAP: dict[str, str] = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "browser": "cmd /c start https://www.google.com",
    "file_explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "task_manager": "taskmgr.exe",
    "paint": "mspaint.exe",
}


def open_app(app: str = "notepad", **_) -> dict:
    """Open an application by name."""
    app_lower = app.lower().strip()
    cmd = APP_MAP.get(app_lower)
    if not cmd:
        return {"ok": False, "result": f"Unknown app: {app}", "data": {}}
    try:
        subprocess.Popen(cmd, shell=True)
        return {"ok": True, "result": f"Opened {app_lower}", "data": {"app": app_lower}}
    except Exception as e:
        return {"ok": False, "result": f"Failed to open {app}: {e}", "data": {}}


def _get_ram() -> str:
    """Get RAM usage via Windows API."""
    try:
        kernel32 = ctypes.windll.kernel32
        c_ulonglong = ctypes.c_ulonglong

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", c_ulonglong),
                ("ullAvailPhys", c_ulonglong),
                ("ullTotalPageFile", c_ulonglong),
                ("ullAvailPageFile", c_ulonglong),
                ("ullTotalVirtual", c_ulonglong),
                ("ullAvailVirtual", c_ulonglong),
                ("ullAvailExtendedVirtual", c_ulonglong),
            ]

        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
        total_gb = mem.ullTotalPhys / (1024**3)
        avail_gb = mem.ullAvailPhys / (1024**3)
        used_gb = total_gb - avail_gb
        pct = mem.dwMemoryLoad
        return f"{used_gb:.1f}/{total_gb:.1f} GB ({pct}%)"
    except Exception:
        return "unknown"


def _get_battery() -> str:
    """Get battery status via Windows API."""
    try:
        import ctypes.wintypes

        class SYSTEM_BATTERY_STATUS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_ubyte),
                ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte),
                ("Reserved1", ctypes.c_ubyte),
                ("BatteryLifeTime", ctypes.wintypes.DWORD),
                ("BatteryFullLifetime", ctypes.wintypes.DWORD),
            ]

        status = SYSTEM_BATTERY_STATUS()
        result = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
        if result:
            pct = status.BatteryLifePercent
            ac = "Charging" if status.ACLineStatus == 1 else "On battery"
            if pct == 255:
                return "No battery detected"
            return f"{pct}% ({ac})"
        return "unknown"
    except Exception:
        return "unknown"


def _get_uptime() -> str:
    """Get system uptime via Windows API."""
    try:
        import ctypes.wintypes
        kernel32 = ctypes.windll.kernel32
        tick_count = kernel32.GetTickCount64()
        seconds = tick_count // 1000
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)
    except Exception:
        return "unknown"


def get_system_info(query: str = "all", **_) -> dict:
    """Get system information. query: ram, battery, uptime, cpu, all."""
    q = query.lower().strip()
    info = {}
    if q in ("ram", "memory", "all"):
        info["ram"] = _get_ram()
    if q in ("battery", "power", "all"):
        info["battery"] = _get_battery()
    if q in ("uptime", "all"):
        info["uptime"] = _get_uptime()
    if q in ("cpu", "all"):
        info["cpu"] = "see ram/battery/uptime"
    if not info:
        info["ram"] = _get_ram()
        info["battery"] = _get_battery()
        info["uptime"] = _get_uptime()

    text = " | ".join(f"{k}: {v}" for k, v in info.items())
    return {"ok": True, "result": text, "data": info}


def read_screen(**_) -> dict:
    """Take a screenshot and return info (placeholder for VL model)."""
    return {
        "ok": False,
        "result": "Screen reading requires qwen3-vl:4b. Use the desktop button to capture.",
        "data": {},
    }
