# ============================================================
# LavOS 2026 — brain/rules.py  (never-die fallback)
# Hardcoded matching for the 3-5 demo commands so the LIVE demo
# works even if every LLM/network path fails.
# e.g. "complete task 1" / "good morning" / "report task 2".
# Todo(phase 3): keyword->intent map, answers for demo commands,
# keeps the same tool interface as llm.py so agent.py is blind
# to which brain answered. This file saves the demo.
# ============================================================