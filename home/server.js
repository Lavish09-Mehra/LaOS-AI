// ============================================================
// LavOS 2026 — home/server.js  (Vision Home UI server)
// Small Node + Express + Socket.io server on localhost.
// Serves the UI, bridges to Python brain via HTTP, and
// broadcasts status/typing/permission events to the UI.
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

// --- Static files -------------------------------------------------------
app.use(express.static(path.join(__dirname, "public")));

// --- Health check --------------------------------------------------------
app.get("/health", (_, res) => res.json({ status: "ok", brain: BRAIN_URL }));

// --- Socket.io bridge to Python brain ------------------------------------
io.on("connection", (socket) => {
  console.log(`[home] client connected: ${socket.id}`);

  // User sends a chat message
  socket.on("chat", async (data) => {
    const text = (data.text || "").trim();
    const sessionId = data.session_id || null;
    if (!text) return;

    // Send typing status
    socket.emit("status", { state: "thinking" });

    try {
      const resp = await fetch(`${BRAIN_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, session_id: sessionId }),
      });
      const result = await resp.json();

      // Send reply back
      socket.emit("reply", {
        text: result.reply || result.text || "",
        tool_call: result.tool_call || null,
        engine: result.engine || "unknown",
        session_id: result.session_id || sessionId,
      });
    } catch (err) {
      console.error("[home] brain error:", err.message);
      socket.emit("reply", {
        text: "Sorry, Vision brain is offline. Is Python running?",
        tool_call: null,
        engine: "error",
        session_id: sessionId,
      });
    }

    socket.emit("status", { state: "idle" });
  });

  // Permission events from UI
  socket.on("permission_grant", (data) => {
    socket.broadcast.emit("permission_result", {
      action_id: data.action_id,
      status: "granted",
    });
  });

  socket.on("permission_deny", (data) => {
    socket.broadcast.emit("permission_result", {
      action_id: data.action_id,
      status: "denied",
    });
  });

  socket.on("disconnect", () => {
    console.log(`[home] client disconnected: ${socket.id}`);
  });
});

// --- Start server -------------------------------------------------------
server.listen(PORT, () => {
  console.log(`LavOS 2026 — Vision Home`);
  console.log(`  http://localhost:${PORT}`);
  console.log(`  brain: ${BRAIN_URL}`);
});
