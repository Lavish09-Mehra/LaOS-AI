// ============================================================
// LavOS 2026 — home/server.js  (Vision Home UI server)
// Small Node + Express + Socket.io server on localhost.
// Serves the UI, opens a live socket to the Python brain, and
// routes user messages <-> tools. The "window" into Vision.
// Todo(phase 10): /public static, socket bridge to brain/main.py,
// broadcast status/typing/permission events to the overlay.
// ============================================================