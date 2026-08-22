// LavOS 2026 - app.js
const socket = io();
let sessionId = null;
let isListening = false;
let recognition = null;
let settings = {};
let streamInterval = null;

// ===== WINDOW MANAGEMENT =====
function openApp(id) {
  document.getElementById(id).classList.add('open');
  document.getElementById('lavosPanel').classList.remove('open');
  document.getElementById('calPanel').classList.remove('open');
  document.getElementById('lavosSearch').classList.remove('open');
}
function closeApp(id) { document.getElementById(id).classList.remove('open'); }

function toggleSearch() {
  const btn = document.getElementById('lavosSearch');
  const isOpen = btn.classList.toggle('open');
  btn.setAttribute('aria-expanded', isOpen);
  document.getElementById('lavosPanel').classList.add('open');
  document.getElementById('calPanel').classList.remove('open');
}
function toggleAiPanel() {
  document.getElementById('calPanel').classList.remove('open');
  document.getElementById('lavosPanel').classList.toggle('open');
  document.getElementById('lavosSearch').classList.remove('open');
}
function toggleCal() {
  document.getElementById('lavosPanel').classList.remove('open');
  document.getElementById('lavosSearch').classList.remove('open');
  document.getElementById('calPanel').classList.toggle('open');
}

// ===== CLOCK / CALENDAR =====
function tick() {
  const now = new Date();
  document.getElementById('clockTime').textContent = now.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  document.getElementById('clockDate').textContent = now.toLocaleDateString([], {weekday:'short', month:'short', day:'numeric'});
  document.getElementById('calTime').textContent = now.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  document.getElementById('calDate').textContent = now.toLocaleDateString([], {weekday:'long', month:'long', day:'numeric', year:'numeric'});
}
setInterval(tick, 1000); tick();

function buildCalendar() {
  const grid = document.getElementById('calGrid');
  const now = new Date();
  const y = now.getFullYear(), m = now.getMonth(), today = now.getDate();
  const first = new Date(y, m, 1).getDay();
  const days = new Date(y, m+1, 0).getDate();
  let h = '';
  ['S','M','T','W','T','F','S'].forEach(function(d){ h += '<div class="dow">'+d+'</div>'; });
  for (let i=0; i<first; i++) h += '<div class="day"></div>';
  for (let d=1; d<=days; d++) h += '<div class="day'+(d===today?' today':'')+'">'+d+'</div>';
  grid.innerHTML = h;
}
buildCalendar();

// ===== CHAT =====
function addPanelMessage(text, role, engine) {
  const chat = document.getElementById('panelChat');
  const div = document.createElement('div');
  div.className = 'panel-msg ' + role;
  div.innerHTML = escapeHtml(text) + (engine ? '<div class="engine">' + engine + '</div>' : '');
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function sendMessage() {
  const input = document.getElementById('panelInput');
  const text = input.value.trim();
  if (!text) return;
  addPanelMessage(text, 'user');
  input.value = '';
  socket.emit('chat', { text: text, session_id: sessionId });
  document.getElementById('footEngine').className = 'dot';
}

document.getElementById('panelInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') sendMessage();
});

socket.on('reply', function(data) {
  addPanelMessage(data.text || '...', 'assistant', data.engine || '');
  if (data.session_id) sessionId = data.session_id;
  document.getElementById('footEngine').className = 'dot on';
  if (data.text) speak(data.text);
});

socket.on('status', function(data) {
  document.getElementById('footEngine').className = data.state === 'thinking' ? 'dot' : 'dot on';
});

socket.on('permission_request', function(data) {
  if (confirm('Permission: ' + (data.description || 'Allow action?'))) {
    socket.emit('permission_grant', { action_id: data.action_id });
  } else {
    socket.emit('permission_deny', { action_id: data.action_id });
  }
});

// ===== VOICE INPUT (Web Speech API) =====
function toggleMic() {
  if (isListening) { stopMic(); } else { startMic(); }
}

function startMic() {
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    addPanelMessage('Speech recognition not supported in this browser', 'assistant');
    return;
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';
  recognition.onresult = function(e) {
    const transcript = e.results[0][0].transcript;
    addPanelMessage(transcript, 'user');
    socket.emit('chat', { text: transcript, session_id: sessionId });
    stopMic();
  };
  recognition.onerror = function() { stopMic(); };
  recognition.onend = function() { stopMic(); };
  recognition.start();
  isListening = true;
  document.getElementById('micBtn').classList.add('listening');
  document.getElementById('footVoice').className = 'dot on';
}

function stopMic() {
  if (recognition) { try { recognition.stop(); } catch(e){} recognition = null; }
  isListening = false;
  document.getElementById('micBtn').classList.remove('listening');
  document.getElementById('footVoice').className = 'dot';
}

// ===== VOICE OUTPUT =====
function speak(text) {
  if (!settings.voice_output) return;
  if (!('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.0;
  u.pitch = 1.0;
  speechSynthesis.speak(u);
}

// ===== SCREEN STREAM =====
function startStream() {
  fetch('/api/stream/start', {method:'POST'}).then(function(r){return r.json();}).then(function(d){
    if (d.ok) {
      document.getElementById('streamStartBtn').disabled = true;
      document.getElementById('streamStopBtn').disabled = false;
      document.getElementById('streamAnalyzeBtn').disabled = false;
      document.getElementById('streamStatus').textContent = 'streaming...';
      document.getElementById('taskbarStreamDot').classList.add('active');
      document.getElementById('footStream').className = 'dot on';
      streamInterval = setInterval(fetchFrame, 1000);
    }
  });
}

function stopStream() {
  fetch('/api/stream/stop', {method:'POST'}).then(function(r){return r.json();}).then(function(d){
    if (streamInterval) { clearInterval(streamInterval); streamInterval = null; }
    document.getElementById('streamStartBtn').disabled = false;
    document.getElementById('streamStopBtn').disabled = true;
    document.getElementById('streamAnalyzeBtn').disabled = true;
    document.getElementById('streamStatus').textContent = 'stopped';
    document.getElementById('streamPreview').innerHTML = 'stream inactive';
    document.getElementById('taskbarStreamDot').classList.remove('active');
    document.getElementById('footStream').className = 'dot';
  });
}

function fetchFrame() {
  fetch('/api/stream/frame').then(function(r){return r.json();}).then(function(d){
    if (d.ok && d.image) {
      document.getElementById('streamPreview').innerHTML = '<img src="data:image/jpeg;base64,' + d.image + '">';
      document.getElementById('streamStatus').textContent = 'streaming - ' + new Date().toLocaleTimeString();
    }
  }).catch(function(){});
}

function analyzeStream() {
  addPanelMessage('Analyzing screen...', 'user');
  socket.emit('chat', { text: 'describe what you see on my screen', session_id: sessionId });
}

document.getElementById('streamStartBtn').addEventListener('click', startStream);
document.getElementById('streamStopBtn').addEventListener('click', stopStream);
document.getElementById('streamAnalyzeBtn').addEventListener('click', analyzeStream);

// ===== TODOS =====
function fetchTodos() {
  fetch('/api/todos').then(function(r){return r.json();}).then(function(d){
    if (d.ok) renderTodos(d.data || []);
  }).catch(function(){});
}

function renderTodos(todos) {
  const list = document.getElementById('todoList');
  const badge = document.getElementById('todoBadge');
  const pending = todos.filter(function(t){return !t.done;});
  if (pending.length > 0) { badge.classList.add('show'); } else { badge.classList.remove('show'); }
  if (todos.length === 0) { list.innerHTML = '<div style="color:var(--text-dim);font-size:12px;padding:8px 0;">no todos</div>'; return; }
  list.innerHTML = '';
  todos.forEach(function(t) {
    const div = document.createElement('div');
    div.className = 'todo-item' + (t.done ? ' done' : '');
    div.innerHTML = '<div class="todo-check">' + (t.done ? '&#10003;' : '') + '</div><span>' + escapeHtml(t.text) + '</span>';
    div.addEventListener('click', function() {
      if (!t.done) {
        fetch('/api/todos/' + t.id + '/complete', {method:'POST'}).then(function(){ fetchTodos(); });
      }
    });
    list.appendChild(div);
  });
}

function addTodoFromInput() {
  const input = document.getElementById('todoInput');
  const text = input.value.trim();
  if (!text) return;
  fetch('/api/todos', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: text})
  }).then(function(){ input.value = ''; fetchTodos(); });
}

document.getElementById('todoAddBtn').addEventListener('click', addTodoFromInput);
document.getElementById('todoInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') addTodoFromInput();
});
document.getElementById('todoReportBtn').addEventListener('click', function() {
  socket.emit('chat', { text: 'generate a report of my todos', session_id: sessionId });
});

// ===== AUDIT LOG =====
function fetchAudit() {
  fetch('/api/audit').then(function(r){return r.json();}).then(function(d){
    if (d.ok && d.data && d.data.entries) renderAudit(d.data.entries);
  }).catch(function(){});
}

function renderAudit(entries) {
  const list = document.getElementById('auditList');
  if (entries.length === 0) { list.innerHTML = '<div style="color:var(--text-dim);font-size:12px;">no entries yet</div>'; return; }
  list.innerHTML = '';
  entries.forEach(function(e) {
    const div = document.createElement('div');
    div.className = 'audit-entry';
    const ts = (e.ts || '').substring(0, 19).replace('T', ' ');
    div.innerHTML = '<span class="ts">' + escapeHtml(ts) + '</span>' + escapeHtml(e.action) + ': ' + escapeHtml(e.detail);
    list.appendChild(div);
  });
}

document.getElementById('auditRefreshBtn').addEventListener('click', fetchAudit);
document.getElementById('auditClearBtn').addEventListener('click', function() {
  if (confirm('Clear audit log?')) {
    fetch('/api/audit/clear', {method:'POST'}).then(function(){ fetchAudit(); });
  }
});

// ===== SETTINGS =====
function loadSettings() {
  fetch('/api/settings').then(function(r){return r.json();}).then(function(d){
    if (d.ok && d.data) {
      settings = d.data;
      document.getElementById('cfgAiName').value = settings.ai_name || '';
      document.getElementById('cfgWakeWord').value = settings.wake_word || '';
      document.getElementById('cfgVoiceOn').checked = !!settings.voice_output;
      document.getElementById('cfgVoiceEngine').value = settings.voice_engine || 'browser';
      document.getElementById('cfgStreamOn').checked = !!settings.stream_enabled;
      document.getElementById('cfgStreamFps').value = String(settings.stream_fps || 1);
      document.getElementById('cfgGroqKey').value = settings.groq_api_key || '';
      document.getElementById('cfgGroqModel').value = settings.groq_model || '';
      document.getElementById('cfgNimKey').value = settings.nim_api_key || '';
      document.getElementById('cfgNimModel').value = settings.nim_model || '';
      document.getElementById('cfgZenKey').value = settings.zen_api_key || '';
      document.getElementById('cfgOllamaOn').checked = !!settings.ollama_enabled;
      document.getElementById('cfgOllamaUrl').value = settings.ollama_url || '';
      document.getElementById('cfgOllamaChat').value = settings.ollama_chat_model || '';
      document.getElementById('cfgOllamaVision').value = settings.ollama_vision_model || '';
      document.getElementById('cfgPermissions').value = settings.permissions || 'always';
      var pt = document.getElementById('panelTitle');
      if (settings.ai_name) pt.textContent = settings.ai_name;
    }
  }).catch(function(){});
}

function saveSettings() {
  var s = {
    ai_name: document.getElementById('cfgAiName').value.trim(),
    wake_word: document.getElementById('cfgWakeWord').value.trim(),
    voice_output: document.getElementById('cfgVoiceOn').checked,
    voice_engine: document.getElementById('cfgVoiceEngine').value,
    stream_enabled: document.getElementById('cfgStreamOn').checked,
    stream_fps: parseInt(document.getElementById('cfgStreamFps').value) || 1,
    groq_api_key: document.getElementById('cfgGroqKey').value.trim(),
    groq_model: document.getElementById('cfgGroqModel').value.trim(),
    nim_api_key: document.getElementById('cfgNimKey').value.trim(),
    nim_model: document.getElementById('cfgNimModel').value.trim(),
    zen_api_key: document.getElementById('cfgZenKey').value.trim(),
    ollama_enabled: document.getElementById('cfgOllamaOn').checked,
    ollama_url: document.getElementById('cfgOllamaUrl').value.trim(),
    ollama_chat_model: document.getElementById('cfgOllamaChat').value.trim(),
    ollama_vision_model: document.getElementById('cfgOllamaVision').value.trim(),
    permissions: document.getElementById('cfgPermissions').value
  };
  fetch('/api/settings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(s)
  }).then(function(r){return r.json();}).then(function(d){
    settings = s;
    if (s.ai_name) document.getElementById('panelTitle').textContent = s.ai_name;
  });
}

document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);

// ===== UTILITIES =====
function escapeHtml(str) {
  var d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ===== INIT =====
loadSettings();
fetchTodos();
fetchAudit();
