const socket = io();
let sessionId = null;
let isListening = false;
let recognition = null;
let settings = {};
let streamInterval = null;
let dragState = null;

// ===== WINDOW MANAGEMENT =====
var openWindows = {};
var windowPositions = {
  'win-terminal': { top: 80, left: 120 },
  'win-files': { top: 100, left: 200 },
  'win-browser': { top: 90, left: 240 },
  'win-settings': { top: 70, left: 180 },
  'win-notes': { top: 100, left: 200 },
  'win-audit': { top: 110, left: 260 },
  'win-stream': { top: 90, left: 220 },
  'win-calendar': { top: 60, left: 160 }
};
var windowCount = 0;

function openApp(id) {
  var win = document.getElementById(id);
  if (!win) return;
  if (openWindows[id]) {
    minimizeApp(id);
    return;
  }
  if (!win.style.top) {
    var pos = windowPositions[id] || { top: 80 + windowCount * 30, left: 120 + windowCount * 30 };
    win.style.top = pos.top + 'px';
    win.style.left = pos.left + 'px';
  }
  win.classList.add('open', 'focused');
  openWindows[id] = true;
  windowCount++;
  closeOverview();
  closeTray();
  updateDockIndicator(id, true);
}
function closeApp(id) {
  var win = document.getElementById(id);
  win.classList.add('closing');
  win.classList.remove('focused');
  setTimeout(function() { win.classList.remove('open', 'closing'); }, 200);
  openWindows[id] = false;
  windowCount = Math.max(0, windowCount - 1);
  updateDockIndicator(id, false);
}
function minimizeApp(id) {
  var win = document.getElementById(id);
  win.classList.add('closing');
  win.classList.remove('focused');
  setTimeout(function() { win.classList.remove('open', 'closing'); }, 200);
  openWindows[id] = false;
  windowCount = Math.max(0, windowCount - 1);
  updateDockIndicator(id, false);
}
function toggleFullScreen(id) {
  var win = document.getElementById(id);
  if (win.dataset.maximized === 'true') {
    win.style.top = win.dataset.prevTop;
    win.style.left = win.dataset.prevLeft;
    win.style.width = win.dataset.prevWidth;
    win.style.height = win.dataset.prevHeight;
    win.dataset.maximized = 'false';
  } else {
    win.dataset.prevTop = win.style.top;
    win.dataset.prevLeft = win.style.left;
    win.dataset.prevWidth = win.style.width;
    win.dataset.prevHeight = win.style.height;
    win.style.top = '0';
    win.style.left = '0';
    win.style.width = '100%';
    win.style.height = '100%';
    win.dataset.maximized = 'true';
  }
}
function showDesktop() {
  document.querySelectorAll('.window.open').forEach(function(w) {
    w.classList.add('closing');
    w.classList.remove('focused');
    setTimeout(function() { w.classList.remove('open', 'closing'); }, 200);
    openWindows[w.id] = false;
  });
  windowCount = 0;
  closeOverview();
  updateAllDockIndicators();
}
function updateDockIndicator(id, open) {
  var app = id.replace('win-', '');
  var item = document.querySelector('.dock-item[data-app="' + app + '"]');
  if (item) {
    if (open) item.classList.add('open');
    else item.classList.remove('open');
  }
}
function updateAllDockIndicators() {
  document.querySelectorAll('.dock-item').forEach(function(item) {
    var app = item.dataset.app;
    var winId = 'win-' + app;
    if (openWindows[winId]) item.classList.add('open');
    else item.classList.remove('open');
  });
}
function dockClick(app) {
  var winId = 'win-' + app;
  if (app === 'desktop') { showDesktop(); return; }
  if (openWindows[winId]) { minimizeApp(winId); }
  else { openApp(winId); }
}
function focusWindow(id) {
  document.querySelectorAll('.window').forEach(function(w) { w.classList.remove('focused'); });
  document.getElementById(id).classList.add('focused');
}

// ===== DYNAMIC ISLAND =====
var dockTimer = null;
var dockIsland = document.getElementById('dockIsland');
dockIsland.addEventListener('mouseenter', function() {
  clearTimeout(dockTimer);
  dockIsland.classList.add('expanded');
});
dockIsland.addEventListener('mouseleave', function() {
  clearTimeout(dockTimer);
  dockTimer = setTimeout(function() {
    dockIsland.classList.remove('expanded');
  }, 5000);
});
dockIsland.addEventListener('click', function(e) {
  if (!e.target.closest('.dock-item')) {
    clearTimeout(dockTimer);
    dockIsland.classList.add('expanded');
    dockTimer = setTimeout(function() { dockIsland.classList.remove('expanded'); }, 5000);
  }
});

// Window dragging
document.addEventListener('mousedown', function(e) {
  var header = e.target.closest('.win-header');
  if (!header || e.target.closest('.win-controls')) return;
  var win = header.closest('.window');
  if (!win) return;
  dragState = { win: win, startX: e.clientX, startY: e.clientY, startTop: win.offsetTop, startLeft: win.offsetLeft };
  focusWindow(win.id);
});
document.addEventListener('mousemove', function(e) {
  if (!dragState) return;
  var dx = e.clientX - dragState.startX;
  var dy = e.clientY - dragState.startY;
  dragState.win.style.left = (dragState.startLeft + dx) + 'px';
  dragState.win.style.top = (dragState.startTop + dy) + 'px';
});
document.addEventListener('mouseup', function() { dragState = null; });

// Double-click header to toggle full screen
document.addEventListener('dblclick', function(e) {
  var header = e.target.closest('.win-header');
  if (!header || e.target.closest('.win-controls')) return;
  var win = header.closest('.window');
  if (win) toggleFullScreen(win.id);
});

// Click window to focus
document.addEventListener('mousedown', function(e) {
  var win = e.target.closest('.window');
  if (win) focusWindow(win.id);
});

// ===== OVERVIEW =====
function toggleOverview() {
  var ov = document.getElementById('overview');
  if (ov.classList.contains('open')) { closeOverview(); return; }
  openOverview();
}
function openOverview() {
  var ov = document.getElementById('overview');
  ov.classList.add('open');
  ov.style.animation = '';
  document.getElementById('overviewSearch').value = '';
  document.getElementById('overviewSearch').focus();
  renderOverviewThumbs();
}
function closeOverview() {
  var ov = document.getElementById('overview');
  ov.style.animation = 'fadeOut .2s var(--ease) forwards';
  setTimeout(function() { ov.classList.remove('open'); ov.style.animation = ''; }, 200);
}
function renderOverviewThumbs() {
  var c = document.getElementById('overviewWindows');
  c.innerHTML = '';
  document.querySelectorAll('.window.open').forEach(function(w) {
    var title = w.querySelector('.win-title').textContent;
    var div = document.createElement('div');
    div.className = 'overview-thumb';
    div.innerHTML = '<div class="thumb-title">' + title + '</div>';
    div.onclick = function() { openApp(w.id); closeOverview(); };
    c.appendChild(div);
  });
  if (c.children.length === 0) {
    c.innerHTML = '<div style="color:var(--text-muted);font-size:14px;padding:40px;">No open windows</div>';
  }
}
document.getElementById('activitiesBtn').addEventListener('click', toggleOverview);
document.getElementById('overview').addEventListener('click', function(e) {
  if (e.target === this) closeOverview();
});

// ===== TRAY =====
function openTray() {
  document.getElementById('trayDropdown').classList.add('open');
}
function closeTray() {
  var el = document.getElementById('trayDropdown');
  el.style.animation = 'fadeOut .15s ease forwards';
  setTimeout(function() { el.classList.remove('open'); el.style.animation = ''; }, 150);
}
document.getElementById('systemTray').addEventListener('mouseenter', function() {
  openTray();
});
document.getElementById('systemTray').addEventListener('mouseleave', function(e) {
  var dd = document.getElementById('trayDropdown');
  setTimeout(function() {
    if (!dd.matches(':hover') && !document.getElementById('systemTray').matches(':hover')) closeTray();
  }, 200);
});
document.getElementById('trayDropdown').addEventListener('mouseleave', function() {
  if (!document.getElementById('systemTray').matches(':hover')) closeTray();
});
document.getElementById('systemTray').addEventListener('click', function(e) {
  e.stopPropagation();
  if (document.getElementById('trayDropdown').classList.contains('open')) closeTray();
  else openTray();
});

// ===== CALENDAR =====
var calMonthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
var calToday = new Date();
var calViewYear = calToday.getFullYear();
var calViewMonth = calToday.getMonth();
var calMiniYear = calViewYear;
var calMiniMonth = calViewMonth;
var calSelectedDate = new Date();

function renderCalMain() {
  document.getElementById('calMonthLabel').textContent = calMonthNames[calViewMonth];
  document.getElementById('calYearLabel').textContent = calViewYear;
  var grid = document.getElementById('calDaysGrid');
  grid.innerHTML = '';
  var firstDay = new Date(calViewYear, calViewMonth, 1).getDay();
  var daysInMonth = new Date(calViewYear, calViewMonth + 1, 0).getDate();
  var daysInPrev = new Date(calViewYear, calViewMonth, 0).getDate();
  var totalCells = 42, cellIndex = 0;
  for (var i = firstDay - 1; i >= 0; i--) { addCalCell(grid, daysInPrev - i, true, false, false); cellIndex++; }
  for (var d = 1; d <= daysInMonth; d++) {
    var isToday = d === calToday.getDate() && calViewMonth === calToday.getMonth() && calViewYear === calToday.getFullYear();
    var isSel = calSelectedDate && d === calSelectedDate.getDate() && calViewMonth === calSelectedDate.getMonth() && calViewYear === calSelectedDate.getFullYear();
    addCalCell(grid, d, false, isToday, isSel);
    cellIndex++;
  }
  var trailDay = 1;
  while (cellIndex < totalCells) { addCalCell(grid, trailDay, true, false, false); trailDay++; cellIndex++; }
}
function addCalCell(grid, num, muted, isToday, isSel) {
  var el = document.createElement('div');
  el.className = 'cal-day' + (muted ? ' muted' : '') + (isToday ? ' today' : '') + (isSel ? ' selected' : '');
  var numEl = document.createElement('div');
  numEl.className = 'cal-day-num';
  numEl.textContent = num;
  el.appendChild(numEl);
  if (!muted) {
    el.addEventListener('click', (function(d) {
      return function() {
        calSelectedDate = new Date(calViewYear, calViewMonth, d);
        renderCalMain();
      };
    })(num));
  }
  grid.appendChild(el);
}
function renderCalMini() {
  document.getElementById('miniLabel').textContent = calMonthNames[calMiniMonth].slice(0, 3).toUpperCase() + ' ' + calMiniYear;
  var grid = document.getElementById('miniGrid');
  grid.innerHTML = '';
  var wk = ['S','M','T','W','T','F','S'];
  wk.forEach(function(w) { var el = document.createElement('div'); el.className = 'mw'; el.textContent = w; grid.appendChild(el); });
  var firstDay = new Date(calMiniYear, calMiniMonth, 1).getDay();
  var daysInMonth = new Date(calMiniYear, calMiniMonth + 1, 0).getDate();
  var daysInPrev = new Date(calMiniYear, calMiniMonth, 0).getDate();
  for (var i = firstDay - 1; i >= 0; i--) { var el = document.createElement('div'); el.className = 'md muted'; el.textContent = daysInPrev - i; grid.appendChild(el); }
  for (var d = 1; d <= daysInMonth; d++) {
    var el = document.createElement('div');
    var isToday = d === calToday.getDate() && calMiniMonth === calToday.getMonth() && calMiniYear === calToday.getFullYear();
    el.className = 'md' + (isToday ? ' today' : '');
    el.textContent = d;
    el.addEventListener('click', (function(d) {
      return function() {
        calViewYear = calMiniYear; calViewMonth = calMiniMonth;
        calSelectedDate = new Date(calMiniYear, calMiniMonth, d);
        renderCalMain(); renderCalMini();
      };
    })(d));
    grid.appendChild(el);
  }
  var totalCells = firstDay + daysInMonth;
  var trailing = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
  for (var t = 1; t <= trailing; t++) { var el = document.createElement('div'); el.className = 'md muted'; el.textContent = t; grid.appendChild(el); }
}
document.getElementById('calPrevBtn').addEventListener('click', function() {
  calViewMonth--; if (calViewMonth < 0) { calViewMonth = 11; calViewYear--; }
  calMiniMonth = calViewMonth; calMiniYear = calViewYear;
  renderCalMain(); renderCalMini();
});
document.getElementById('calNextBtn').addEventListener('click', function() {
  calViewMonth++; if (calViewMonth > 11) { calViewMonth = 0; calViewYear++; }
  calMiniMonth = calViewMonth; calMiniYear = calViewYear;
  renderCalMain(); renderCalMini();
});
document.getElementById('miniPrev').addEventListener('click', function() {
  calMiniMonth--; if (calMiniMonth < 0) { calMiniMonth = 11; calMiniYear--; }
  renderCalMini();
});
document.getElementById('miniNext').addEventListener('click', function() {
  calMiniMonth++; if (calMiniMonth > 11) { calMiniMonth = 0; calMiniYear++; }
  renderCalMini();
});
document.getElementById('calTodayBtn').addEventListener('click', function() {
  calToday = new Date();
  calViewYear = calToday.getFullYear(); calViewMonth = calToday.getMonth();
  calMiniYear = calViewYear; calMiniMonth = calViewMonth;
  calSelectedDate = new Date();
  renderCalMain(); renderCalMini();
});
renderCalMain(); renderCalMini();

// Clock click opens calendar window
document.getElementById('clockBtn').addEventListener('click', function(e) {
  e.stopPropagation();
  openApp('win-calendar');
});

// ===== CLOCK =====
function tick() {
  var now = new Date();
  var t = now.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  document.getElementById('topClock').textContent = t;
  document.getElementById('trayBatteryPct').textContent = '--';
}
setInterval(tick, 1000); tick();

// ===== CHAT / AI PANEL =====
function toggleAiPanel() {
  var panel = document.getElementById('aiPanel');
  if (panel.classList.contains('open')) {
    panel.classList.add('closing');
    setTimeout(function() { panel.classList.remove('open', 'closing'); }, 250);
  } else {
    panel.classList.add('open');
    panel.classList.remove('closing');
  }
}
function addAiMessage(text, role, engine) {
  var c = document.getElementById('aiPanelMessages');
  var div = document.createElement('div');
  div.className = 'ai-msg ' + role;
  div.innerHTML = esc(text) + (engine ? '<div class="engine">' + engine + '</div>' : '');
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
}
function sendAiMessage() {
  var input = document.getElementById('aiInput');
  var text = input.value.trim();
  if (!text) return;
  addAiMessage(text, 'user');
  input.value = '';
  socket.emit('chat', { text: text, session_id: sessionId });
  document.getElementById('footEngine').className = 'status-dot';
}
document.getElementById('aiInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') sendAiMessage();
});
socket.on('reply', function(data) {
  addAiMessage(data.text || '...', 'assistant', data.engine || '');
  if (data.session_id) sessionId = data.session_id;
  document.getElementById('footEngine').className = 'status-dot on';
  if (data.text && settings.voice_output) speak(data.text);
});
socket.on('status', function(data) {
  document.getElementById('footEngine').className = data.state === 'thinking' ? 'status-dot' : 'status-dot on';
});
socket.on('permission_request', function(data) {
  if (confirm('Permission: ' + (data.description || 'Allow?'))) {
    socket.emit('permission_grant', { action_id: data.action_id });
  } else {
    socket.emit('permission_deny', { action_id: data.action_id });
  }
});

// ===== VOICE INPUT =====
function toggleMic() { isListening ? stopMic() : startMic(); }
function startMic() {
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    addAiMessage('Speech recognition not supported', 'assistant');
    return;
  }
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';
  recognition.onresult = function(e) {
    var t = e.results[0][0].transcript;
    addAiMessage(t, 'user');
    socket.emit('chat', { text: t, session_id: sessionId });
    stopMic();
  };
  recognition.onerror = function() { stopMic(); };
  recognition.onend = function() { stopMic(); };
  recognition.start();
  isListening = true;
  document.getElementById('micBtn').classList.add('listening');
  document.getElementById('footVoice').className = 'status-dot on';
}
function stopMic() {
  if (recognition) { try{recognition.stop();}catch(e){} recognition=null; }
  isListening = false;
  document.getElementById('micBtn').classList.remove('listening');
  document.getElementById('footVoice').className = 'status-dot';
}

// ===== VOICE OUTPUT =====
function speak(text) {
  if (!('speechSynthesis' in window)) return;
  var u = new SpeechSynthesisUtterance(text);
  u.rate = 1.0;
  speechSynthesis.speak(u);
}

// ===== SCREEN STREAM =====
function startStream() {
  fetch('/api/stream/start',{method:'POST'}).then(function(r){return r.json();}).then(function(d){
    if (d.ok) {
      document.getElementById('streamStartBtn').disabled = true;
      document.getElementById('streamStopBtn').disabled = false;
      document.getElementById('streamAnalyzeBtn').disabled = false;
      document.getElementById('streamStatus').textContent = 'streaming...';
      document.getElementById('footStream').className = 'status-dot on';
      streamInterval = setInterval(fetchFrame, 1000);
    }
  });
}
function stopStream() {
  fetch('/api/stream/stop',{method:'POST'}).then(function(r){return r.json();}).then(function(){
    if (streamInterval) { clearInterval(streamInterval); streamInterval = null; }
    document.getElementById('streamStartBtn').disabled = false;
    document.getElementById('streamStopBtn').disabled = true;
    document.getElementById('streamAnalyzeBtn').disabled = true;
    document.getElementById('streamStatus').textContent = 'stopped';
    document.getElementById('streamPreview').innerHTML = '<span>Stream inactive</span>';
    document.getElementById('footStream').className = 'status-dot';
  });
}
function fetchFrame() {
  fetch('/api/stream/frame').then(function(r){return r.json();}).then(function(d){
    if (d.ok && d.image) {
      document.getElementById('streamPreview').innerHTML = '<img src="data:image/jpeg;base64,'+d.image+'">';
      document.getElementById('streamStatus').textContent = 'streaming - ' + new Date().toLocaleTimeString();
    }
  }).catch(function(){});
}
function analyzeStream() {
  addAiMessage('Analyzing screen...', 'user');
  socket.emit('chat', { text: 'describe what you see on my screen', session_id: sessionId });
}

// ===== NOTES =====
var notes = [];
var activeNoteId = null;

function loadNotes() {
  try { notes = JSON.parse(localStorage.getItem('lavos_notes') || '[]'); } catch(e) { notes = []; }
  if (!notes.length) { createNote(); return; }
  renderNotesSidebar();
  selectNote(notes[0].id);
}
function saveNotes() {
  localStorage.setItem('lavos_notes', JSON.stringify(notes));
}
function createNote() {
  var note = { id: Date.now(), title: 'Untitled', content: '', created: new Date().toISOString() };
  notes.unshift(note);
  saveNotes();
  renderNotesSidebar();
  selectNote(note.id);
}
function deleteNote(id, e) {
  if (e) e.stopPropagation();
  notes = notes.filter(function(n) { return n.id !== id; });
  if (!notes.length) createNote();
  saveNotes();
  renderNotesSidebar();
  if (activeNoteId === id) selectNote(notes[0].id);
}
function selectNote(id) {
  activeNoteId = id;
  var note = notes.find(function(n) { return n.id === id; });
  if (!note) return;
  document.getElementById('notesArea').value = note.content;
  renderNotesSidebar();
}
function renderNotesSidebar() {
  var sidebar = document.getElementById('notesSidebar');
  var search = (document.getElementById('notesSearch').value || '').toLowerCase();
  var filtered = notes.filter(function(n) {
    return !search || n.title.toLowerCase().includes(search) || n.content.toLowerCase().includes(search);
  });
  sidebar.innerHTML = '';
  filtered.forEach(function(n) {
    var div = document.createElement('div');
    div.className = 'note-entry' + (n.id === activeNoteId ? ' active' : '');
    var title = n.title || 'Untitled';
    var preview = n.content.substring(0, 40) || 'Empty note';
    div.innerHTML = '<div class="note-entry-title">' + esc(title) + '</div>'
      + '<div class="note-entry-preview">' + esc(preview) + '</div>'
      + '<button class="note-entry-delete" onclick="deleteNote(' + n.id + ',event)">&#10005;</button>';
    div.onclick = function() { selectNote(n.id); };
    sidebar.appendChild(div);
  });
}
function filterNotes() { renderNotesSidebar(); }
document.getElementById('notesArea').addEventListener('input', function() {
  if (!activeNoteId) return;
  var note = notes.find(function(n) { return n.id === activeNoteId; });
  if (!note) return;
  note.content = this.value;
  var firstLine = this.value.split('\n')[0].substring(0, 30) || 'Untitled';
  note.title = firstLine;
  saveNotes();
  renderNotesSidebar();
});
document.addEventListener('DOMContentLoaded', loadNotes);

// ===== AUDIT =====
function fetchAudit() {
  fetch('/api/audit').then(function(r){return r.json();}).then(function(d){
    if (d.ok && d.data && d.data.entries) renderAudit(d.data.entries);
  }).catch(function(){});
}
function renderAudit(entries) {
  var list = document.getElementById('auditList');
  if (!entries.length) { list.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;">No entries yet</div>'; return; }
  list.innerHTML = '';
  entries.forEach(function(e) {
    var div = document.createElement('div');
    div.className = 'audit-entry';
    var ts = (e.ts||'').substring(0,19).replace('T',' ');
    div.innerHTML = '<span class="ts">'+esc(ts)+'</span>'+esc(e.action)+': '+esc(e.detail);
    list.appendChild(div);
  });
}
function clearAudit() {
  if (confirm('Clear audit log?')) {
    fetch('/api/audit/clear',{method:'POST'}).then(function(){fetchAudit();});
  }
}

// ===== SETTINGS =====
var settingsTabs = {
  general: function() {
    return '<div class="settings-section">General</div>'+
      '<div class="settings-row"><span class="settings-label">OS Version</span><span class="settings-val">LavOS 2026</span></div>'+
      '<div class="settings-row"><span class="settings-label">AI Name</span><input class="gnome-input" id="cfgAiName" value="'+esc(settings.ai_name||'')+'" style="width:140px;"></div>'+
      '<div class="settings-row"><span class="settings-label">Wake Word</span><input class="gnome-input" id="cfgWakeWord" value="'+esc(settings.wake_word||'')+'" style="width:140px;"></div>'+
      '<div class="settings-row"><span class="settings-label">Permissions</span><select class="gnome-select" id="cfgPermissions">'+
        '<option value="always"'+(settings.permissions==='always'?' selected':'')+'>Always Ask</option>'+
        '<option value="never"'+(settings.permissions==='never'?' selected':'')+'>Never Ask</option>'+
      '</select></div>'+
      '<div style="padding:16px 0;"><button class="gnome-btn primary" onclick="saveSettings()">Save</button></div>';
  },
  ai: function() {
    return '<div class="settings-section">Cloud Providers</div>'+
      '<div class="settings-row"><span class="settings-label">Groq API Key</span><input class="gnome-input" id="cfgGroqKey" type="password" value="'+esc(settings.groq_api_key||'')+'" style="width:200px;" placeholder="gsk_..."></div>'+
      '<div class="settings-row"><span class="settings-label">Groq Model</span><input class="gnome-input" id="cfgGroqModel" value="'+esc(settings.groq_model||'')+'" style="width:200px;"></div>'+
      '<div class="settings-row"><span class="settings-label">NIM API Key</span><input class="gnome-input" id="cfgNimKey" type="password" value="'+esc(settings.nim_api_key||'')+'" style="width:200px;" placeholder="nvapi-..."></div>'+
      '<div class="settings-row"><span class="settings-label">NIM Model</span><input class="gnome-input" id="cfgNimModel" value="'+esc(settings.nim_model||'')+'" style="width:200px;"></div>'+
      '<div class="settings-row"><span class="settings-label">Zen API Key</span><input class="gnome-input" id="cfgZenKey" type="password" value="'+esc(settings.zen_api_key||'')+'" style="width:200px;"></div>'+
      '<div class="settings-section">Ollama (Local)</div>'+
      '<div class="settings-row"><span class="settings-label">Ollama Enabled</span><label class="toggle"><input type="checkbox" id="cfgOllamaOn"'+(settings.ollama_enabled?' checked':'')+'><span class="slider"></span></label></div>'+
      '<div class="settings-row"><span class="settings-label">Ollama URL</span><input class="gnome-input" id="cfgOllamaUrl" value="'+esc(settings.ollama_url||'')+'" style="width:200px;" placeholder="http://127.0.0.1:11434"></div>'+
      '<div class="settings-row"><span class="settings-label">Chat Model</span><input class="gnome-input" id="cfgOllamaChat" value="'+esc(settings.ollama_chat_model||'')+'" style="width:140px;" placeholder="qwen3:4b"></div>'+
      '<div class="settings-row"><span class="settings-label">Vision Model</span><input class="gnome-input" id="cfgOllamaVision" value="'+esc(settings.ollama_vision_model||'')+'" style="width:140px;" placeholder="qwen3-vl:4b"></div>'+
      '<div style="padding:16px 0;"><button class="gnome-btn primary" onclick="saveSettings()">Save</button></div>';
  },
  voice: function() {
    return '<div class="settings-section">Voice</div>'+
      '<div class="settings-row"><span class="settings-label">Voice Output</span><label class="toggle"><input type="checkbox" id="cfgVoiceOn"'+(settings.voice_output?' checked':'')+'><span class="slider"></span></label></div>'+
      '<div class="settings-row"><span class="settings-label">Voice Engine</span><select class="gnome-select" id="cfgVoiceEngine">'+
        '<option value="browser"'+(settings.voice_engine==='browser'?' selected':'')+'>Browser TTS</option>'+
        '<option value="pyttsx3"'+(settings.voice_engine==='pyttsx3'?' selected':'')+'>pyttsx3</option>'+
        '<option value="off"'+(settings.voice_engine==='off'?' selected':'')+'>Off</option>'+
      '</select></div>'+
      '<div style="padding:16px 0;"><button class="gnome-btn primary" onclick="saveSettings()">Save</button></div>';
  },
  screen: function() {
    return '<div class="settings-section">Screen Capture</div>'+
      '<div class="settings-row"><span class="settings-label">Screen Capture</span><label class="toggle"><input type="checkbox" id="cfgStreamOn"'+(settings.stream_enabled?' checked':'')+'><span class="slider"></span></label></div>'+
      '<div class="settings-row"><span class="settings-label">Capture FPS</span><select class="gnome-select" id="cfgStreamFps">'+
        '<option value="1"'+(settings.stream_fps===1?' selected':'')+'>1 fps</option>'+
        '<option value="2"'+(settings.stream_fps===2?' selected':'')+'>2 fps</option>'+
        '<option value="5"'+(settings.stream_fps===5?' selected':'')+'>5 fps</option>'+
      '</select></div>'+
      '<div style="padding:16px 0;"><button class="gnome-btn primary" onclick="saveSettings()">Save</button></div>';
  },
  appearance: function() {
    return '<div class="settings-section">Appearance</div>'+
      '<div class="settings-row"><span class="settings-label">Theme</span><span class="settings-val">Dark</span></div>'+
      '<div class="settings-row"><span class="settings-label">Accent Color</span><span class="settings-val" style="color:var(--accent);">Blue</span></div>'+
      '<div class="settings-row"><span class="settings-label">Font</span><span class="settings-val">Inter / Cantarell</span></div>';
  },
  privacy: function() {
    return '<div class="settings-section">Privacy</div>'+
      '<div class="settings-row"><span class="settings-label">Screenshots</span><span class="settings-val">Auto-deleted after reading</span></div>'+
      '<div class="settings-row"><span class="settings-label">Data Storage</span><span class="settings-val">Local only</span></div>'+
      '<div class="settings-row"><span class="settings-label">API Keys</span><span class="settings-val">Stored locally in .env</span></div>';
  },
  network: function() {
    return '<div class="settings-section">Network</div>'+
      '<div class="settings-row"><span class="settings-label">Status</span><span class="settings-val" style="color:var(--green);">Connected</span></div>'+
      '<div class="settings-row"><span class="settings-label">Brain URL</span><span class="settings-val">http://127.0.0.1:8080</span></div>';
  },
  power: function() {
    return '<div class="settings-section">Power</div>'+
      '<div class="settings-row"><span class="settings-label">Battery</span><span class="settings-val" id="settingsBattery">--</span></div>'+
      '<div class="settings-row"><span class="settings-label">Uptime</span><span class="settings-val" id="settingsUptime">--</span></div>';
  },
  about: function() {
    return '<div class="settings-section">About</div>'+
      '<div class="settings-row"><span class="settings-label">OS</span><span class="settings-val">LavOS 2026</span></div>'+
      '<div class="settings-row"><span class="settings-label">Engine</span><span class="settings-val">Cloud-first (Groq / NIM / Zen)</span></div>'+
      '<div class="settings-row"><span class="settings-label">GitHub</span><span class="settings-val" style="color:var(--accent);">Lavish09-Mehra/LaOS-AI</span></div>';
  }
};
function switchSettingsTab(tab, el) {
  document.querySelectorAll('.settings-nav').forEach(function(n){n.classList.remove('active');});
  if (el) el.classList.add('active');
  var content = document.getElementById('settingsContent');
  content.innerHTML = settingsTabs[tab] ? settingsTabs[tab]() : '';
}
function loadSettings() {
  fetch('/api/settings').then(function(r){return r.json();}).then(function(d){
    if (d.ok && d.data) {
      settings = d.data;
      if (settings.ai_name) document.getElementById('aiPanelTitle').textContent = settings.ai_name;
      switchSettingsTab('general', document.querySelector('.settings-nav[data-tab="general"]'));
    }
  }).catch(function(){});
}
function saveSettings() {
  var s = {};
  var aiName = document.getElementById('cfgAiName');
  var wakeWord = document.getElementById('cfgWakeWord');
  var groqKey = document.getElementById('cfgGroqKey');
  var groqModel = document.getElementById('cfgGroqModel');
  var nimKey = document.getElementById('cfgNimKey');
  var nimModel = document.getElementById('cfgNimModel');
  var zenKey = document.getElementById('cfgZenKey');
  var ollamaOn = document.getElementById('cfgOllamaOn');
  var ollamaUrl = document.getElementById('cfgOllamaUrl');
  var ollamaChat = document.getElementById('cfgOllamaChat');
  var ollamaVision = document.getElementById('cfgOllamaVision');
  var voiceOn = document.getElementById('cfgVoiceOn');
  var voiceEngine = document.getElementById('cfgVoiceEngine');
  var streamOn = document.getElementById('cfgStreamOn');
  var streamFps = document.getElementById('cfgStreamFps');
  var perms = document.getElementById('cfgPermissions');
  if (aiName) s.ai_name = aiName.value.trim();
  if (wakeWord) s.wake_word = wakeWord.value.trim();
  if (groqKey) s.groq_api_key = groqKey.value.trim();
  if (groqModel) s.groq_model = groqModel.value.trim();
  if (nimKey) s.nim_api_key = nimKey.value.trim();
  if (nimModel) s.nim_model = nimModel.value.trim();
  if (zenKey) s.zen_api_key = zenKey.value.trim();
  if (ollamaOn) s.ollama_enabled = ollamaOn.checked;
  if (ollamaUrl) s.ollama_url = ollamaUrl.value.trim();
  if (ollamaChat) s.ollama_chat_model = ollamaChat.value.trim();
  if (ollamaVision) s.ollama_vision_model = ollamaVision.value.trim();
  if (voiceOn) s.voice_output = voiceOn.checked;
  if (voiceEngine) s.voice_engine = voiceEngine.value;
  if (streamOn) s.stream_enabled = streamOn.checked;
  if (streamFps) s.stream_fps = parseInt(streamFps.value)||1;
  if (perms) s.permissions = perms.value;
  fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(s)})
  .then(function(){ settings=Object.assign(settings,s); if(s.ai_name) document.getElementById('aiPanelTitle').textContent=s.ai_name; });
}
function screenLock() {}

// ===== UTILITIES =====
function esc(str) { var d=document.createElement('div'); d.textContent=str; return d.innerHTML; }

// ===== TERMINAL =====
var termHistory = [];
var termHistIdx = -1;
var termDirs = [];
var termBuf = '';
var termReady = true;

function termFocus() {
  document.getElementById('termInput').focus();
}

function termBoot() {
  var out = document.getElementById('termOutput');
  var lines = [
    { text: '', cls: '' },
    { text: '  ██████╗      ██╗      ██████╗  ██████╗██╗  ██╗', cls: 'term-purple' },
    { text: '  ██╔══██╗     ██║     ██╔═══██╗██╔════╝██║ ██╔╝', cls: 'term-purple' },
    { text: '  ██║  ██║     ██║     ██║   ██║██║     █████╔╝ ', cls: 'term-purple' },
    { text: '  ██║  ██║     ██║     ██║   ██║██║     ██╔═██╗ ', cls: 'term-purple' },
    { text: '  ██████╔╝     ███████╗╚██████╔╝╚██████╗██║  ██╗', cls: 'term-purple' },
    { text: '  ╚═════╝      ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝', cls: 'term-purple' },
    { text: '', cls: '' },
    { text: '  LavOS 2026 — Built from scratch', cls: 'term-dim' },
    { text: '  kernel: lavos-kernel  |  engine: cloud-first', cls: 'term-dim' },
    { text: '  type "help" for available commands', cls: 'term-dim' },
    { text: '', cls: '' }
  ];
  lines.forEach(function(l) {
    var div = document.createElement('div');
    div.className = 'term-output-line ' + (l.cls || '');
    div.textContent = l.text;
    out.appendChild(div);
  });
}

function termPrint(text, cls) {
  var out = document.getElementById('termOutput');
  var div = document.createElement('div');
  div.className = 'term-output-line ' + (cls || '');
  div.textContent = text;
  out.appendChild(div);
  termScroll();
}

function termPrintHtml(html) {
  var out = document.getElementById('termOutput');
  var div = document.createElement('div');
  div.className = 'term-output-line';
  div.innerHTML = html;
  out.appendChild(div);
  termScroll();
}

function termScroll() {
  var body = document.getElementById('termBody');
  body.scrollTop = body.scrollHeight;
}

function termExec(cmd) {
  if (!cmd.trim()) return;
  var promptHtml = '<span class="term-prompt">user@lavos<span class="term-dim">:</span><span class="term-blue">~</span>$ </span>' + esc(cmd);
  termPrintHtml(promptHtml);
  termHistory.push(cmd);
  termHistIdx = termHistory.length;

  var parts = cmd.trim().split(/\s+/);
  var bin = parts[0].toLowerCase();
  var args = parts.slice(1);

  switch (bin) {
    case 'help':
      termPrint('Available commands:', 'term-cyan');
      termPrint('  help              Show this help message', 'term-dim');
      termPrint('  clear / cls       Clear terminal', 'term-dim');
      termPrint('  echo [text]       Print text', 'term-dim');
      termPrint('  mkdir [name]      Create a directory', 'term-dim');
      termPrint('  date              Show current date/time', 'term-dim');
      termPrint('  whoami            Show current user', 'term-dim');
      termPrint('  hostname          Show hostname', 'term-dim');
      termPrint('  uname             Show OS info', 'term-dim');
      termPrint('  uptime            Show system uptime', 'term-dim');
      termPrint('  free / memory     Show RAM usage', 'term-dim');
      termPrint('  battery           Show battery status', 'term-dim');
      termPrint('  ls                List files', 'term-dim');
      termPrint('  cat [file]        Show file contents', 'term-dim');
      termPrint('  pwd               Print working directory', 'term-dim');
      termPrint('  neofetch          System info with ASCII art', 'term-dim');
      termPrint('  cowsay [text]     Cow says...', 'term-dim');
      termPrint('  matrix            Enter the Matrix', 'term-dim');
      termPrint('  ai [text]         Talk to AI assistant', 'term-dim');
      termPrint('  open [app]        Open an application', 'term-dim');
      termPrint('  reboot            Reboot system', 'term-dim');
      termPrint('  shutdown          Shutdown system', 'term-dim');
      break;

    case 'clear': case 'cls':
      document.getElementById('termOutput').innerHTML = '';
      break;

    // echo: prints arguments to terminal output
    case 'echo':
      termPrint(args.join(' '));
      break;

    // mkdir: creates a virtual directory in session storage
    case 'mkdir':
      if (!args[0]) { termPrint('mkdir: missing operand', 'term-red'); break; }
      termDirs.push(args[0]);
      termPrint('Directory created: ' + args[0], 'term-green');
      break;

    case 'date':
      termPrint(new Date().toString());
      break;

    case 'whoami':
      termPrint('user');
      break;

    case 'hostname':
      termPrint('lavos');
      break;

    case 'uname':
      if (args.includes('-a')) {
        termPrint('LavOS 2026 lavos 1.0.0 x86_64 Windows');
      } else {
        termPrint('LavOS');
      }
      break;

    case 'uptime':
      fetch('/api/status').then(function(r){return r.json();}).then(function(d){
        termPrint('up ' + (d.uptime || 'unknown') + ', ' + (d.ram || ''));
      }).catch(function(){ termPrint('uptime unavailable', 'term-red'); });
      break;

    case 'free': case 'memory': case 'mem':
      fetch('/api/status').then(function(r){return r.json();}).then(function(d){
        termPrint('RAM: ' + (d.ram || 'unknown'));
      }).catch(function(){ termPrint('memory unavailable', 'term-red'); });
      break;

    case 'battery': case 'batt':
      fetch('/api/status').then(function(r){return r.json();}).then(function(d){
        termPrint('Battery: ' + (d.battery || 'unknown'));
      }).catch(function(){ termPrint('battery unavailable', 'term-red'); });
      break;

    case 'ls':
      termPrint('Documents/  Downloads/  Projects/  .config/', 'term-blue');
      termPrint('README.md  notes.txt  .env  storage/', 'term-dim');
      break;

    case 'cat':
      if (!args[0]) { termPrint('cat: missing operand', 'term-red'); break; }
      if (args[0] === 'README.md') {
        termPrint('# LavOS 2026', 'term-green');
        termPrint('A desktop AI assistant built from scratch.', 'term-dim');
        termPrint('GitHub: Lavish09-Mehra/LaOS-AI', 'term-dim');
      } else if (args[0] === '.env') {
        termPrint('cat: .env: Permission denied', 'term-red');
      } else {
        termPrint('cat: ' + args[0] + ': No such file', 'term-red');
      }
      break;

    case 'pwd':
      termPrint('/home/user');
      break;

    case 'neofetch':
      var nf = [
        '       LavOS       user@lavos',
        '      _____        ----------',
        '     /     \\       OS: LavOS 2026',
        '    / () () \\      Kernel: lavos-kernel',
        '   |  ___  |      Engine: cloud-first',
        '   | |   | |       Shell: lavos-term',
        '   |_|   |_|       Terminal: LavOS Terminal',
        '   /       \\       Theme: Tokyo Night',
        '  / /   \\ \\ \\      CPU: AMD Ryzen 7 PRO 5850U',
        ' /_/     \\_\\_\\     RAM: 15.3 GB',
        '                     Uptime: loading...',
      ];
      nf.forEach(function(l, i) {
        termPrint(l, i < 8 ? 'term-purple' : 'term-dim');
      });
      break;

    case 'cowsay':
      var msg = args.join(' ') || 'moo';
      var border = '-'.repeat(msg.length + 2);
      termPrint(' ' + border);
      termPrint('< ' + msg + ' >');
      termPrint(' ' + border);
      termPrint('        \\   ^__^');
      termPrint('         \\  (oo)\\_______');
      termPrint('            (__)\\       )\\/\\');
      termPrint('                ||----w |');
      termPrint('                ||     ||');
      break;

    case 'matrix':
      termPrint('Wake up, user...', 'term-green');
      termPrint('The Matrix has you...', 'term-green');
      termPrint('Follow the white rabbit.', 'term-green');
      break;

    case 'ai':
      if (!args.length) { termPrint('Usage: ai <message>', 'term-yellow'); break; }
      var msg = args.join(' ');
      termPrint('Thinking...', 'term-dim');
      socket.emit('chat', { text: msg, session_id: sessionId });
      break;

    case 'open':
      if (!args[0]) { termPrint('Usage: open <app>', 'term-yellow'); break; }
      var appMap = { terminal: 'win-terminal', files: 'win-files', browser: 'win-browser', settings: 'win-settings', todos: 'win-todos', audit: 'win-audit', stream: 'win-stream' };
      var winId = appMap[args[0].toLowerCase()];
      if (winId) { openApp(winId); termPrint('Opened ' + args[0]); }
      else { termPrint('open: unknown app "' + args[0] + '"', 'term-red'); }
      break;

    case 'reboot':
      termPrint('Rebooting...', 'term-yellow');
      setTimeout(function() { location.reload(); }, 1500);
      break;

    case 'shutdown':
      termPrint('Shutting down...', 'term-red');
      setTimeout(function() { document.body.style.opacity = '0'; }, 500);
      break;

    case 'sudo':
      termPrint('user is not in the sudoers file. This incident will be reported.', 'term-red');
      break;

    case 'rm':
      if (args.includes('-rf') && args.includes('/')) {
        termPrint('Nice try. Nice try.', 'term-red');
      } else {
        termPrint('rm: operation not permitted in demo mode', 'term-yellow');
      }
      break;

    case 'exit':
      closeApp('win-terminal');
      break;

    case 'tree':
      termPrint('.', 'term-blue');
      termPrint('├── Documents/', 'term-blue');
      termPrint('├── Downloads/', 'term-blue');
      termPrint('├── Projects/', 'term-blue');
      termPrint('│   └── LaOS-AI/', 'term-blue');
      termPrint('├── .config/', 'term-blue');
      termPrint('├── README.md', 'term-dim');
      termPrint('└── .env', 'term-dim');
      break;

    default:
      termPrint('bash: ' + bin + ': command not found. Type "help" for available commands.', 'term-red');
  }
  termScroll();
}

// Terminal input handling
document.addEventListener('DOMContentLoaded', function() {
  var termInput = document.getElementById('termInput');
  var termDisplay = document.getElementById('termDisplay');
  if (!termInput) return;

  termInput.addEventListener('input', function() {
    termDisplay.textContent = termInput.value;
  });

  termInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      var cmd = termInput.value;
      termInput.value = '';
      termDisplay.textContent = '';
      termExec(cmd);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (termHistIdx > 0) {
        termHistIdx--;
        termInput.value = termHistory[termHistIdx];
        termDisplay.textContent = termInput.value;
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (termHistIdx < termHistory.length - 1) {
        termHistIdx++;
        termInput.value = termHistory[termHistIdx];
        termDisplay.textContent = termInput.value;
      } else {
        termHistIdx = termHistory.length;
        termInput.value = '';
        termDisplay.textContent = '';
      }
    } else if (e.key === 'l' && e.ctrlKey) {
      e.preventDefault();
      document.getElementById('termOutput').innerHTML = '';
    } else if (e.key === 'c' && e.ctrlKey) {
      e.preventDefault();
      termPrintHtml('<span class="term-prompt">user@lavos<span class="term-dim">:</span><span class="term-blue">~</span>$ </span>' + esc(termInput.value) + '^C');
      termInput.value = '';
      termDisplay.textContent = '';
    } else if (e.key === 'a' && e.ctrlKey) {
      e.preventDefault();
      termInput.setSelectionRange(0, 0);
    } else if (e.key === 'e' && e.ctrlKey) {
      e.preventDefault();
      termInput.setSelectionRange(termInput.value.length, termInput.value.length);
    }
  });

  // Auto-focus terminal when opened
  var origOpenApp = openApp;
  window.openApp = function(id) {
    origOpenApp(id);
    if (id === 'win-terminal') {
      setTimeout(function() { termFocus(); }, 100);
    }
  };

  termBoot();
  setTimeout(termFocus, 200);
});

// ===== INIT =====
loadSettings();
loadNotes();
fetchAudit();
