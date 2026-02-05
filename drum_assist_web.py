import threading
from flask import Flask, render_template_string, request, jsonify

import engine

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>DrumAssist</title>
  <style>
    body { font-family: Arial, sans-serif; background:#111; color:#eee; text-align:center; margin:0; }
    #flash { height: 55vh; display:flex; align-items:center; justify-content:center; cursor:pointer; user-select:none; }
    .controls { padding:16px; background:#222; border-top:1px solid #333; }
    .bpm { font-size: 64px; font-weight:700; color:#00ff66; margin:10px 0; }
    button { font-size:18px; padding:12px 18px; margin:6px; border-radius:10px; border:0; cursor:pointer; }
    .stop { background:#c0392b; color:#fff; }
    .go { background:#2980b9; color:#fff; }
    select { font-size:18px; padding:10px; border-radius:8px; margin:8px; }

    #pattern { margin: 10px 0 0; line-height: 2.2; }
    .step { padding:0.2rem 0.45rem; border-bottom:2px solid transparent; color:#ccc; }
    .step.active { border-bottom-color:#ffcc00; color:#fff; }

    .flash-accent { background:#7f1d1d; }
    .flash-beat { background:#1d2a7f; }
  </style>
</head>
<body>
  <div id="flash" onclick="tap()">Tap tempo (click)</div>

  <div class="controls">
    <div id="status">STOPPED</div>
    <div class="bpm"><span id="bpm">--</span> BPM</div>

    <div>
      <button id="toggle" class="go" onclick="toggle()">START</button>
      <button onclick="tap()">TAP</button>
      <button onclick="adjust(-5)">-5</button>
      <button onclick="adjust(5)">+5</button>
    </div>

    <div>
      <select id="patternSelect" onchange="setPattern()">
        {% for p in patterns %}
          <option value="{{ loop.index0 }}">{{ p.name }}</option>
        {% endfor %}
      </select>
      <button onclick="nextPattern()">Next</button>
    </div>

    <div id="pattern"></div>
  </div>

<script>
let lastBeatCount = -1;

function renderPattern(beats, activeIdx) {
  const el = document.getElementById('pattern');
  el.innerHTML = '';
  beats.forEach((b, i) => {
    const s = document.createElement('span');
    s.className = 'step' + (i === activeIdx ? ' active' : '');
    s.dataset.index = i;
    s.textContent = (b === 1 ? 'A' : (b === 2 ? '•' : '·'));
    el.appendChild(s);
  });
}

function updateUI(data) {
  document.getElementById('bpm').textContent = data.bpm;
  document.getElementById('status').textContent = data.playing ? 'PLAYING' : 'STOPPED';

  const btn = document.getElementById('toggle');
  btn.textContent = data.playing ? 'STOP' : 'START';
  btn.className = data.playing ? 'stop' : 'go';

  const sel = document.getElementById('patternSelect');
  sel.value = data.current_idx;

  renderPattern(data.pattern_beats, data.step);

  if (data.playing && data.beat_count !== lastBeatCount) {
    lastBeatCount = data.beat_count;
    const flash = document.getElementById('flash');
    flash.classList.remove('flash-accent', 'flash-beat');
    if (data.last_beat_type === 1) {
      flash.classList.add('flash-accent');
      setTimeout(()=>flash.classList.remove('flash-accent'), 120);
    } else if (data.last_beat_type === 2) {
      flash.classList.add('flash-beat');
      setTimeout(()=>flash.classList.remove('flash-beat'), 80);
    }
  }
}

async function poll() {
  const r = await fetch('/status');
  updateUI(await r.json());
}

function toggle() { fetch('/toggle').then(r=>r.json()).then(updateUI); }
function tap() { fetch('/tap', {method:'POST'}).then(r=>r.json()).then(updateUI); }
function adjust(delta) {
  fetch('/bpm', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({delta})})
    .then(r=>r.json()).then(updateUI);
}
function setPattern() {
  const idx = document.getElementById('patternSelect').value;
  fetch('/pattern/' + idx).then(r=>r.json()).then(updateUI);
}
function nextPattern() { fetch('/next').then(r=>r.json()).then(updateUI); }

document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); tap(); }
  if (e.code === 'Enter') { toggle(); }
});

setInterval(poll, 80);
poll();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, patterns=engine.PATTERNS)

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
    engine.next_pattern()
    return status()

if __name__ == "__main__":
    engine.start_engine()
    app.run(host="0.0.0.0", port=5000, debug=False)
