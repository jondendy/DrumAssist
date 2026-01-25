import time
import threading
import json
import os
from flask import Flask, render_template_string, request, jsonify

# --- CONFIG ---
SAVE_FILE = "dh2_settings.json"

# --- PATTERNS ---
PATTERNS = [
    {'name': '4/4 Basic', 'beats': [1, 2, 2, 2]},
    {'name': '4/4 Subdivisions', 'beats': [1, 0, 2, 0, 2, 0, 2, 0]},
    {'name': '6/8 Feel', 'beats': [1, 2, 2, 1, 2, 2]},
    {'name': '3/4 Waltz', 'beats': [1, 2, 2]},
    {'name': 'Prog Rock 7/8', 'beats': [1, 2, 1, 2, 1, 2, 2]}
]

# --- STATE ---
state = {
    "bpm": 120,
    "current_idx": 0,
    "playing": False,
    "last_beat_type": 0,
    "beat_count": 0
}

app = Flask(__name__)

def save_state():
    with open(SAVE_FILE, 'w') as f:
        json.dump({"bpm": state["bpm"], "idx": state["current_idx"]}, f)

def load_state():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
            state["bpm"] = data.get("bpm", 120)
            state["current_idx"] = data.get("idx", 0)

load_state()

# --- SEQUENCER ENGINE ---
def run_sequencer():
    step = 0
    while True:
        if state["playing"]:
            pattern = PATTERNS[state["current_idx"]]["beats"]
            beat_type = pattern[step % len(pattern)]
            state["last_beat_type"] = beat_type
            state["beat_count"] = step
            
            # Timing
            sleep_time = 60.0 / state["bpm"]
            if len(pattern) > 4:
                sleep_time /= 2
            
            time.sleep(sleep_time)
            step += 1
        else:
            state["last_beat_type"] = 0
            time.sleep(0.1)

# --- WEB UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Drum Assistant Web</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #1a1a1a; 
            color: #eee; 
            text-align: center; 
            margin: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        #flash-container {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.05s;
            cursor: pointer;
            user-select: none;
        }
        .controls {
            padding: 20px;
            background: #2d2d2d;
            border-top: 2px solid #444;
        }
        .bpm-display { font-size: 5rem; font-weight: bold; margin: 10px 0; color: #00ff00; }
        button { 
            font-size: 1.2rem; 
            padding: 15px 30px; 
            margin: 5px; 
            border-radius: 10px; 
            border: none; 
            background: #007bff; 
            color: white; 
            font-weight: bold;
            cursor: pointer;
        }
        button:active { transform: scale(0.98); }
        .stop { background: #dc3545; }
        select { font-size: 1.2rem; padding: 10px; border-radius: 5px; margin: 10px; }
        
        /* Flash Animations */
        .flash-accent { background: #ff4444 !important; }
        .flash-beat { background: #4444ff !important; }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }
        .playing { background: #28a745; color: white; }
        .stopped { background: #6c757d; color: white; }
    </style>
</head>
<body>
    <div id="flash-container" onclick="handleTap()">
        <div>
            <div id="status" class="status-badge stopped">STOPPED</div>
            <div class="bpm-display" id="bpm-val">{{ bpm }}</div>
            <div id="pattern-name" style="font-size: 1.5rem; opacity: 0.8;">{{ pattern_name }}</div>
            <p style="opacity: 0.5;">Click anywhere or press SPACE to tap</p>
        </div>
    </div>

    <div class="controls">
        <select id="pattern-select" onchange="updatePattern()">
            {% for p in patterns %}
            <option value="{{ loop.index0 }}" {% if loop.index0 == current_idx %}selected{% endif %}>{{ p.name }}</option>
            {% endfor %}
        </select>
        <br>
        <button id="toggle-btn" onclick="togglePlay()" class="">START</button>
        <button onclick="handleTap()">TAP TEMPO</button>
    </div>

    <script>
        let lastBeatCount = -1;
        
        function togglePlay() {
            fetch('/toggle').then(r => r.json()).then(updateUI);
        }

        function handleTap() {
            fetch('/tap').then(r => r.json()).then(updateUI);
        }

        function updatePattern() {
            let idx = document.getElementById('pattern-select').value;
            fetch('/set_pattern/' + idx).then(r => r.json()).then(updateUI);
        }

        function updateUI(data) {
            document.getElementById('bpm-val').innerText = data.bpm;
            let btn = document.getElementById('toggle-btn');
            let status = document.getElementById('status');
            
            if (data.playing) {
                btn.innerText = "STOP";
                btn.className = "stop";
                status.innerText = "PLAYING";
                status.className = "status-badge playing";
            } else {
                btn.innerText = "START";
                btn.className = "";
                status.innerText = "STOPPED";
                status.className = "status-badge stopped";
            }
        }

        // Space bar listener
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space') {
                e.preventDefault();
                handleTap();
            } else if (e.code === 'Enter') {
                togglePlay();
            }
        });

        // Polling for flashes and updates
        setInterval(() => {
            fetch('/status').then(r => r.json()).then(data => {
                updateUI(data);
                
                if (data.playing && data.beat_count !== lastBeatCount) {
                    lastBeatCount = data.beat_count;
                    let container = document.getElementById('flash-container');
                    
                    if (data.last_beat_type === 1) {
                        container.classList.add('flash-accent');
                        setTimeout(() => container.classList.remove('flash-accent'), 100);
                    } else if (data.last_beat_type === 2) {
                        container.classList.add('flash-beat');
                        setTimeout(() => container.classList.remove('flash-beat'), 50);
                    }
                }
            });
        }, 50);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, 
                                bpm=state["bpm"], 
                                patterns=PATTERNS, 
                                current_idx=state["current_idx"],
                                pattern_name=PATTERNS[state["current_idx"]]["name"])

@app.route('/status')
def get_status():
    return jsonify({
        "bpm": state["bpm"],
        "playing": state["playing"],
        "last_beat_type": state["last_beat_type"],
        "beat_count": state["beat_count"]
    })

@app.route('/toggle')
def toggle():
    state["playing"] = not state["playing"]
    return get_status()

tap_times = []
@app.route('/tap')
def tap():
    global tap_times
    now = time.time()
    if tap_times and (now - tap_times[-1] > 2.0): tap_times = []
    tap_times.append(now)
    tap_times = tap_times[-4:]
    if len(tap_times) >= 2:
        intervals = [t - s for s, t in zip(tap_times, tap_times[1:])]
        avg = sum(intervals) / len(intervals)
        state["bpm"] = int(60.0 / avg)
        save_state()
    return get_status()

@app.route('/set_pattern/<int:idx>')
def set_pattern(idx):
    state["current_idx"] = idx % len(PATTERNS)
    save_state()
    return get_status()

if __name__ == '__main__':
    threading.Thread(target=run_sequencer, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
