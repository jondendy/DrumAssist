import mido
import time
import threading
import json
import os
from gpiozero import Button, LED

# --- CONFIG ---
SAVE_FILE = "dh2_settings.json"
# Physical Pins: 11, 13, 15 for buttons. 12, 16 for LEDs.
btn_start = Button(17)  # Red
btn_tap   = Button(27)  # Blue
btn_next  = Button(22)  # White
led_beat   = LED(18) 
led_status = LED(23)

# --- MIDI CONFIGURATION ---
MIDI_CHANNEL = 9  # Channel 10 in MIDI terms (0-15)
# Alesis SamplePad Note Numbers (Standard General MIDI)
SOUNDS = {
    'click': 37,   # Side Stick
    'accent': 49,  # Crash Cymbal (or assign to a Cowbell on Alesis)
    'subdiv': 42   # Closed Hi-Hat
}

# --- PATTERNS (1 = Accent, 2 = Click, 0 = Rest/Subdivision) ---
PATTERNS = [
    {'name': '4/4 Basic', 'beats': [1, 2, 2, 2]},
    {'name': '4/4 Subdivisions', 'beats': [1, 0, 2, 0, 2, 0, 2, 0]},
    {'name': '6/8 Feel', 'beats': [1, 2, 2, 1, 2, 2]},
    {'name': '3/4 Waltz', 'beats': [1, 2, 2]},
    {'name': 'Prog Rock 7/8', 'beats': [1, 2, 1, 2, 1, 2, 2]}
]

# --- STATE MANAGEMENT ---
state = {
    "bpm": 120,
    "current_idx": 0,
    "playing": False
}

def save_state():
    with open(SAVE_FILE, 'w') as f:
        json.dump({"bpm": state["bpm"], "idx": state["current_idx"]}, f)

def load_state():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
            state["bpm"] = data.get("bpm", 120)
            state["current_idx"] = data.get("idx", 0)

load_state()  # Run on boot

# --- TAP TEMPO LOGIC ---
tap_times = []

def handle_tap():
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
        if 30 < new_bpm < 300:  # Sanity check
            state["bpm"] = new_bpm
            print(f"Tap Tempo: {new_bpm} BPM")
            save_state()

def handle_start():
    state["playing"] = not state["playing"]
    if state["playing"]:
        global tap_times
        tap_times = []  # Reset taps on start
        led_status.on()
        print(f"Started: {PATTERNS[state['current_idx']]['name']} at {state['bpm']} BPM")
    else:
        led_status.off()
        print("Stopped")

def next_pattern():
    state["current_idx"] = (state["current_idx"] + 1) % len(PATTERNS)
    save_state()
    led_status.blink(on_time=0.1, n=3)
    print(f"Pattern: {PATTERNS[state['current_idx']]['name']}")

# Wire up buttons
btn_tap.when_pressed = handle_tap
btn_start.when_pressed = handle_start
btn_next.when_pressed = next_pattern

# --- SEQUENCER ENGINE ---
def run_sequencer():
    step = 0
    while True:
        if state["playing"]:
            pattern = PATTERNS[state["current_idx"]]["beats"]
            beat_type = pattern[step % len(pattern)]
            
            # Determine Note
            note = None
            if beat_type == 1:
                note = SOUNDS['accent']
                is_accent = True
            elif beat_type == 2:
                note = SOUNDS['click']
                is_accent = False
            # elif beat_type == 0: note = SOUNDS['subdiv']  # Optional
            
            # Fire MIDI
            if note and outport:
                outport.send(mido.Message('note_on', note=note, velocity=110, channel=MIDI_CHANNEL))
                time.sleep(0.05)
                outport.send(mido.Message('note_off', note=note, velocity=0, channel=MIDI_CHANNEL))
            
            # LED Pulse
            if note:
                led_beat.on()
                time.sleep(0.15 if is_accent else 0.05)
                led_beat.off()
            
            # Calculate sleep based on BPM and Pattern Resolution
            sleep_time = 60.0 / state["bpm"]
            if len(pattern) > 4:
                sleep_time /= 2  # Speed up for eighth notes
            
            # Accurate timing (subtract LED time)
            remaining_time = sleep_time - (0.15 if (note and is_accent) else 0.05)
            if remaining_time > 0:
                time.sleep(remaining_time)
            
            step += 1
        else:
            time.sleep(0.1)

# --- MIDI SETUP ---
outport = None
try:
    ports = mido.get_output_names()
    # Look for a USB MIDI device
    matching = [p for p in ports if "USB" in p or "Alesis" in p]
    port_name = matching[0] if matching else ports[0]
    outport = mido.open_output(port_name)
    print(f"Connected to {port_name}")
except Exception as e:
    print(f"MIDI Error: {e}. Running in dummy mode.")

# Start Engine
threading.Thread(target=run_sequencer, daemon=True).start()

print(f"Drum Assistant Ready! Pattern: {PATTERNS[state['current_idx']]['name']}, BPM: {state['bpm']}")
print("Red button: Start/Stop, Blue button: Tap Tempo, White button: Next Pattern")

# Keep alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down...")
    if state["playing"]:
        led_status.off()
    led_beat.off()
