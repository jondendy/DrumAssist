#!/usr/bin/env python3
"""
Drum Assistant - Laptop Mode
Provides keyboard-based control and terminal visual feedback when GPIO is not available.
Falls back gracefully from hardware buttons to keyboard input.

Controls:
- SPACE: Tap tempo
- ENTER: Start/Stop
- N: Next pattern
- Q: Quit
"""

import mido
import time
import threading
import json
import os
import sys
from collections import deque

# Try to import GPIO, but continue without it
try:
    from gpiozero import Button, LED
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    print("GPIO not available - running in LAPTOP MODE")
    print("Controls: SPACE=tap, ENTER=start/stop, N=next pattern, Q=quit")

# Try keyboard input library
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("Install 'keyboard' library for better controls: pip install keyboard")
    print("Falling back to simple input mode")

# --- CONFIG ---
SAVE_FILE = "dh2_settings.json"

# --- MIDI CONFIGURATION ---
MIDI_CHANNEL = 9  # Channel 10 in MIDI terms (0-15)
SOUNDS = {
    'click': 37,   # Side Stick
    'accent': 49,  # Crash Cymbal
    'subdiv': 42   # Closed Hi-Hat
}

# --- PATTERNS ---
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
    "playing": False,
    "mode": "laptop" if not GPIO_AVAILABLE else "hardware"
}

def save_state():
    try:
        with open(SAVE_FILE, 'w') as f:
            json.dump({"bpm": state["bpm"], "idx": state["current_idx"]}, f)
    except Exception as e:
        print(f"Could not save state: {e}")

def load_state():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                state["bpm"] = data.get("bpm", 120)
                state["current_idx"] = data.get("idx", 0)
        except Exception as e:
            print(f"Could not load state: {e}")

load_state()

# --- TAP TEMPO LOGIC ---
tap_times = []

def handle_tap():
    global tap_times
    now = time.time()
    if tap_times and (now - tap_times[-1] > 2.0):
        tap_times = []
    
    tap_times.append(now)
    tap_times = tap_times[-4:]
    
    if len(tap_times) >= 2:
        intervals = [t - s for s, t in zip(tap_times, tap_times[1:])]
        avg_interval = sum(intervals) / len(intervals)
        new_bpm = int(60.0 / avg_interval)
        if 30 < new_bpm < 300:
            state["bpm"] = new_bpm
            print(f"\r\033[K🎵 Tap Tempo: {new_bpm} BPM", end='', flush=True)
            save_state()

def handle_start():
    state["playing"] = not state["playing"]
    if state["playing"]:
        global tap_times
        tap_times = []
        if GPIO_AVAILABLE:
            led_status.on()
        status = "▶️  PLAYING" if state["mode"] == "laptop" else "Started"
        print(f"\r\033[K{status}: {PATTERNS[state['current_idx']]['name']} @ {state['bpm']} BPM")
    else:
        if GPIO_AVAILABLE:
            led_status.off()
        print(f"\r\033[K⏸  STOPPED")

def next_pattern():
    state["current_idx"] = (state["current_idx"] + 1) % len(PATTERNS)
    save_state()
    if GPIO_AVAILABLE:
        led_status.blink(on_time=0.1, n=3)
    print(f"\r\033[K🔄 Pattern: {PATTERNS[state['current_idx']]['name']}")

# --- HARDWARE SETUP (if available) ---
if GPIO_AVAILABLE:
    btn_start = Button(17)
    btn_tap = Button(27)
    btn_next = Button(22)
    led_beat = LED(18)
    led_status = LED(23)
    
    btn_tap.when_pressed = handle_tap
    btn_start.when_pressed = handle_start
    btn_next.when_pressed = next_pattern

# --- KEYBOARD SETUP (laptop mode) ---
if KEYBOARD_AVAILABLE:
    keyboard.on_press_key('space', lambda _: handle_tap())
    keyboard.on_press_key('enter', lambda _: handle_start())
    keyboard.on_press_key('n', lambda _: next_pattern())

# --- VISUAL FEEDBACK (laptop mode) ---
def visual_beat_indicator(is_accent=False):
    """Show visual beat in terminal"""
    if state["mode"] == "laptop":
        if is_accent:
            print("\r\033[K▮▮▮▮▮ 🥁 BEAT 1 ▮▮▮▮▮", end='', flush=True)
        else:
            print("\r\033[K▯▯ • ▯▯", end='', flush=True)
    
    if GPIO_AVAILABLE:
        led_beat.on()
        time.sleep(0.15 if is_accent else 0.05)
        led_beat.off()

# --- SEQUENCER ENGINE ---
def run_sequencer():
    step = 0
    last_beat_time = time.time()
    
    while True:
        if state["playing"]:
            pattern = PATTERNS[state["current_idx"]]["beats"]
            beat_type = pattern[step % len(pattern)]
            
            note = None
            is_accent = False
            
            if beat_type == 1:
                note = SOUNDS['accent']
                is_accent = True
            elif beat_type == 2:
                note = SOUNDS['click']
                is_accent = False
            
            # Fire MIDI
            if note and outport:
                try:
                    outport.send(mido.Message('note_on', note=note, velocity=110, channel=MIDI_CHANNEL))
                    time.sleep(0.01)
                    outport.send(mido.Message('note_off', note=note, velocity=0, channel=MIDI_CHANNEL))
                except Exception as e:
                    print(f"\r\033[KMIDI error: {e}")
            
            # Visual feedback
            if note:
                visual_beat_indicator(is_accent)
            
            # Calculate accurate timing
            sleep_time = 60.0 / state["bpm"]
            if len(pattern) > 4:
                sleep_time /= 2
            
            # Compensate for processing time
            elapsed = time.time() - last_beat_time
            remaining = max(0, sleep_time - elapsed)
            time.sleep(remaining)
            
            last_beat_time = time.time()
            step += 1
        else:
            time.sleep(0.1)

# --- MIDI SETUP ---
outport = None
try:
    ports = mido.get_output_names()
    if ports:
        matching = [p for p in ports if "USB" in p or "Alesis" in p]
        port_name = matching[0] if matching else ports[0]
        outport = mido.open_output(port_name)
        print(f"🎹 MIDI: Connected to {port_name}")
    else:
        print("⚠️  No MIDI ports found - visual mode only")
except Exception as e:
    print(f"⚠️  MIDI Error: {e} - visual mode only")

# --- STARTUP ---
print("\n" + "="*60)
print("🥁 DRUM ASSISTANT - {} MODE".format(state["mode"].upper()))
print("="*60)
print(f"Pattern: {PATTERNS[state['current_idx']]['name']}")
print(f"BPM: {state['bpm']}")

if state["mode"] == "laptop":
    if KEYBOARD_AVAILABLE:
        print("\n📋 Keyboard Controls:")
        print("  SPACE  - Tap Tempo")
        print("  ENTER  - Start/Stop")
        print("  N      - Next Pattern")
        print("  Q      - Quit")
    else:
        print("\n📋 Type commands: 'tap', 'start', 'stop', 'next', 'quit'")
else:
    print("\n🔘 Hardware buttons active")
    print("  Red    - Start/Stop")
    print("  Blue   - Tap Tempo")
    print("  White  - Next Pattern")

print("="*60 + "\n")

# Start sequencer
threading.Thread(target=run_sequencer, daemon=True).start()

# --- MAIN LOOP ---
try:
    if KEYBOARD_AVAILABLE:
        # Use keyboard library
        print("Ready! Press keys to control...\n")
        while True:
            if keyboard.is_pressed('q'):
                break
            time.sleep(0.1)
    else:
        # Fallback to simple input
        print("Type commands and press Enter...\n")
        while True:
            try:
                cmd = input("> ").strip().lower()
                if cmd in ['q', 'quit', 'exit']:
                    break
                elif cmd in ['t', 'tap']:
                    handle_tap()
                elif cmd in ['s', 'start', 'stop']:
                    handle_start()
                elif cmd in ['n', 'next']:
                    next_pattern()
                elif cmd == 'help':
                    print("Commands: tap, start/stop, next, quit")
            except EOFError:
                break
except KeyboardInterrupt:
    pass
finally:
    print("\n\n👋 Shutting down...")
    if state["playing"] and GPIO_AVAILABLE:
        led_status.off()
        led_beat.off()
    print("Goodbye!\n")
