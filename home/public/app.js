// ============================================================
// LavOS 2026 — home/public/app.js
// Frontend logic for Vision Home.
// Connects to server.js via Socket.io, sends messages,
// renders replies, handles permission dialogs.
// ============================================================

const socket = io();
const chatArea = document.getElementById("chatArea");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const statusPill = document.getElementById("statusPill");
const permissionBar = document.getElementById("permissionBar");
const permText = document.getElementById("permText");
const permAllow = document.getElementById("permAllow");
const permDeny = document.getElementById("permDeny");

let sessionId = null;
let welcomeEl = document.querySelector(".welcome");

// --- Send message -------------------------------------------------------
function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  // Remove welcome screen
  if (welcomeEl) {
    welcomeEl.remove();
    welcomeEl = null;
  }

  addMessage(text, "user");
  userInput.value = "";
  socket.emit("chat", { text, session_id: sessionId });
}

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

// --- Receive reply ------------------------------------------------------
socket.on("reply", (data) => {
  addMessage(data.text, "assistant", data.engine);
  if (data.session_id) sessionId = data.session_id;
});

// --- Status updates -----------------------------------------------------
socket.on("status", (data) => {
  statusPill.textContent = data.state.toUpperCase();
  statusPill.className = "status-pill " + data.state;
});

// --- Permission dialog --------------------------------------------------
socket.on("permission_request", (data) => {
  permissionBar.classList.remove("hidden");
  permText.textContent = data.description || "Permission requested";
  permAllow.onclick = () => {
    socket.emit("permission_grant", { action_id: data.action_id });
    permissionBar.classList.add("hidden");
  };
  permDeny.onclick = () => {
    socket.emit("permission_deny", { action_id: data.action_id });
    permissionBar.classList.add("hidden");
  };
});

// --- Render message -----------------------------------------------------
function addMessage(text, role, engine) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.innerHTML = `
    <div class="msg-text">${escapeHtml(text)}</div>
    ${engine ? `<div class="msg-meta">${engine}</div>` : ""}
  `;
  chatArea.appendChild(div);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}
