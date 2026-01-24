# DrumAssist
simple metronomic sample generation to drive sample pad or drum machine for in-ear click track



I'm planning on a headless setup for the pattern selection and hardware buttons for the start and tap tempo function

That is a perfect project for a Raspberry Pi Zero. Even though it’s low-power, a metronome or basic drum sequencer is mostly about precise timing, which the Zero can handle easily if you use the right libraries.

Since you know Python, you don't need to write the audio engine from scratch. You can leverage existing packages to handle the "heavy lifting" of sound and GPIO (buttons).

1. Recommended Software Stack
For a headless Pi Zero, I recommend this combination:

gpiozero: The gold standard for Raspberry Pi buttons. It’s much cleaner than the old RPi.GPIO and handles "debouncing" (preventing double-clicks) automatically.

pydub or pygame.mixer: For playing the drum samples. pygame is slightly easier for beginners, but pydub (paired with simpleaudio) often has lower latency on the Pi Zero.

mido (Optional): If you eventually want your Pi to trigger other gear via MIDI rather than just making its own sound.

2. Hardware "Gotcha" for Pi Zero
The Raspberry Pi Zero does not have a 3.5mm audio jack. To get sound out for a metronome, you will need:

USB Sound Card: The simplest "plug and play" option.

I2S DAC (e.g., Pimoroni pHAT DAC): A small board that sits on the pins for high-quality audio.

HDMI Audio Extractor: If you're plugged into a monitor/TV.

3. How to Structure the Code
You can build this by combining a few simple Python concepts.

Tap Tempo Logic
Instead of complex music theory, tap tempo is just math. You record the time of each button press and calculate the average gap.

Python
from gpiozero import Button
import time

taps = []

def get_bpm():
    global taps
    taps.append(time.time())
    taps = taps[-4:]  # Keep only the last 4 taps for a rolling average
    if len(taps) >= 2:
        avg_gap = (taps[-1] - taps[0]) / (len(taps) - 1)
        return 60 / avg_gap
    return 120  # Default
The Sequencer Pattern
Think of a drum pattern as a simple list. A "1" is a hit, and a "0" is silence.

Python
# A simple 4/4 rock beat
pattern = [1, 0, 0, 0, 1, 0, 0, 0] 
# To play it:
for hit in pattern:
    if hit:
        play_click_sound()
    time.sleep(calculated_delay)
4. Running it Headless
To make it work like a real piece of hardware (turning on when you plug in the Pi), you'll want to use systemd. This is a small configuration file that tells Linux to run your Python script automatically on boot.

Next Steps
Would you like me to write a basic starter script for you that combines a "Start/Stop" button and a "Tap Tempo" button using the gpiozero library?

Why sound. Can't it all be midi

It actually makes much more sense to do this via MIDI, especially on a Pi Zero. Since the Zero lacks a built-in headphone jack, going the MIDI route saves you from buying a USB sound card or an audio pHAT.

By using MIDI, your Pi Zero becomes a "Brain" that tells other gear (like a drum machine, a laptop, or even a hardware synth) exactly when to play.

Two Ways to Handle MIDI on a Pi Zero
1. The "USB Gadget" Method (The Coolest Way)
The Pi Zero has a unique feature: it can pretend to be a USB device. You can configure it so that when you plug it into a computer or a tablet, the computer sees it as a Class-Compliant MIDI Controller.

No extra hardware needed: Just a high-quality micro-USB cable.

Best for: Sending timing to a DAW (Ableton, Logic) or a VST drum kit.

2. The USB-to-MIDI Adapter Method
You can plug a standard USB-to-MIDI cable into the Pi’s data port (using a micro-USB OTG adapter).

Best for: Driving hardware drum modules (like a Roland V-Drums brain) or external synthesizers.

Recommended Python Library: mido
For MIDI, mido is the industry standard for Python. It is lightweight and very easy to read.

Install it via terminal:

Bash
pip install mido python-rtmidi
How the code changes: Instead of loading a .wav file, you simply send a "Note On" message. For a metronome, you’d usually send MIDI Note 37 (Side Stick) or 42 (Closed Hi-Hat) on MIDI Channel 10 (the standard drum channel).

Python
import mido
import time

# Open the output port (this could be your drum brain or virtual MIDI)
outport = mido.open_output('Your_Device_Name')

def play_metronome_hit():
    # Note 37 = Side Stick, velocity 100, channel 9 (Mido uses 0-15, so 9 is Ch. 10)
    msg = mido.Message('note_on', note=37, velocity=100, channel=9)
    outport.send(msg)
    
    # MIDI needs a "Note Off" or the sound might ring forever on some synths
    time.sleep(0.05) 
    outport.send(mido.Message('note_off', note=37, channel=9))
Why MIDI is better for your Headless Setup:
Zero Audio Latency: You don't have to worry about "buffer sizes" or crackling audio on the weak Pi Zero processor.

Perfect Timing: MIDI messages are tiny (only 3 bytes). The Pi Zero can send these with microsecond precision.

Flexibility: You can change the "sound" of your metronome just by changing the patch on your receiving device, without touching your Python code.

Next Step
Would you like the instructions on how to turn your Pi Zero into a USB MIDI Gadget so it shows up as a MIDI device automatically when plugged in?

i'd like you to search for or if it doesn't exist, arrange the setup for a USB Midi Gadget with the headless ability to choose the pattern and types of sound that ill help a drummer (me) to hear the rhythms in a piece supporting them (me) to play the music at a steady progressive pace picked by agreement with the band and tapped out on a hardware button to get the tempo as desired. Ideally the headless setup will run a little webpage or ui to pick the pattern and time signature which can then be output to a midi device - in my case an Alessis Sample Pad Pro. I'll be using this to produce suitable sounds in my ear, rim shots, block or closed high hat to outline the shape of the rhythm.

This is a fantastic use for a Raspberry Pi Zero. It is perfectly capable of handling this.

Correction on "Gadget" vs. "Host" mode: Since you want to plug the Pi directly into the Alesis SamplePad, the Pi must act as the HOST (the computer), not a Gadget.

Gadget Mode: Pi acts like a keyboard you plug into a PC.

Host Mode (What you need): Pi acts like the PC. You just need a Micro-USB OTG (On-The-Go) Adapter to plug the Alesis USB cable into the Pi.

Here is the complete solution for a Headless "Drummer's Assistant" that creates its own Wi-Fi Control Page, accepts Hardware Tap Tempo, and drives your Alesis.

1. The Hardware Setup
Pi Zero W / 2W: Running Raspberry Pi OS Lite (Headless).

USB OTG Adapter: Converts the Pi's Micro-USB data port to a standard USB-A port.

Connection: Plug the Alesis SamplePad USB cable into the OTG adapter.

Buttons:

GPIO 17: Tap Tempo (Momentary Switch) -> Connect between Pin 17 and GND.

GPIO 27: Start/Stop (Momentary Switch) -> Connect between Pin 27 and GND.

2. The Software Logic
We will use Python with three key libraries:

flask: Serves the "Little Webpage" to your phone for pattern picking.

mido: Sends MIDI to the Alesis.

gpiozero: Handles the physical buttons.

3. The Code
Save this file as drummer_assist.py on your Pi.

Python
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
4. How to run it
Install dependencies:

Bash
sudo apt-get update
sudo apt-get install python3-pip python3-rtmidi
pip3 install mido flask gpiozero
Make it Headless: You want this to run automatically when you plug the Pi in. Create a system service:

Bash
sudo nano /etc/systemd/system/drummer.service
Paste this in:

Ini, TOML
[Unit]
Description=Drummer Metronome
After=network.target sound.target

[Service]
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/drummer_assist.py
Restart=always

[Install]
WantedBy=multi-user.target
Enable it:

Bash
sudo systemctl enable drummer.service
sudo systemctl start drummer.service
5. Accessing the Web Page
Since you are at a gig/practice, you might not have a router. You should configure your Raspberry Pi to act as a Wi-Fi Hotspot (Access Point).

Use raspi-config or a tool like RaspAP to set up the hotspot.

Once set up, connect your phone to the Pi's Wi-Fi network (e.g., "DrumPi").

Open your browser and type the Pi's IP address (usually 192.168.4.1 or drumpi.local).
