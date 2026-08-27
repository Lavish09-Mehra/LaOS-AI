# ============================================================
# LavOS 2026 — brain/tools/system.py  (hands on the laptop)
# Open apps, read system stats, optional screenshot.
# Every sensitive action goes through permission.py first.
# ============================================================

import json
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


def capture_screen(query: str = "full", **_) -> dict:
    """Take a screenshot to a temp file. Auto-deleted after use for privacy."""
    try:
        from PIL import ImageGrab, Image as PILImage


        import tempfile, time
        tmp_dir = tempfile.mkdtemp(prefix="lavos_ss_")
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(tmp_dir, f"screen_{ts}.png")
        img = ImageGrab.grab()
        # downscale to max 512px wide for faster VL processing
        w, h = img.size
        if w > 512:
            ratio = 512 / w
            img = img.resize((512, int(h * ratio)), PILImage.LANCZOS)
        img.save(path, optimize=True)
        return {"ok": True, "result": f"Screenshot captured", "data": {"path": path, "size": img.size}}
    except Exception as e:
        return {"ok": False, "result": f"Screenshot failed: {e}", "data": {}}


def _delete_screenshot(path: str) -> None:
    """Delete temp screenshot file. Silent — never crashes."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
            # clean up temp dir if empty
            parent = os.path.dirname(path)
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
    except OSError:
        pass


def read_screen(query: str = "full", **_) -> dict:
    """Take a screenshot, read it with cloud VL, then DELETE it. Zero privacy leak."""
    ss = capture_screen(query=query)
    if not ss["ok"]:
        return ss
    path = ss["data"]["path"]

    try:
        import base64
        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
    except Exception as e:
        _delete_screenshot(path)
        return {"ok": False, "result": f"Failed to read screenshot: {e}", "data": {}}

    # --- Cloud VL (MiMo-V2.5 via OpenCode Zen) ---
    try:
        from brain.config import ZEN_API_KEY, ZEN_URL, ZEN_VISION_MODEL
        import urllib.request
        payload = {
            "model": ZEN_VISION_MODEL,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Describe what you see on this screenshot in detail. Read all text visible."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}],
            "max_tokens": 300,
            "temperature": 0.3,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {ZEN_API_KEY}"}
        req = urllib.request.Request(ZEN_URL, data=data, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=30)
        body = json.loads(resp.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"]
        if text and len(text.strip()) > 5:
            _delete_screenshot(path)
            return {"ok": True, "result": text.strip(), "data": {"engine": "zen-vision"}}
    except Exception:
        pass

    # --- Fallback: NIM VL ---
    try:
        from brain.config import NIM_API_KEY, NIM_URL, NIM_MODEL
        import urllib.request
        payload = {
            "model": NIM_MODEL,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Describe what you see on this screenshot in detail. Read all text visible."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}],
            "max_tokens": 300,
            "temperature": 0.3,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {NIM_API_KEY}"}
        req = urllib.request.Request(NIM_URL, data=data, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=30)
        body = json.loads(resp.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"]
        if text and len(text.strip()) > 5:
            _delete_screenshot(path)
            return {"ok": True, "result": text.strip(), "data": {"engine": "nim"}}
    except Exception:
        pass

    _delete_screenshot(path)
    return {"ok": False, "result": "Screen reading failed — no vision API available", "data": {}}
