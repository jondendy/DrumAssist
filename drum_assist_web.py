from flask import Flask, render_template_string, request, jsonify
import engine

app = Flask(__name__)

HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>DrumAssist</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { margin:0; font-family: Arial, sans-serif; background:#111; color:#eee; }
    .layout { display:flex; height:100vh; }
    .left { width: 340px; max-width: 45vw; overflow:auto; border-right:1px solid #333; background:#161616; }
    .right { flex:1; display:flex; flex-direction:column; }

    .header { padding:12px 14px; border-bottom:1px solid #333; background:#1f1f1f; position:sticky; top:0; }
    .flash { flex:1; display:flex; align-items:center; justify-content:center; user-select:none; cursor:pointer; }
    .flash.accent { background:#7f1d1d; }
    .flash.beat { background:#1d2a7f; }

    table { width:100%; border-collapse:collapse; }
    th, td { padding:10px 12px; border-bottom:1px solid #222; font-size:14px; }
    tr:hover { background:#202020; cursor:pointer; }
    tr.active { background:#2a2a2a; }

    .controls { padding:14px; border-top:1px solid #333; background:#202020; }
    .row { display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:center; margin:8px 0; }
    button { font-size:16px; padding:10px 14px; border-radius:10px; border:0; cursor:pointer; }
    .go { background:#2980b9; color:#fff; }
    .stop { background:#c0392b; color:#fff; }
    .alt { background:#444; color:#fff; }
    .bpm { font-size:52px; font-weight:700; color:#00ff66; }

    .editor { padding:14px; border-top:1px solid #333; background:#1a1a1a; }
    input[type=text] { width:100%; padding:10px; font-size:16px; border-radius:8px; border:1px solid #444; background:#111; color:#eee; box-sizing:border-box; }
    textarea { width:100%; padding:10px; font-size:16px; border-radius:8px; border:1px solid #444; background:#111; color:#eee; box-sizing:border-box; min-height:78px; }
    .small { opacity:0.8; font-size:13px; margin-top:6px; }
    .msg { min-height: 18px; margin-top:8px; font-size:14px; color:#ffcc66; text-align:center; }

    #pattern { text-align:center; padding:10px 0 0; line-height:2.2; }
    .step { padding:0.2rem 0.45rem; border-bottom:2px solid transparent; color:#ccc; }
    .step.active { border-bottom-color:#ffcc00; color:#fff; }

    @media (max-width: 820px){
      .left { width: 46vw; }
    }
  </style>
</head>
<body>
<div class="layout">
  <div class="left">
    <div class="header">
      <div style="font-weight:700;">Patterns</div>
      <div class="small">Tap a row to load into editor</div>
    </div>
    <table id="patternsTable">
      <thead>
        <tr><th>#</th><th>Name</th><th>Len</th><th>Fill</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="right">
    <div id="flash" class="flash" onclick="tap()">Tap tempo / click</div>

    <div class="controls">
      <div class="row">
        <div id="status">STOPPED</div>
      </div>

      <div class="row">
        <div class="bpm"><span id="bpm">--</span> BPM</div>
      </div>

      <div class="row">
        <button id="toggleBtn" class="go" onclick="togglePlay()">START</button>
        <button class="alt" onclick="tap()">TAP</button>
        <button class="alt" onclick="adjust(-5)">-5</button>
        <button class="alt" onclick="adjust(5)">+5</button>
      </div>

      <div class="row">
        <button class="alt" onclick="next()">Next (pattern or fill)</button>
        <button class="alt" onclick="fill(1)">Fill 1 bar</button>
        <button class="alt" onclick="fill(2)">Fill 2 bars</button>
      </div>

      <div id="pattern"></div>
      <div class="msg" id="fillInfo"></div>
    </div>

    <div class="editor">
      <div style="font-weight:700; margin-bottom:8px;">Pattern editor</div>
      <div class="small">Tokens: A=accent, x=click, .=rest. Spaces and | are ignored. Multi-line supported.</div>

      <div style="margin-top:10px;">Name</div>
      <input id="editName" type="text" />

      <div style="margin-top:10px;">Main groove</div>
      <textarea id="editMain" spellcheck="false"></textarea>

      <div style="margin-top:10px;">Fill (optional; must match main length)</div>
      <textarea id="editFill" spellcheck="false"></textarea>

      <div class="row" style="margin-top:10px;">
        <button class="alt" onclick="loadCurrentIntoEditor()">Reload from current</button>
        <button class="go" onclick="savePattern()">Save pattern</button>
      </div>

      <div class="msg" id="msg"></div>
    </div>
  </div>
</div>

<script>
let lastBeatCount = -1;
let patternsCache = [];
let currentIdx = 0;

function tokenFor(b){ return (b === 1 ? 'A' : (b === 2 ? 'x' : '.')); }

function beatsToMultiline(beats){
  // Default: show as 2 lines if long, otherwise 1 line
  const chars = beats.map(tokenFor);
  if (chars.length <= 8) return chars.join(' ');
  const mid = Math.ceil(chars.length/2);
  return chars.slice(0, mid).join(' ') + "\n" + chars.slice(mid).join(' ');
}

function renderPattern(beats, activeIdx) {
  const el = document.getElementById('pattern');
  el.innerHTML = '';
  beats.forEach((b, i) => {
    const s = document.createElement('span');
    s.className = 'step' + (i === activeIdx ? ' active' : '');
    s.dataset.index = i;
    s.textContent = tokenFor(b);
    el.appendChild(s);
  });
}

function renderTable(patterns, activeIdx){
  const tbody = document.querySelector('#patternsTable tbody');
  tbody.innerHTML = '';
  patterns.forEach((p, i) => {
    const tr = document.createElement('tr');
    if (i === activeIdx) tr.classList.add('active');
    tr.innerHTML = `<td>${i}</td><td>${p.name}</td><td>${p.beats.length}</td><td>${p.fill ? 'Y' : ''}</td>`;
    tr.onclick = () => loadPatternToEditor(i);
    tbody.appendChild(tr);
  });
}

function loadPatternToEditor(i){
  const p = patternsCache[i];
  currentIdx = i;
  document.getElementById('editName').value = p.name;
  document.getElementById('editMain').value = beatsToMultiline(p.beats);
  document.getElementById('editFill').value = p.fill ? beatsToMultiline(p.fill) : '';
  document.getElementById('msg').textContent = `Loaded pattern ${i} into editor.`;
}

async function fetchPatterns(){
  const r = await fetch('/patterns');
  patternsCache = await r.json();
  renderTable(patternsCache, currentIdx);
}

function setMsg(t){ document.getElementById('msg').textContent = t || ''; }

async function savePattern(){
  const payload = {
    idx: currentIdx,
    name: document.getElementById('editName').value,
    main: document.getElementById('editMain').value,
    fill: document.getElementById('editFill').value
  };
  const r = await fetch('/pattern/update', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await r.json();
  if (!data.ok){
    setMsg('Error: ' + data.error);
    return;
  }
  setMsg('Saved.');
  await fetchPatterns();
  await poll();
}

async function loadCurrentIntoEditor(){
  await fetchPatterns();
  loadPatternToEditor(currentIdx);
}

function updateUI(data) {
  document.getElementById('bpm').textContent = data.bpm;
  document.getElementById('status').textContent = data.playing ? 'PLAYING' : 'STOPPED';

  const btn = document.getElementById('toggleBtn');
  btn.textContent = data.playing ? 'STOP' : 'START';
  btn.className = data.playing ? 'stop' : 'go';

  currentIdx = data.current_idx;

  renderPattern(data.pattern_beats, data.step);
  renderTable(patternsCache, currentIdx);

  const fillInfo = document.getElementById('fillInfo');
  if (data.has_fill){
    fillInfo.textContent = `Fill: pending ${data.fill_pending_bars} bar(s), active ${data.fill_active_bars} bar(s).`;
  } else {
    fillInfo.textContent = `No fill set for this pattern.`;
  }

  if (data.playing && data.beat_count !== lastBeatCount) {
    lastBeatCount = data.beat_count;
    const flash = document.getElementById('flash');
    flash.classList.remove('accent', 'beat');
    if (data.last_beat_type === 1) {
      flash.classList.add('accent');
      setTimeout(()=>flash.classList.remove('accent'), 120);
    } else if (data.last_beat_type === 2) {
      flash.classList.add('beat');
      setTimeout(()=>flash.classList.remove('beat'), 80);
    }
  }
}

async function poll() {
  const r = await fetch('/status');
  updateUI(await r.json());
}

function togglePlay() { fetch('/toggle').then(r=>r.json()).then(updateUI); }
function tap() { fetch('/tap', {method:'POST'}).then(r=>r.json()).then(updateUI); }
function adjust(delta) {
  fetch('/bpm', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({delta})})
    .then(r=>r.json()).then(updateUI);
}
function next() { fetch('/next').then(r=>r.json()).then(updateUI); }
function fill(bars) {
  fetch('/fill', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({bars})})
    .then(r=>r.json()).then(updateUI);
}

document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); tap(); }
  if (e.code === 'Enter') { togglePlay(); }
});

setInterval(poll, 100);
(async () => { await fetchPatterns(); await poll(); })();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/patterns")
def patterns():
    out = []
    for p in engine.PATTERNS:
        out.append({
            "name": p["name"],
            "beats": p["beats"],
            "fill": p.get("fill")
        })
    return jsonify(out)

@app.route("/pattern/update", methods=["POST"])
def pattern_update():
    data = request.get_json(force=True)
    try:
        engine.update_pattern_from_text(
            idx=int(data.get("idx", 0)),
            name=str(data.get("name", "")),
            beats_text=str(data.get("main", "")),
            fill_text=str(data.get("fill", "")),
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/status")
def status():
    st = engine.get_status()
    beats = engine.PATTERNS[st["current_idx"]]["beats"]
    st["pattern_beats"] = beats
    return jsonify(st)

@app.route("/toggle")
def toggle():
    engine.handle_start()
    return status()

@app.route("/tap", methods=["POST"])
def tap():
    engine.handle_tap()
    return status()

@app.route("/bpm", methods=["POST"])
def bpm():
    data = request.get_json(force=True)
    engine.adjust_bpm(int(data.get("delta", 0)))
    return status()

@app.route("/pattern/<int:idx>")
def pattern(idx):
    engine.set_pattern(idx)
    return status()

@app.route("/next")
def nextp():
    # This calls "fill if playing, next pattern if stopped"
    engine.next_button_action()
    return status()

@app.route("/fill", methods=["POST"])
def fill():
    data = request.get_json(force=True)
    engine.request_fill(int(data.get("bars", 1)))
    return status()

if __name__ == "__main__":
    engine.start_engine()
    app.run(host="0.0.0.0", port=5000, debug=False)
