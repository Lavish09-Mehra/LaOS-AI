// ============================================================
// LavOS 2026 — home/server.js
// Node + Express + Socket.io server.
// Serves the UI, bridges to Python brain via HTTP,
// relays API calls for todos/audit/settings/stream.
// ============================================================

const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const path = require("path");

const app = express();
const server = http.createServer(app);
const io = new Server(server);

const PORT = process.env.PORT || 3000;
const BRAIN_URL = process.env.BRAIN_URL || "http://127.0.0.1:8080";

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

// --- Health -----------------------------------------------------------
app.get("/health", (_, res) => res.json({ status: "ok", brain: BRAIN_URL }));

// --- API relay helper -------------------------------------------------
async function brainFetch(path, method, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch(`${BRAIN_URL}${path}`, opts);
  return resp.json();
}

// --- Settings ---------------------------------------------------------
app.get("/api/settings", async (_, res) => {
  try { res.json(await brainFetch("/settings", "GET")); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

app.post("/api/settings", async (req, res) => {
  try { res.json(await brainFetch("/settings", "POST", req.body)); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

// --- Todos ------------------------------------------------------------
app.get("/api/todos", async (_, res) => {
  try { res.json(await brainFetch("/todos", "GET")); }
  catch (e) { res.json({ ok: false, error: e.message, data: [] }); }
});

app.post("/api/todos", async (req, res) => {
  try { res.json(await brainFetch("/todos", "POST", req.body)); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

app.post("/api/todos/:id/complete", async (req, res) => {
  try { res.json(await brainFetch(`/todos/${req.params.id}/complete`, "POST")); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

app.delete("/api/todos/:id", async (req, res) => {
  try { res.json(await brainFetch(`/todos/${req.params.id}`, "DELETE")); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

// --- Audit ------------------------------------------------------------
app.get("/api/audit", async (_, res) => {
  try { res.json(await brainFetch("/audit", "GET")); }
  catch (e) { res.json({ ok: false, error: e.message, data: { entries: [] } }); }
});

app.post("/api/audit/clear", async (_, res) => {
  try { res.json(await brainFetch("/audit/clear", "POST")); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

// --- Stream -----------------------------------------------------------
app.post("/api/stream/start", async (_, res) => {
  try { res.json(await brainFetch("/stream/start", "POST")); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

app.post("/api/stream/stop", async (_, res) => {
  try { res.json(await brainFetch("/stream/stop", "POST")); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

app.get("/api/stream/frame", async (_, res) => {
  try { res.json(await brainFetch("/stream/frame", "GET")); }
  catch (e) { res.json({ ok: false, error: e.message }); }
});

// --- Socket.io bridge -------------------------------------------------
io.on("connection", (socket) => {
  console.log(`[home] client connected: ${socket.id}`);

  socket.on("chat", async (data) => {
    const text = (data.text || "").trim();
    const sessionId = data.session_id || null;
    if (!text) return;

    socket.emit("status", { state: "thinking" });

    try {
      const result = await brainFetch("/chat", "POST", { text, session_id: sessionId });
      socket.emit("reply", {
        text: result.reply || result.text || "",
        tool_call: result.tool_call || null,
        engine: result.engine || "unknown",
        session_id: result.session_id || sessionId,
      });
    } catch (err) {
      console.error("[home] brain error:", err.message);
      socket.emit("reply", {
        text: "Brain offline. Is Python running?",
        tool_call: null,
        engine: "error",
        session_id: sessionId,
      });
    }

    socket.emit("status", { state: "idle" });
  });

  socket.on("permission_grant", (data) => {
    socket.broadcast.emit("permission_result", { action_id: data.action_id, status: "granted" });
  });

  socket.on("permission_deny", (data) => {
    socket.broadcast.emit("permission_result", { action_id: data.action_id, status: "denied" });
  });

  socket.on("disconnect", () => {
    console.log(`[home] client disconnected: ${socket.id}`);
  });
});

// --- Start ------------------------------------------------------------
server.listen(PORT, () => {
  console.log(`LavOS 2026`);
  console.log(`  http://localhost:${PORT}`);
  console.log(`  brain: ${BRAIN_URL}`);
});
