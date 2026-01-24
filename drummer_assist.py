import time
import threading
import mido
from flask import Flask, render_template_string, request, jsonify
from gpiozero import Button

# --- CONFIGURATION ---
MIDI_CHANNEL = 9  # Channel 10 in Midi terms (0-15)
# Alesis SamplePad Note Numbers (Standard General MIDI)
SOUNDS = {
    'click': 37,    # Side Stick
    'accent': 49,   # Crash Cymbal (or assign to a Cowbell on Alesis)
    'subdiv': 42    # Closed Hi-Hat
}

# --- GLOBAL STATE ---
state = {
    'bpm': 100,
    'playing': False,
    'pattern': '4/4', # Default pattern
    'signature': 4    # Beats per bar
}

# --- PATTERNS (1 = Accent, 2 = Click, 0 = Rest/Subdivision) ---
PATTERNS = {
    '4/4 Basic': [1, 2, 2, 2],
    '4/4 Subdivisions': [1, 0, 2, 0, 2, 0, 2, 0],
    '6/8 Feel': [1, 2, 2, 1, 2, 2],
    '3/4 Waltz': [1, 2, 2],
    'Prog Rock 7/8': [1, 2, 1, 2, 1, 2, 2]
}

# --- MIDI SETUP ---
# Tries to find the Alesis automatically. If not, uses default port.
output_port = None
try:
    ports = mido.get_output_names()
    # Look for a USB MIDI device
    matching = [p for p in ports if "USB" in p or "Alesis" in p]
    port_name = matching[0] if matching else ports[0]
    output_port = mido.open_output(port_name)
    print(f"Connected to {port_name}")
except Exception as e:
    print(f"MIDI Error: {e}. Running in dummy mode.")

# --- METRONOME ENGINE (Runs in separate thread) ---
def metronome_loop():
    step = 0
    while True:
        if state['playing'] and output_port:
            current_pat = PATTERNS[state['pattern']]
            beat_type = current_pat[step % len(current_pat)]
            
            # Determine Note
            note = None
            if beat_type == 1: note = SOUNDS['accent']
            elif beat_type == 2: note = SOUNDS['click']
            # elif beat_type == 0: note = SOUNDS['subdiv'] # Optional
            
            if note:
                output_port.send(mido.Message('note_on', note=note, velocity=110, channel=MIDI_CHANNEL))
                # Short sleep to prevent "stuck" notes, though drum brains usually ignore note_off
                time.sleep(0.05)
                output_port.send(mido.Message('note_off', note=note, velocity=0, channel=MIDI_CHANNEL))

            # Calculate sleep based on BPM and Pattern Resolution
            # If pattern has 8 steps for a 4/4 bar, we treat them as eighth notes
            beats_in_bar = len(current_pat)
            # Simple assumption: patterns are written in quarter notes or eighth notes
            # Adjust logic here for complex time signatures
            
            # Logic for sleep: 60 / BPM = Quarter Note duration
            # If pattern is 'subdivisions', runs twice as fast
            sleep_time = 60.0 / state['bpm']
            if len(current_pat) > 4: sleep_time /= 2 # Speed up for eighth notes
            
            time.sleep(sleep_time)
            step += 1
        else:
            time.sleep(0.1)

# Start Engine
t = threading.Thread(target=metronome_loop, daemon=True)
t.start()

# --- BUTTON LOGIC ---
tap_times = []

def on_tap():
    global tap_times
    now = time.time()
    # Reset if pause is too long
    if tap_times and (now - tap_times[-1] > 2.0):
        tap_times = []
    
    tap_times.append(now)
    # Keep last 4 taps
    tap_times = tap_times[-4:]
    
    if len(tap_times) >= 2:
        # Calculate BPM
        intervals = [t - s for s, t in zip(tap_times, tap_times[1:])]
        avg_interval = sum(intervals) / len(intervals)
        new_bpm = int(60.0 / avg_interval)
        if 30 < new_bpm < 300: # Sanity check
            state['bpm'] = new_bpm
            print(f"Tap Tempo: {new_bpm}")

def on_toggle():
    state['playing'] = not state['playing']
    if state['playing']: 
        global tap_times
        tap_times = [] # Reset taps on start

# Setup GPIO
btn_tap = Button(17) # GPIO 17
btn_start = Button(27) # GPIO 27
btn_tap.when_pressed = on_tap
btn_start.when_pressed = on_toggle

# --- WEB UI (FLASK) ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #222; color: #fff; text-align: center; padding: 20px; }
        select, button { font-size: 1.2rem; padding: 15px; width: 100%; margin: 10px 0; border-radius: 8px; border: none; }
        button { background: #007bff; color: white; font-weight: bold; }
        .stop { background: #dc3545; }
        .bpm-display { font-size: 4rem; font-weight: bold; color: #00ff00; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Drum Buddy</h1>
    <div id="bpm" class="bpm-display">{{ bpm }}</div>
    
    <label>Pattern:</label>
    <select id="pattern" onchange="updateSettings()">
        {% for p in patterns %}
        <option value="{{ p }}" {% if p == current_pat %}selected{% endif %}>{{ p }}</option>
        {% endfor %}
    </select>
    
    <button id="toggleBtn" onclick="togglePlay()">Start / Stop</button>

    <script>
        function updateSettings() {
            let pat = document.getElementById('pattern').value;
            fetch('/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pattern: pat})
            });
        }
        
        function togglePlay() {
            fetch('/toggle');
        }

        // Poll for updates (e.g. if you use Tap Tempo button)
        setInterval(() => {
            fetch('/status').then(r => r.json()).then(data => {
                document.getElementById('bpm').innerText = data.bpm;
                let btn = document.getElementById('toggleBtn');
                if (data.playing) {
                    btn.innerText = "STOP";
                    btn.className = "stop";
                } else {
                    btn.innerText = "START";
                    btn.className = "";
                }
            });
        }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, bpm=state['bpm'], patterns=PATTERNS.keys(), current_pat=state['pattern'])

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    if 'pattern' in data:
        state['pattern'] = data['pattern']
    return jsonify(success=True)

@app.route('/toggle')
def toggle():
    on_toggle() # Re-use the hardware logic
    return jsonify(success=True)

@app.route('/status')
def status():
    return jsonify(bpm=state['bpm'], playing=state['playing'])

if __name__ == '__main__':
    # Host 0.0.0.0 makes it accessible to other devices on the network
    app.run(host='0.0.0.0', port=80)
