# LavOS 2026 — Vision Edition

> A laptop you can talk to that does work for you.
> Real from-scratch kernel demo + Vision desktop agent (voice, to-do, VS Code help).

## Read first
- **`docs/MASTER_PLAN.md`** — THE one file. Everything we decided: plan, tech, routing, phases, roles, risks.
- `docs/demo-script.md` — the 5-minute live demo.

## The two products
- **`kernel/`** — LavOS: our own hand-written 32-bit OS, boots in QEMU via GRUB (multiboot), splash + interactive shell. **Done & booting.**
- **`brain/`** — Vision: the desktop AI agent (voice, to-do, VS Code help, local-first).

## Quick map
- `kernel/` — LavOS bootable OS (C/asm, boots in QEMU via GRUB)
- `brain/` — Vision agent (Python): voice, LLM router, tools, agent loop
- `home/` — Node web UI (Vision Home + floating overlay)
- `vscode-extension/` — sends code context to Vision, shows solutions
- `storage/` — local-first data (todos, reports, logs, config)

## Naming
- OS: **LavOS 2026**
- AI default name: **Vision** (wake word "hey Vision") — fully renameable by
  the user via `storage/config.json` (`ai_name` + `wake_word`). Renamed once,
  the agent, wake word and UI all follow.

## Model (hackathon)
Local: `qwen3:4b` via Ollama (offline, private). Cloud (online only): NVIDIA NIM → Gemini spare.
Also see the one-line engine switch in `brain/config.py`.

## Rules we follow
- Every file ≤ 600 lines (split if approaching).
- 1 step = 1 file, testable after every step.
- Feature freeze Day 13. Demo cannot die.
- Run the kernel demo: in WSL `cd /mnt/c/Users/Hp/Desktop/AI\ OS\ 2026/kernel && make run`