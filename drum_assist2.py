import mido
import time
import threading
import json
import os
from gpiozero import Button, LED

# --- CONFIG ---
SAVE_FILE = "dh2_settings.json"
# Physical Pins: 11, 13, 15 for buttons. 12, 16 for LEDs.
btn_start = Button(17) # Red
btn_tap   = Button(27) # Blue
btn_next  = Button(22) # White
led_beat   = LED(18) 
led_status = LED(23)

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

load_state() # Run on boot

# --- LOGIC ---
def handle_tap():
    # ... (same tap logic as before) ...
    save_state() # Save whenever you change it
    import json

    def save_drum_settings(bpm, pattern_idx):
        settings = {'bpm': bpm, 'pattern': pattern_idx}
        with open('/home/pi/drum_helper_v2.json', 'w') as f:
            json.dump(settings, f)
        print("Settings saved for next time!")

# Call this inside your 'handle_tap' or 'next_pattern' functions!


def next_pattern():
    state["current_idx"] = (state["current_idx"] + 1) % len(patterns)
    save_state()
    led_status.blink(on_time=0.1, n=3)

# --- SEQUENCER ENGINE ---
def run_sequencer():
    step = 0
    while True:
        if state["playing"]:
            pattern = patterns[state["current_idx"]]["beats"]
            is_downbeat = (step % len(pattern) == 0)
            if is_downbeat:

            # Stronger flash and higher MIDI note for the "1"
                note = 39 
                led_beat.on()
                time.sleep(0.15) # Longer flash
            else:
                 # Standard click
                 note = 37
                 led_beat.on()
                 time.sleep(0.05) # Short sharp flash

            led_beat.off()

            
            # MIDI Note selection
            note = 39 if is_accent else 37 
            
            # Fire MIDI
            if outport:
                outport.send(mido.Message('note_on', note=note, velocity=100, channel=9))
            
            # LED Pulse
            led_beat.on()
            time.sleep(0.15 if is_accent else 0.05)
            led_beat.off()
            
            # Accurate timing
            time.sleep((60.0 / state["bpm"]) - 0.1)
            step += 1
        else:
            time.sleep(0.1)

# Initialize
try:
    outport = mido.open_output(mido.get_output_names()[0])
except:
    outport = None

threading.Thread(target=run_sequencer, daemon=True).start()
