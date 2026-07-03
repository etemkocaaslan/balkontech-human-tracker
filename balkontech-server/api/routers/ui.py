from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI"])

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Balkontech Human Tracker</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0a0a;--bg2:#111;--bg3:#161616;--bg4:#1c1c1c;
  --border:#222;--border2:#2a2a2a;
  --text:#e0e0e0;--muted:#666;--dim:#333;
  --green:#22c55e;--amber:#f59e0b;--red:#ef4444;--blue:#3b82f6;
}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
     display:flex;flex-direction:column;height:100vh;overflow:hidden;font-size:13px}

/* ── Header ── */
header{background:var(--bg2);border-bottom:1px solid var(--border);
       padding:0 20px;display:flex;align-items:center;gap:0;flex-shrink:0;height:44px}
.logo{font-size:.9rem;font-weight:700;color:#fff;margin-right:24px;letter-spacing:.03em}
.logo span{color:var(--green)}
nav{display:flex;height:100%}
.tab{padding:0 18px;border:none;background:none;color:var(--muted);font-size:.78rem;
     font-weight:600;cursor:pointer;border-bottom:2px solid transparent;
     transition:color .15s,border-color .15s;letter-spacing:.04em;text-transform:uppercase}
.tab:hover{color:var(--text)}
.tab.active{color:var(--green);border-bottom-color:var(--green)}
.hbadge{margin-left:auto;font-size:.65rem;padding:2px 10px;border-radius:4px;
        background:var(--bg4);border:1px solid var(--border2);color:var(--muted)}
.hbadge.live{border-color:var(--green);color:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.45}}

/* ── Layout ── */
main{display:flex;flex:1;overflow:hidden}
.pane{display:flex;flex:1;overflow:hidden}
.pane.hidden{display:none}

/* ── Sidebar ── */
.sidebar{width:272px;background:var(--bg2);border-right:1px solid var(--border);
         display:flex;flex-direction:column;overflow-y:auto;flex-shrink:0}
.sb{padding:14px 14px;border-bottom:1px solid var(--border)}
.sb h2{font-size:.6rem;text-transform:uppercase;letter-spacing:.12em;color:var(--dim);margin-bottom:10px}

/* ── Right rail ── */
.rail{width:252px;background:var(--bg2);border-left:1px solid var(--border);
      display:flex;flex-direction:column;overflow-y:auto;flex-shrink:0}

/* ── Center ── */
.center{flex:1;display:flex;flex-direction:column;background:#000;overflow:hidden}
#stream-img{flex:1;object-fit:contain;width:100%;display:none}
.placeholder{flex:1;display:flex;flex-direction:column;align-items:center;
             justify-content:center;color:var(--dim);gap:8px}
.placeholder svg{opacity:.25;width:56px;height:56px}
.placeholder p{font-size:.8rem}

/* ── Forms ── */
label{display:block;font-size:.7rem;color:var(--muted);margin-bottom:3px;margin-top:8px}
label:first-child{margin-top:0}
input,select{width:100%;background:var(--bg4);border:1px solid var(--border2);
             border-radius:6px;color:var(--text);padding:7px 9px;
             font-size:.78rem;outline:none;transition:border-color .15s}
input:focus,select:focus{border-color:#444}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px}

/* ── Buttons ── */
.btn{display:block;width:100%;padding:8px;border:1px solid var(--border2);
     border-radius:6px;font-size:.78rem;font-weight:600;cursor:pointer;
     background:var(--bg4);color:#aaa;transition:background .15s;text-align:center}
.btn:hover{background:#222}
.btn.primary{background:var(--green);color:#000;border-color:var(--green)}
.btn.primary:hover{background:#16a34a}
.btn.danger{color:var(--red);border-color:var(--border2)}.btn.danger:hover{background:#2a1111;border-color:var(--red)}
.btn.sm{padding:5px 10px;font-size:.72rem;width:auto}
.btn-row{display:flex;gap:6px;margin-top:8px}

/* ── Session list ── */
.session-list{list-style:none}
.session-item{display:flex;align-items:center;gap:7px;padding:7px 9px;
              border-radius:6px;cursor:pointer;margin-bottom:3px;
              border:1px solid transparent;transition:background .1s}
.session-item:hover{background:var(--bg4)}
.session-item.active{background:#1a2e1a;border-color:#22c55e33}
.sdot{width:7px;height:7px;border-radius:50%;background:var(--green);flex-shrink:0}
.sid{font-family:monospace;font-size:.78rem;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sdel{background:none;border:none;color:var(--dim);cursor:pointer;font-size:.9rem;padding:0 2px}
.sdel:hover{color:var(--red)}
.empty{color:var(--dim);font-size:.75rem;padding:4px 0}

/* ── Stats ── */
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px}
.stat-card{background:var(--bg4);border:1px solid var(--border2);border-radius:7px;
           padding:9px;text-align:center}
.stat-card .v{font-size:1.5rem;font-weight:700;color:var(--green)}
.stat-card .l{font-size:.58rem;color:var(--muted);text-transform:uppercase;margin-top:1px}

/* ── Zone status ── */
.zone-list{list-style:none}
.zitem{display:flex;justify-content:space-between;align-items:center;
       padding:7px 9px;background:var(--bg4);border:1px solid var(--border2);
       border-radius:6px;margin-bottom:5px;transition:border-color .3s}
.zitem.on{border-color:#22c55e44;background:#1a2e1a}
.zname{display:flex;align-items:center;gap:6px;font-weight:600;font-size:.78rem}
.zdot{width:8px;height:8px;border-radius:50%;background:var(--dim);flex-shrink:0}
.zdot.on{background:var(--green);box-shadow:0 0 5px #22c55e88}
.zwho{font-size:.65rem;color:var(--muted);margin-top:2px;padding-left:14px}
.zcount{font-size:.7rem;font-weight:700;background:var(--bg);border:1px solid var(--border2);
        border-radius:10px;padding:1px 8px;color:var(--muted)}
.zcount.on{background:#22c55e22;border-color:#22c55e55;color:var(--green)}

/* ── Models ── */
.model-grid{display:flex;flex-direction:column;gap:6px}
.model-card{background:var(--bg4);border:1px solid var(--border2);border-radius:8px;
            padding:10px 12px;display:flex;align-items:center;gap:10px}
.model-icon{width:32px;height:32px;border-radius:6px;background:var(--bg3);
            border:1px solid var(--border);display:flex;align-items:center;
            justify-content:center;font-size:.75rem;color:var(--muted);flex-shrink:0}
.model-name{font-size:.82rem;font-weight:600}
.model-type{font-size:.65rem;color:var(--muted);margin-top:1px}

/* ── Misc ── */
.msg{font-size:.7rem;padding:5px 8px;border-radius:5px;margin-top:6px}
.msg.ok{background:#1a2e1a;color:var(--green)}
.msg.err{background:#2a1111;color:var(--red)}
.msg.info{background:var(--bg4);color:var(--muted)}
.separator{height:1px;background:var(--border);margin:12px 0}
#sbar{padding:8px 14px;font-size:.67rem;color:var(--dim);
      border-top:1px solid var(--border);margin-top:auto}
</style>
</head>
<body>

<!-- Header -->
<header>
  <div class="logo">Balkon<span>tech</span></div>
  <nav>
    <button class="tab active" onclick="switchTab('stream')">▶ Stream</button>
    <button class="tab" onclick="switchTab('zones')">⬡ Zone Editor</button>
    <button class="tab" onclick="switchTab('models')">⚙ Models</button>
    <button class="tab" onclick="switchTab('keys')">🔑 API Keys</button>
  </nav>
  <span class="hbadge" id="live-badge">IDLE</span>
</header>

<main>

<!-- ══════════ STREAM TAB ══════════ -->
<div class="pane" id="tab-stream">

  <!-- Left: session management -->
  <aside class="sidebar">

    <div class="sb">
      <h2>Active Sessions</h2>
      <ul class="session-list" id="session-list"><li class="empty">No sessions</li></ul>
      <button class="btn sm" style="margin-top:8px" onclick="refreshSessions()">↻ Refresh</button>
    </div>

    <div class="sb" style="flex:1">
      <h2>Create Session</h2>

      <label>Video path</label>
      <input id="c-video" placeholder="out_1917_1080.mp4"/>

      <label>Video ID <span style="color:var(--dim)">(for zones)</span></label>
      <input id="c-videoid" placeholder="auto from filename"/>

      <label>Detector model</label>
      <select id="c-model"><option value="yolov8n.pt">yolov8n.pt</option></select>

      <div class="row2">
        <div>
          <label>Conf threshold</label>
          <input id="c-conf" type="number" value="0.25" step="0.05" min="0.05" max="0.95"/>
        </div>
        <div>
          <label>NMS IoU</label>
          <input id="c-nms" type="number" value="0.45" step="0.05" min="0.1" max="0.9"/>
        </div>
      </div>

      <div class="row2">
        <div>
          <label>Img size</label>
          <select id="c-imgsz">
            <option value="320">320</option>
            <option value="416">416</option>
            <option value="640" selected>640</option>
            <option value="1280">1280</option>
          </select>
        </div>
        <div>
          <label>Device</label>
          <select id="c-device">
            <option value="cpu" selected>CPU</option>
            <option value="0">GPU 0</option>
            <option value="1">GPU 1</option>
          </select>
        </div>
      </div>

      <label>Target classes <span style="color:var(--dim)">(comma-sep, 0=person)</span></label>
      <input id="c-classes" value="0"/>

      <div class="row2">
        <div>
          <label>Track buffer</label>
          <input id="c-tbuf" type="number" value="90" min="10"/>
        </div>
        <div>
          <label>Match thresh</label>
          <input id="c-match" type="number" value="0.85" step="0.05" min="0.1" max="1"/>
        </div>
      </div>

      <div id="create-msg"></div>
      <div class="btn-row">
        <button class="btn primary" onclick="createSession()" style="flex:1">+ Create Session</button>
      </div>
    </div>

    <div id="sbar">Ready</div>
  </aside>

  <!-- Center: MJPEG stream -->
  <div class="center">
    <img id="stream-img" alt="stream"/>
    <div class="placeholder" id="placeholder">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
        <rect x="2" y="6" width="20" height="14" rx="2"/>
        <path d="M9 10l6 4-6 4V10z"/>
      </svg>
      <p>Select a session to start streaming</p>
    </div>
  </div>

  <!-- Right: stats + zone status -->
  <aside class="rail">

    <div class="sb">
      <h2>Live Stats</h2>
      <div class="stat-grid">
        <div class="stat-card"><div class="v" id="s-tracks">—</div><div class="l">Tracks</div></div>
        <div class="stat-card"><div class="v" id="s-frame">—</div><div class="l">Frame</div></div>
      </div>
      <button class="btn danger" id="stop-btn" onclick="stopStream()" style="display:none">■ Stop</button>
    </div>

    <div class="sb" style="flex:1">
      <h2>Zone Status</h2>
      <ul class="zone-list" id="zone-status"><li class="empty">No data</li></ul>
    </div>

  </aside>
</div><!-- /tab-stream -->


<!-- ══════════ ZONE EDITOR TAB ══════════ -->
<div class="pane hidden" id="tab-zones" style="flex:1;overflow:hidden">
  <iframe src="/zone-editor" style="width:100%;height:100%;border:none;display:block"></iframe>
</div><!-- /tab-zones -->


<!-- ══════════ MODELS TAB ══════════ -->
<div class="pane hidden" id="tab-models">
  <div style="padding:24px;flex:1;overflow-y:auto;max-width:640px">
    <h2 style="font-size:.65rem;text-transform:uppercase;letter-spacing:.12em;color:var(--dim);margin-bottom:14px">Available Models</h2>
    <div class="model-grid" id="model-grid">
      <div class="empty">Loading…</div>
    </div>
    <div class="btn-row" style="margin-top:16px">
      <button class="btn sm" onclick="loadModels()">↻ Refresh</button>
    </div>
  </div>
</div>

<!-- ══════════ API KEYS TAB ══════════ -->
<div class="pane hidden" id="tab-keys">
  <div style="padding:24px;flex:1;overflow-y:auto;max-width:640px">
    <h2 style="font-size:.65rem;text-transform:uppercase;letter-spacing:.12em;color:var(--dim);margin-bottom:4px">API Keys</h2>
    <p style="font-size:.72rem;color:var(--muted);margin-bottom:16px">Keys are required by the desktop client to access <code style="font-size:.68rem;background:#1a1a1a;padding:1px 5px;border-radius:3px">/api/v1/*</code> endpoints. The raw key is shown only once on creation.</p>

    <div style="display:flex;gap:8px;margin-bottom:16px">
      <input id="key-name" placeholder="Key name (e.g. balkontech-client)" style="flex:1"/>
      <button class="btn primary sm" onclick="createKey()" style="white-space:nowrap">+ Create Key</button>
    </div>
    <div id="key-create-msg"></div>

    <!-- New key reveal box -->
    <div id="key-reveal" style="display:none;margin-bottom:16px;background:#1a2e1a;border:1px solid #22c55e44;border-radius:8px;padding:14px">
      <div style="font-size:.68rem;color:var(--green);font-weight:700;margin-bottom:6px">⚠ Copy this key now — it will not be shown again</div>
      <div style="display:flex;gap:8px;align-items:center">
        <code id="key-raw" style="flex:1;font-size:.75rem;background:#111;padding:8px 10px;border-radius:6px;word-break:break-all;color:#e0e0e0;border:1px solid #333"></code>
        <button class="btn sm" onclick="copyKey()" style="white-space:nowrap;flex-shrink:0">Copy</button>
      </div>
    </div>

    <div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.1em;color:var(--dim);margin-bottom:8px">Active Keys</div>
    <div id="key-list" style="display:flex;flex-direction:column;gap:6px">
      <div class="empty">Loading…</div>
    </div>
    <button class="btn sm" onclick="loadKeys()" style="margin-top:12px">↻ Refresh</button>
  </div>
</div>

</main><!-- /main -->

<script>
// ═══════════════════════════════════════════════════════════
// TAB SWITCHING
// ═══════════════════════════════════════════════════════════
function switchTab(name) {
  ['stream','zones','models','keys'].forEach(t => {
    document.getElementById('tab-'+t).classList.toggle('hidden', t !== name);
  });
  document.querySelectorAll('.tab').forEach((b,i) => {
    b.classList.toggle('active', ['stream','zones','models','keys'][i] === name);
  });
  if (name === 'models') loadModels();
  if (name === 'keys')   loadKeys();
  if (name === 'zones' && zeImg) { setTimeout(zeResizeCanvas,50); zeDrawAll(); }
}

// ═══════════════════════════════════════════════════════════
// STREAM TAB
// ═══════════════════════════════════════════════════════════
let activeSession = null;
let statsInterval = null;
const ZONE_COLORS = ['#3b89eb','#f59e2d','#e451b4','#4cb35b','#b4b604','#5050c8'];

async function refreshSessions() {
  const res  = await fetch('/sessions').catch(()=>null);
  if (!res || !res.ok) return;
  const ids  = await res.json();
  const list = document.getElementById('session-list');
  if (!ids.length) { list.innerHTML='<li class="empty">No sessions</li>'; return; }
  list.innerHTML = ids.map(id => `
    <li class="session-item ${id===activeSession?'active':''}" onclick="selectSession('${id}')">
      <span class="sdot"></span>
      <span class="sid" title="${id}">${id.slice(0,8)}…</span>
      <button class="sdel" onclick="event.stopPropagation();deleteSession('${id}')" title="Delete">✕</button>
    </li>`).join('');
}

async function createSession() {
  const videoPath = document.getElementById('c-video').value.trim();
  const videoIdRaw = document.getElementById('c-videoid').value.trim();
  const classes   = document.getElementById('c-classes').value.split(',').map(s=>parseInt(s.trim())).filter(n=>!isNaN(n));
  const body = {
    detector_model:    document.getElementById('c-model').value,
    tracker_type:      'bytetrack',
    conf_threshold:    parseFloat(document.getElementById('c-conf').value),
    nms_iou_threshold: parseFloat(document.getElementById('c-nms').value),
    imgsz:             parseInt(document.getElementById('c-imgsz').value),
    device:            document.getElementById('c-device').value,
    target_classes:    classes.length ? classes : [0],
    tracker_params: {
      track_buffer: parseInt(document.getElementById('c-tbuf').value),
      match_thresh: parseFloat(document.getElementById('c-match').value),
      max_age: 90, track_thresh: 0.35, min_conf: 0.1, iou_threshold: 0.3, min_hits: 1
    }
  };
  setMsg('create-msg','Creating…','info');
  const res = await fetch('/sessions', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).catch(()=>null);
  if (!res) { setMsg('create-msg','Network error','err'); return; }
  const data = await res.json();
  if (!res.ok) { setMsg('create-msg', data.detail||'Error','err'); return; }
  setMsg('create-msg',`Created: ${data.session_id.slice(0,8)}…`,'ok');

  // Store video association for zone overlay
  const vid = videoIdRaw || videoPath.split(/[\\/]/).pop().replace(/\.[^.]+$/,'');
  sessionVideoMap[data.session_id] = { videoPath, videoId: vid };

  await refreshSessions();
  selectSession(data.session_id);
}

const sessionVideoMap = {};  // {session_id: {videoPath, videoId}}

function selectSession(id) {
  if (activeSession === id) return;
  stopStream(false);
  activeSession = id;

  const img = document.getElementById('stream-img');
  img.src = `/sessions/${id}/stream`;
  img.style.display = 'block';
  document.getElementById('placeholder').style.display = 'none';
  document.getElementById('stop-btn').style.display = 'block';
  document.getElementById('live-badge').textContent = 'LIVE';
  document.getElementById('live-badge').className = 'hbadge live';

  refreshSessions();
  statsInterval = setInterval(()=>fetchStats(id), 1000);
  setStatus(`Streaming ${id.slice(0,8)}…`);
}

function stopStream(doRefresh=true) {
  if (!activeSession) return;
  const img = document.getElementById('stream-img');
  img.src=''; img.style.display='none';
  document.getElementById('placeholder').style.display='flex';
  document.getElementById('stop-btn').style.display='none';
  document.getElementById('live-badge').textContent='IDLE';
  document.getElementById('live-badge').className='hbadge';
  clearInterval(statsInterval); statsInterval=null;
  document.getElementById('s-tracks').textContent='—';
  document.getElementById('s-frame').textContent='—';
  document.getElementById('zone-status').innerHTML='<li class="empty">No data</li>';
  activeSession=null;
  if (doRefresh) refreshSessions();
  setStatus('Ready');
}

async function deleteSession(id) {
  if (!confirm('Delete session '+id.slice(0,8)+'?')) return;
  if (id===activeSession) stopStream(false);
  await fetch('/sessions/'+id, {method:'DELETE'});
  refreshSessions();
}

async function fetchStats(id) {
  const res = await fetch(`/sessions/${id}/stats`).catch(()=>null);
  if (!res) return;
  if (res.status===404) { stopStream(); setStatus('Session ended'); return; }
  const d = await res.json();
  document.getElementById('s-tracks').textContent = d.track_count ?? '—';
  document.getElementById('s-frame').textContent  = d.frame_index ?? '—';
  renderZoneStatus(d.zone_occupancy ?? {});
}

function renderZoneStatus(occ) {
  const ul = document.getElementById('zone-status');
  const entries = Object.entries(occ);
  if (!entries.length) { ul.innerHTML='<li class="empty">No workers in zones</li>'; return; }
  ul.innerHTML = entries.map(([zone,tids],i) => {
    const on = tids.length>0;
    const c  = ZONE_COLORS[i%ZONE_COLORS.length];
    return `<li class="zitem ${on?'on':''}">
      <div>
        <div class="zname">
          <span class="zdot ${on?'on':''}" style="${on?'background:'+c+';box-shadow:0 0 5px '+c+'88':''}"></span>
          ${zone}
        </div>
        ${on?`<div class="zwho" style="color:${c}">${tids.map(t=>'#'+t).join(', ')}</div>`:''}
      </div>
      <span class="zcount ${on?'on':''}" style="${on?'color:'+c:''}">${tids.length}</span>
    </li>`;
  }).join('');
}

// populate model dropdown from /models
async function populateModelDropdown() {
  const res = await fetch('/models').catch(()=>null);
  if (!res || !res.ok) return;
  const models = await res.json();
  if (!models.length) return;
  const sel = document.getElementById('c-model');
  sel.innerHTML = models.map(m=>`<option value="${m.name}">${m.name}</option>`).join('');
}

// ═══════════════════════════════════════════════════════════
// MODELS TAB
// ═══════════════════════════════════════════════════════════
async function loadModels() {
  const res = await fetch('/models').catch(()=>null);
  const grid = document.getElementById('model-grid');
  if (!res||!res.ok) { grid.innerHTML='<div class="empty">Cannot reach service</div>'; return; }
  const models = await res.json();
  if (!models.length) { grid.innerHTML='<div class="empty">No models found</div>'; return; }
  grid.innerHTML = models.map(m=>`
    <div class="model-card">
      <div class="model-icon">.pt</div>
      <div>
        <div class="model-name">${m.name}</div>
        <div class="model-type">${m.has_detector?'✓ Detector':''} ${m.has_reid?'✓ ReID':''}</div>
      </div>
    </div>`).join('');
}

// ═══════════════════════════════════════════════════════════
// API KEY MANAGEMENT
// ═══════════════════════════════════════════════════════════

async function createKey() {
  const name = document.getElementById('key-name').value.trim();
  if (!name) { setMsg('key-create-msg','Enter a key name','err'); return; }
  setMsg('key-create-msg','Creating…','info');

  const res = await fetch('/admin/keys', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name}),
  });
  const d = await res.json();
  if (!res.ok) { setMsg('key-create-msg', d.detail || 'Error', 'err'); return; }

  setMsg('key-create-msg', '', '');
  document.getElementById('key-name').value = '';
  document.getElementById('key-raw').textContent = d.raw_key;
  document.getElementById('key-reveal').style.display = 'block';
  loadKeys();
}

function copyKey() {
  const key = document.getElementById('key-raw').textContent;
  navigator.clipboard.writeText(key).then(() => {
    const btn = event.target;
    btn.textContent = '✓ Copied';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

async function loadKeys() {
  const res = await fetch('/admin/keys').catch(() => null);
  const container = document.getElementById('key-list');
  if (!res || !res.ok) { container.innerHTML = '<div class="empty">Cannot reach service</div>'; return; }
  const keys = await res.json();
  if (!keys.length) { container.innerHTML = '<div class="empty">No API keys yet</div>'; return; }

  container.innerHTML = keys.map(k => `
    <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;
                background:var(--bg4);border:1px solid var(--border2);border-radius:7px">
      <div style="flex:1">
        <div style="font-size:.8rem;font-weight:600">${k.name}</div>
        <div style="font-size:.65rem;color:var(--muted);font-family:monospace">id: ${k.id} &nbsp;·&nbsp; ${new Date(k.created_at).toLocaleString()}</div>
      </div>
      <button class="btn sm danger" onclick="deleteKey('${k.id}','${k.name}')">Delete</button>
    </div>`).join('');
}

async function deleteKey(id, name) {
  if (!confirm('Delete key "' + name + '"?\nClients using this key will lose access.')) return;
  await fetch('/admin/keys/' + id, {method: 'DELETE'});
  document.getElementById('key-reveal').style.display = 'none';
  loadKeys();
}

// ═══════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════
function setMsg(id, text, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'msg ' + (type || '');
  el.style.display = text ? 'block' : 'none';
}
function zeMsg(id, text, type) { setMsg(id, text, type); }
function setStatus(msg) {
  document.getElementById('sbar').textContent = msg;
}

// ═══════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════
refreshSessions();
populateModelDropdown();
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return HTMLResponse(content=_HTML)
