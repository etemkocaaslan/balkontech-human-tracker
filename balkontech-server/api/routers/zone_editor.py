from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI"])

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Zone Editor</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#0f0f0f;color:#e0e0e0;font-family:'Segoe UI',system-ui,sans-serif;display:flex;height:100vh;overflow:hidden}

    /* ── Sidebar ── */
    .sidebar{width:300px;background:#141414;border-right:1px solid #222;display:flex;flex-direction:column;overflow-y:auto;flex-shrink:0}
    .sidebar-section{padding:16px;border-bottom:1px solid #222}
    .sidebar-section h2{font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;color:#555;margin-bottom:12px}
    input,select,textarea{width:100%;background:#1e1e1e;border:1px solid #333;border-radius:6px;color:#e0e0e0;padding:8px 10px;font-size:.82rem;outline:none;margin-bottom:8px}
    input:focus,select:focus{border-color:#555}
    .btn{display:block;width:100%;padding:9px;border:none;border-radius:6px;font-size:.82rem;font-weight:600;cursor:pointer;margin-bottom:6px;transition:background .15s}
    .btn-primary{background:#22c55e;color:#000}.btn-primary:hover{background:#16a34a}
    .btn-secondary{background:#1e1e1e;color:#aaa;border:1px solid #333}.btn-secondary:hover{background:#2a2a2a}
    .btn-danger{background:#1e1e1e;color:#ef4444;border:1px solid #333}.btn-danger:hover{background:#2a1111}

    .point-list{list-style:none;max-height:140px;overflow-y:auto}
    .point-item{display:flex;justify-content:space-between;align-items:center;padding:4px 8px;background:#1e1e1e;border-radius:4px;margin-bottom:4px;font-size:.75rem;font-family:monospace}
    .point-item button{background:none;border:none;color:#ef4444;cursor:pointer;font-size:.8rem}

    .zone-list{list-style:none}
    .zone-item{padding:8px;background:#1a2e1a;border-radius:6px;margin-bottom:6px;font-size:.78rem}
    .zone-item .zone-name{color:#22c55e;font-weight:600}
    .zone-item .zone-meta{color:#555;font-size:.7rem;margin-top:2px}
    .zone-item button{float:right;background:none;border:none;color:#ef4444;cursor:pointer;font-size:.85rem}

    .msg{font-size:.75rem;padding:6px 8px;border-radius:4px;margin-top:8px}
    .msg.ok{background:#1a2e1a;color:#22c55e}
    .msg.err{background:#2a1111;color:#ef4444}

    /* ── Canvas area ── */
    .canvas-wrap{flex:1;display:flex;align-items:center;justify-content:center;background:#000;position:relative;overflow:hidden}
    canvas{cursor:crosshair;max-width:100%;max-height:100%;object-fit:contain}
    .canvas-hint{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.7);color:#888;font-size:.72rem;padding:4px 12px;border-radius:12px;pointer-events:none}
  </style>
</head>
<body>

<!-- Sidebar -->
<aside class="sidebar">

  <!-- Video source -->
  <div class="sidebar-section">
    <h2>Video Source</h2>
    <input id="video-path" placeholder="out_1917_1080.mp4" value="out_1917_1080.mp4"/>
    <input id="frame-index" type="number" value="0" min="0" placeholder="Frame index"/>
    <button class="btn btn-primary" onclick="loadSnapshot()">Load Frame</button>
    <div id="snapshot-msg"></div>
  </div>

  <!-- Zone definition -->
  <div class="sidebar-section">
    <h2>Define Zone</h2>
    <input id="video-id" placeholder="Video ID (e.g. audi_b9)"/>
    <input id="zone-name" placeholder="Zone name (e.g. Station A)"/>
    <input id="zone-desc" placeholder="Description (optional)"/>

    <div style="margin-bottom:6px">
      <span style="font-size:.72rem;color:#555">Points (<span id="pt-count">0</span>) — click on frame</span>
      <button class="btn btn-secondary" style="margin-top:4px" onclick="undoPoint()">↩ Undo last point</button>
      <button class="btn btn-secondary" onclick="clearPoints()">✕ Clear all</button>
    </div>

    <ul class="point-list" id="point-list"></ul>
    <button class="btn btn-primary" onclick="saveZone()" style="margin-top:8px">💾 Save Zone</button>
    <div id="save-msg"></div>
  </div>

  <!-- Saved zones -->
  <div class="sidebar-section" style="flex:1">
    <h2>Saved Zones</h2>
    <button class="btn btn-secondary" onclick="loadZones()">↻ Refresh</button>
    <ul class="zone-list" id="zone-list" style="margin-top:8px"></ul>
  </div>

</aside>

<!-- Canvas -->
<div class="canvas-wrap">
  <canvas id="canvas"></canvas>
  <div class="canvas-hint" id="canvas-hint">Load a frame to start defining zones</div>
</div>

<script>
  const canvas = document.getElementById('canvas');
  const ctx    = canvas.getContext('2d');

  let imgObj   = null;    // HTMLImageElement of the snapshot
  let imgW = 0, imgH = 0; // original frame dimensions
  let points   = [];      // current polygon points (in PIXEL space of original frame)
  let savedZones = [];    // zones loaded from API

  // ── Snapshot loading ──────────────────────────────────────────

  async function loadSnapshot() {
    setMsg('snapshot-msg', '', '');
    const videoPath  = document.getElementById('video-path').value.trim();
    const frameIndex = parseInt(document.getElementById('frame-index').value) || 0;
    if (!videoPath) return;

    try {
      const res = await fetch('/zones/snapshot', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({video_path: videoPath, frame_index: frameIndex})
      });
      const data = await res.json();
      if (!res.ok) { setMsg('snapshot-msg', data.detail, 'err'); return; }

      imgW = data.width; imgH = data.height;
      const img = new Image();
      img.onload = () => {
        imgObj = img;
        resizeCanvas();
        drawAll();
        document.getElementById('canvas-hint').textContent =
          `${imgW}×${imgH} — click to add polygon points`;
        // Auto-fill video-id from filename
        const stem = videoPath.split(/[\\/]/).pop().replace(/\.[^.]+$/, '');
        if (!document.getElementById('video-id').value)
          document.getElementById('video-id').value = stem;
        loadZones();
        setMsg('snapshot-msg', `Loaded frame ${frameIndex} (${imgW}×${imgH})`, 'ok');
      };
      img.src = 'data:image/jpeg;base64,' + data.frame_b64;
    } catch(e) { setMsg('snapshot-msg', 'Network error', 'err'); }
  }

  // ── Canvas resize & draw ──────────────────────────────────────

  function resizeCanvas() {
    if (!imgObj) return;
    const wrap = canvas.parentElement;
    const scale = Math.min(wrap.clientWidth / imgW, wrap.clientHeight / imgH);
    canvas.width  = Math.floor(imgW * scale);
    canvas.height = Math.floor(imgH * scale);
  }

  window.addEventListener('resize', () => { resizeCanvas(); drawAll(); });

  function drawAll() {
    if (!imgObj) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(imgObj, 0, 0, canvas.width, canvas.height);
    drawSavedZones();
    drawCurrentPolygon();
  }

  function canvasToFrame(cx, cy) {
    const sx = imgW / canvas.width;
    const sy = imgH / canvas.height;
    return { x: Math.round(cx * sx), y: Math.round(cy * sy) };
  }

  function frameToCanvas(fx, fy) {
    const sx = canvas.width  / imgW;
    const sy = canvas.height / imgH;
    return { x: fx * sx, y: fy * sy };
  }

  // ── Current polygon ───────────────────────────────────────────

  function drawCurrentPolygon() {
    if (points.length === 0) return;
    const pts = points.map(p => frameToCanvas(p.x, p.y));

    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    pts.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
    if (points.length >= 3) {
      ctx.closePath();
      ctx.fillStyle = 'rgba(34,197,94,0.15)';
      ctx.fill();
    }
    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 2;
    ctx.stroke();

    pts.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#22c55e';
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px monospace';
      ctx.fillText(i + 1, p.x + 7, p.y - 4);
    });
  }

  // ── Saved zones overlay ───────────────────────────────────────

  const ZONE_COLORS = ['#3b82f6','#f59e0b','#ec4899','#8b5cf6','#06b6d4'];

  function drawSavedZones() {
    savedZones.forEach((z, zi) => {
      const color = ZONE_COLORS[zi % ZONE_COLORS.length];
      const pts = z.points.map(p => frameToCanvas(p.x * imgW, p.y * imgH));
      if (pts.length < 2) return;

      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      pts.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
      ctx.closePath();
      ctx.fillStyle = color + '25';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 3]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Label
      const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
      const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length;
      ctx.fillStyle = color;
      ctx.font = 'bold 12px Segoe UI';
      ctx.textAlign = 'center';
      ctx.fillText(z.name, cx, cy);
      ctx.textAlign = 'left';
    });
  }

  // ── Click to add point ────────────────────────────────────────

  canvas.addEventListener('click', e => {
    if (!imgObj) return;
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const fp = canvasToFrame(cx, cy);
    points.push(fp);
    updatePointList();
    drawAll();
  });

  function updatePointList() {
    document.getElementById('pt-count').textContent = points.length;
    const ul = document.getElementById('point-list');
    ul.innerHTML = points.map((p, i) => `
      <li class="point-item">
        <span>${i+1}. x=${p.x}, y=${p.y}</span>
        <button onclick="removePoint(${i})">✕</button>
      </li>`).join('');
  }

  function removePoint(i) { points.splice(i, 1); updatePointList(); drawAll(); }
  function undoPoint()    { points.pop(); updatePointList(); drawAll(); }
  function clearPoints()  { points = []; updatePointList(); drawAll(); }

  // ── Save zone ─────────────────────────────────────────────────

  async function saveZone() {
    setMsg('save-msg','','');
    const videoId = document.getElementById('video-id').value.trim();
    const name    = document.getElementById('zone-name').value.trim();
    const desc    = document.getElementById('zone-desc').value.trim();

    if (!videoId) { setMsg('save-msg','Video ID required','err'); return; }
    if (!name)    { setMsg('save-msg','Zone name required','err'); return; }
    if (points.length < 3) { setMsg('save-msg','At least 3 points required','err'); return; }

    try {
      const res = await fetch(`/zones/${videoId}`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          name, description: desc || null,
          pixel_points: points,
          reference_width:  imgW,
          reference_height: imgH,
        })
      });
      const data = await res.json();
      if (!res.ok) { setMsg('save-msg', data.detail, 'err'); return; }
      setMsg('save-msg', `Saved: ${data.name}`, 'ok');
      clearPoints();
      document.getElementById('zone-name').value = '';
      document.getElementById('zone-desc').value = '';
      loadZones();
    } catch(e) { setMsg('save-msg','Network error','err'); }
  }

  // ── Load saved zones ──────────────────────────────────────────

  async function loadZones() {
    const videoId = document.getElementById('video-id').value.trim();
    if (!videoId) return;
    try {
      const res = await fetch(`/zones/${videoId}`);
      if (!res.ok) return;
      savedZones = await res.json();
      renderZoneList();
      drawAll();
    } catch(e) {}
  }

  function renderZoneList() {
    const ul = document.getElementById('zone-list');
    if (savedZones.length === 0) {
      ul.innerHTML = '<li style="color:#444;font-size:.78rem">No zones yet</li>';
      return;
    }
    ul.innerHTML = savedZones.map((z, zi) => {
      const color = ZONE_COLORS[zi % ZONE_COLORS.length];
      return `
      <li class="zone-item">
        <button onclick="deleteZone('${z.id}')" title="Delete">✕</button>
        <div class="zone-name" style="color:${color}">${z.name}</div>
        <div class="zone-meta">${z.points.length} points · ref ${z.reference_resolution.width}×${z.reference_resolution.height}</div>
      </li>`;
    }).join('');
  }

  async function deleteZone(zoneId) {
    const videoId = document.getElementById('video-id').value.trim();
    if (!videoId) return;
    if (!confirm('Delete this zone?')) return;
    await fetch(`/zones/${videoId}/${zoneId}`, {method:'DELETE'});
    loadZones();
  }

  // ── Utility ───────────────────────────────────────────────────

  function setMsg(id, text, type) {
    const el = document.getElementById(id);
    el.textContent = text;
    el.className = 'msg ' + type;
  }
</script>
</body>
</html>
"""

@router.get("/zone-editor", response_class=HTMLResponse, include_in_schema=False)
def zone_editor():
    """Interactive zone definition tool."""
    return HTMLResponse(content=_HTML)
