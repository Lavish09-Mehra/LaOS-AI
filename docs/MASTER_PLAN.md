# LavOS 2026 — MASTER PLAN

> **This is THE one file. Everything we decided lives here.** Read this first before touching any other file. Update it whenever we change direction on Day 13+ freezes.

**Naming (locked in):** OS = **LavOS 2026** · AI default name = **Vision** (wake word "hey Vision") · AI name is **user-configurable**: read `ai_name` + `wake_word` from `storage/config.json` at startup so users can rename the agent (agent, wake word, and UI all follow the new name).

---

## 1. Vision & Story

**One product, one promise:** *A laptop you can talk to that does work for you — powered by your own private AI, with an operating system built from scratch.*

**The pitch (for judges):** *"I built an OS from scratch — and then I taught it to listen and do work for you."*

**Two products in one repo:**
| Product | What it is | Why it wins |
|---------|-----------|-------------|
| **Kernel demo (BONUS)** | Real bootable C kernel (QEMU) — animated splash, shell stub, alive-heartbeat | "I wrote an OS from zero" — technical credibility |
| **Vision agent (THE product)** | Desktop AI layer on Windows — voice, to-do automation, VS Code help, screen context, floating solutions | "It actually does work" — nobody else demos a living agent |

**House rules:** 15 days · feature-freeze Day 13 · local-first & private · works fully offline · v2-ready design · **every file ≤ 600 lines** · 1 step = 1 file, testable after every step.

---

## 2. Hardware Truth (measured on the actual laptop)

| Spec | Value | Meaning |
|------|-------|---------|
| RAM | 15.3 GB total, ~6 GB free with apps open | Small models only, close apps for demo |
| CPU | AMD Ryzen 7 PRO 5850U (8c/16t) | Decent for CPU inference |
| GPU | Integrated Radeon, 0.5 GB (no real VRAM) | Ollama runs on CPU, shares system RAM |

**=> Locked local model: `qwen3:4b` ONLY for the hackathon.** 8b/14b do NOT fit well with apps open. Production (later) = change **one line** in `brain/config.py` to `8b` or bigger.

---

## 3. The Routing Brain (final, locked)

**Rule of thumb:** *Never send to the cloud what the laptop can do well — always use the cloud when the laptop can't.*

| Task type | Brain | Why |
|-----------|-------|-----|
| Web / internet ("search this") | **Cloud: NIM → Gemini** | Needs internet anyway + bigger brain |
| Big thinking (report / complex explain) | **Cloud → local 4b** | Smartest available |
| Computer tasks (todo, open app, RAM, files) | **Local `qwen3:4b`** | Fast + private + works offline |
| Quick chat ("good morning") | **Local `qwen3:4b`** | Snappy, zero delay |

**Fallback chain (auto, never-die):** `NIM → Gemini → local qwen3:4b → rules.py (scripted)`
- Cloud dies → computer tasks still work (local).
- Internet dies → local + rules still work.
- **Demo can never die. Twice saved.**

**Why treating cloud sparingly is smart:** NIM free tier = ~40 requests/min. By only using it for web/big-brain tasks we never hit 429 during the live demo.

---

## 4. Tech Stack (chosen & why)

| Layer | Choice | Why |
|-------|--------|-----|
| Kernel | C + NASM, GRUB multiboot, QEMU, WSL2 | Real from-scratch bootable kernel |
| Agent brain | Python | User's strength; best LLM/tool/voice ecosystem |
| Local LLM | **Ollama `qwen3:4b`** (hackathon) | Fits laptop, native tool-calling, offline |
| Cloud LLM | **NVIDIA NIM** (free, ~40 RPM) + **Gemini free tier** spare | Free huge brains via OpenAI-compatible API |
| Voice in | Porcupine wake word + Whisper (STT) | Offline, reliable |
| Voice out | pyttsx3 (offline TTS) | No internet needed |
| UI (Home + overlay) | Node + Express + Socket.io | User's known stack, live updates |
| VS Code hook | VS Code Extension (JS) | Official API for file context |
| Web search | DuckDuckGo / SerpAPI | Free, background-able |
| Storage | Local JSON/Markdown files | Simple, auditable, portable, private |

**NIM (build.nvidia.com):** free NVIDIA Developer account → key `nvapi-…` → endpoint `https://integrate.api.nvidia.com/v1` → OpenAI-compatible (function calling works). Rate-limited ~40 RPM, model-dependent. Needs internet.
**Ollama:** local, offline, private-by-default. `ollama pull qwen3:4b`.

---

## 5. UX — How the User Experiences It (design targets)

### Journey A — Morning rollout
Laptop opens → Vision Home appears (to-do panel, status cards, engine badge "LOCAL") → "Hey Vision, good morning" → spoken reply → "complete task 1 and report task 2" → task marked done in panel + `report_task_2.md` created + spoken confirmation.

### Journey B — Stuck while coding (money demo)
In VS Code, select confusing lines → "Hey Vision, I'm stuck — find this" → extension sends file+selection → background web search (you keep typing) → floating solution card (snippet + explanation + source link + Copy) → "copy it" → clipboard set.

### Journey C — Privacy & control
Permission gate before ANY screen/file/web action (overlay Yes/No). All local thinking stays on the machine. Audit tab shows what Vision looked at/searched. No account, no cloud required.

---

## 6. Feature List (final scope)

**Kernel (bonus):** GRUB-boot in QEMU · animated splash · shell stub (`help echo uptime`) · serial heartbeat · print/color text.

**Voice:** wake word "Hey Vision" (offline) · STT (Whisper) · TTS (pyttsx3) · push-to-talk hotkey fallback · listening/thinking status dot.

**Vision Home (Node):** boot-to-Home · live to-do panel · status cards (time/uptime/memory/reports) · engine badge · settings (engine, voice, permissions) · audit log tab.

**Agent core (Python):** tool-calling agent loop `plan → pick tool → execute → observe → narrate` · session memory · rule fallback · multi-provider `llm.py` (Ollama + NIM + Gemini switch).

**Tools:** `todo.list/add/complete/delete/report` · `vscode.get_context` · `web.search` · `overlay.show` · `clipboard.set` · `app.launch` · `permission.ask` · `screen.ocr`.

**VS Code extension:** sends active file + selection → Vision; receives solution → floating card / side panel; copy/insert; thin bridge only.

**Security:** local-first (no cloud account) · permission gate · API-mode switch (NIM/Gemini keys optional) · audit log · offline no-keys operation.

---

## 7. Project Structure (every file ≤ 600 lines)

```
AI OS 2026/
├── kernel/                        # BONUS OS demo (all tiny)
│   ├── Makefile                   # build + run QEMU, one command
│   ├── linker.ld                  # kernel memory layout
│   ├── iso/grub.cfg               # GRUB boot config
│   └── src/ boot.asm kmain.c vga.c shell.c serial.c
├── brain/                         # Vision agent (Python) — the PRODUCT
│   ├── config.py                  # ONE settings file (engine, paths, keys)
│   ├── llm.py                     # router: local 4b → NIM → Gemini + fallback
│   ├── rules.py                   # scripted never-die fallback
│   ├── agent.py                   # task-type router + tool validation/retry
│   ├── wake.py stt.py tts.py      # voice pipeline
│   ├── main.py                    # wake→think→act→narrate loop
│   ├── requirements.txt
│   └── tools/ todo.py search.py system.py permission.py __init__.py
├── home/                          # Node UI (Vision Home + overlay)
│   ├── server.js                  # Express + Socket.io hub
│   └── public/ index.html app.js styles.css
├── vscode-extension/              # context hook + solution panel
│   ├── extension.js
│   └── package.json
├── storage/                       # local-first data
│   ├── todos/ reports/ logs/ config.json
├── docs/                          # MASTER_PLAN.md, demo-script.md
├── media/                         # screenshots + demo video
├── README.md
└── .gitignore
```

**570-line warning rule:** any file approaching 600 lines must be split into modules first (home UI is already split; do the same for anything else).

---

## 8. Phased Build — 1 step = 1 file, testable after every step

| Phase | File | What it proves | Owner |
|-------|------|----------------|-------|
| 0 | repo scaffold + toolchains | `qwen3:4b` answers from Python; folders exist | Me |
| 1 | `brain/config.py` | One settings file drives everything | You |
| 2 | `brain/llm.py` | local 4b works; NIM works; offline auto-fallback | You |
| 3 | `brain/rules.py` | Scripted answers for 5 demo commands | You |
| 4 | `brain/tools/todo.py` | Add/list/complete task + report file | You |
| 5 | `brain/agent.py` (v1 chat) | "complete task 1" works end-to-end from typed line | You+Me |
| 6 | `brain/tools/search.py` | Web search returns snippets + links | You |
| 7 | `brain/tools/system.py` + `permission.py` | Open app, copy clipboard, "ask first" gate | You |
| 8 | `wake.py` + `stt.py` + `tts.py` | Voice: "Hey Vision…" it answers | You |
| 9 | `brain/main.py` (v2 full loop) | Voice command completes a to-do ⭐ | Me |
| 10 | `home/server.js` | Live status/chat page from the agent | You |
| 11 | `home/public/*` | Vision Home: todo panel + chat + permissions | You |
| 12 | `vscode-extension/extension.js` | Send file+selection → floating solution card ⭐ | You |
| 13 | KERNEL files | "OS2026" boots with splash in QEMU | Me |
| 14 | docs/README + video + rehearsal ×3 | 5-min demo runs, offline proven | You |
| 15 | buffer — fixes only | — | Both |

**Rule:** Kernel is a LATE bonus (Phase 13). If anything slips, the kernel is cut first, never the agent.

---

## 9. 15-Day Timeline (2 people)

| Day | Kernel | Vision |
|-----|--------|--------|
| 0 | toolchain + Hello boots | Ollama 4b answers · NIM key works |
| 1–2 | splash + colored text | config, llm router, rules |
| 3–4 | shell stub + heartbeat (freeze) | todo tools, agent v1 |
| 5–6 | — | search, system, permission tools |
| 7–8 | — | voice pipeline (wake/stt/tts) |
| 9–10 | — | main loop, home server + UI |
| 11–12 | — | VS Code extension + solution flow |
| 13 | 🔒 FREEZE — fixes only | same |
| 14–15 | rehearsal ×3, video, pitch, README | same |

---

## 10. Division of Labor

| Area | Owner |
|------|-------|
| Kernel boot/drivers/interrupts, repo scaffold, agent architecture, security gating, demo engineering | **Me** |
| Voice, LLM, tools, VS Code extension, Node UI, docs/README/pitch/video | **You** |
| Daily code review + merge/debt cleanup | **Me** |

---

## 11. Acceptance Checklist (ship it)

- [ ] `qwen3:4b` handles all computer tasks; web tasks go to NIM
- [ ] "Hey Vision, complete task 1 and report task 2" works live
- [ ] VS Code "search this" → floating solution card with source link
- [ ] Permission prompt before first sensitive action
- [ ] Airplane-mode: to-do + voice + computer tasks all work (offline)
- [ ] No account/keys required; cloud switch demonstrable
- [ ] `make run` (or equivalent) boots kernel splash
- [ ] Every file ≤ 600 lines
- [ ] 5-min demo rehearsed 3× with zero paper-fail

---

## 12. Demo Script (5 minutes)

1. Boot the OS in QEMU (10s) — *"I wrote this from scratch."*
2. Vision Home + "Good morning" (30s)
3. "complete task 1, report task 2" — watch it act + narrate (1m)
4. In VS Code "I'm stuck — search this" → floating solution (1m)
5. Permission gate + local badge + one-line hero pitch (1m30s)

---

## 13. Risks → Mitigations

| Risk | Fix |
|------|-----|
| Cloud/wifi dies live | Local 4b + rules fallback — computer tasks never die |
| NIM 429 rate limit | Use cloud only for web/big-brain; well-behaved client (retry/backoff) |
| Voice flaky (mic/noise) | Push-to-talk hotkey = same path, always works |
| 4b "smartness" | Cloud brain for hard steps; rules for rehearsed commands |
| RAM tight (6GB free) | Close heavy apps before demo; only 4b runs locally |
| Scope creep | Freeze Day 13; v2 ideas → docs/ROADMAP-v2 (set up later) |
| File too big | 600-line rule: split into modules (home already done this way) |

---

## 14. Production Future (v2+ — NOT now, only ideas to remember)

- Local `qwen3:8b`/`14b` when hardware allows → one-line config change
- Autonomous screen watching (vision model in the loop)
- PDF reports everywhere · long-term personal memory · more app integrations
- Whole build related reference: our local default model lives in `brain/config.py`