# engine.py
import time
import threading
import json
import os

import mido

SAVE_FILE = "dh2_settings.json"
MIDI_CHANNEL = 9  # Channel 10 in MIDI terms (0-15)
PATTERNS_FILE = "patterns.json"
FILL_MAX_BARS = 2

# Alesis SamplePad Note Numbers (GM-ish)
SOUNDS = {
    "click": 37,    # Side Stick
    "accent": 49,   # Crash Cymbal (or reassign on device)
    "subdiv": 42,   # Closed Hi-Hat (optional)
}

# 1 = Accent, 2 = Click, 0 = Rest/Subdivision
PATTERNS = [
    {"name": "4/4 Basic",         "beats": [1, 2, 2, 2]},
    {"name": "4/4 Subdivisions",  "beats": [1, 0, 2, 0, 2, 0, 2, 0]},
    {"name": "6/8 Feel",          "beats": [1, 2, 2, 1, 2, 2]},
    {"name": "3/4 Waltz",         "beats": [1, 2, 2]},
    {"name": "Prog Rock 7/8",     "beats": [1, 2, 1, 2, 1, 2, 2]},
]

_lock = threading.Lock()
_outport = None
_thread_started = False

state = {
    "bpm": 85,
    "current_idx": 4,
    "playing": False,
    "fill_pending_bars": 0,  # requested fills (queued to start at next bar)
    "fill_active_bars": 0,   # fills currently being played (counts bars remaining)

    # karaoke / UI helpers
    "step": 0,
    "pattern_changed": False,
    "last_beat_type": 0,
    "beat_count": 0,
}

_tap_times = []

def _norm_lines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")

def parse_rhythm(text: str):
    """
    Multi-line friendly parser.
    Allowed tokens (spaces and '|' ignored):
      A or 1  -> accent (1)
      x or 2  -> click  (2)
      . or 0 or - -> rest (0)
    Any other char is ignored (so you can add labels if you want).
    """
    text = _norm_lines(text)
    out = []
    for ch in text:
        if ch in (" ", "\t", "\n", "|"):
            continue
        if ch in ("A", "a", "1"):
            out.append(1)
        elif ch in ("x", "X", "2"):
            out.append(2)
        elif ch in (".", "0", "-"):
            out.append(0)
        else:
            # ignore unknown characters
            continue
    return out

def rhythm_to_text(beats):
    # Single-line display (UI can still be multiline; this is just a formatter)
    return " ".join("A" if b == 1 else ("x" if b == 2 else ".") for b in beats)

def patterns_default():
    # Convert your in-code PATTERNS into file format with optional fill
    return [
        {"name": p["name"], "beats": p["beats"], "fill": p.get("fill")}
        for p in PATTERNS
    ]

def save_patterns():
    try:
        with _lock:
            data = patterns_default()
        with open(PATTERNS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving patterns: {e}")

def load_patterns():
    global PATTERNS
    if not os.path.exists(PATTERNS_FILE):
        return
    try:
        with open(PATTERNS_FILE, "r") as f:
            data = json.load(f)
        # validate minimally
        cleaned = []
        for p in data:
            name = str(p.get("name", "Pattern"))
            beats = p.get("beats", [])
            fill = p.get("fill", None)
            if not isinstance(beats, list) or not beats:
                continue
            beats = [int(x) for x in beats]
            if fill is not None:
                if not isinstance(fill, list) or len(fill) != len(beats):
                    fill = None
                else:
                    fill = [int(x) for x in fill]
            cleaned.append({"name": name, "beats": beats, "fill": fill})
        if cleaned:
            PATTERNS = cleaned
            print(f"Loaded patterns from {PATTERNS_FILE}")
    except Exception as e:
        print(f"Error loading patterns: {e}")

def update_pattern_from_text(idx: int, name: str, beats_text: str, fill_text: str):
    idx = int(idx)
    if not (0 <= idx < len(PATTERNS)):
        raise ValueError("Bad pattern index")

    beats = parse_rhythm(beats_text)
    if not beats:
        raise ValueError("Main rhythm is empty (use A/x/.)")

    fill_text = (fill_text or "").strip()
    fill = parse_rhythm(fill_text) if fill_text else None

    # Keep life simple: fill must match main length
    if fill is not None and len(fill) != len(beats):
        raise ValueError(f"Fill length ({len(fill)}) must match main length ({len(beats)})")

    with _lock:
        PATTERNS[idx]["name"] = (name or PATTERNS[idx]["name"]).strip() or PATTERNS[idx]["name"]
        PATTERNS[idx]["beats"] = beats
        PATTERNS[idx]["fill"] = fill
        state["pattern_changed"] = True  # forces step reset cleanly

    save_patterns()

def save_state():
    with _lock:
        data = {"bpm": state["bpm"], "idx": state["current_idx"]}
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving state: {e}")


def load_state():
    if not os.path.exists(SAVE_FILE):
        return
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        with _lock:
            state["bpm"] = int(data.get("bpm", state["bpm"]))
            state["current_idx"] = int(data.get("idx", state["current_idx"]))
    except Exception as e:
        print(f"Error loading state: {e}")


def init_midi():
    global _outport
    try:
        ports = mido.get_output_names()
        if not ports:
            print("MIDI: No output ports found (dummy mode).")
            _outport = None
            return

        matching = [p for p in ports if ("USB" in p) or ("Alesis" in p)]
        port_name = matching[0] if matching else ports[0]
        _outport = mido.open_output(port_name)
        print(f"MIDI: Connected to {port_name}")
    except Exception as e:
        print(f"MIDI Error: {e}. Running in dummy mode.")
        _outport = None


def _send_note(note, velocity=110, on_time=0.05):
    if _outport is None:
        return
    try:
        _outport.send(mido.Message("note_on", note=note, velocity=velocity, channel=MIDI_CHANNEL))
        time.sleep(on_time)
        _outport.send(mido.Message("note_off", note=note, velocity=0, channel=MIDI_CHANNEL))
    except Exception as e:
        print(f"MIDI send error: {e}")


def set_bpm(new_bpm: int):
    if not (30 <= int(new_bpm) <= 300):
        return
    with _lock:
        state["bpm"] = int(new_bpm)
    save_state()


def adjust_bpm(delta: int):
    with _lock:
        bpm = state["bpm"]
    set_bpm(bpm + int(delta))


def set_pattern(idx: int):
    idx = int(idx)
    if not (0 <= idx < len(PATTERNS)):
        return
    with _lock:
        state["current_idx"] = idx
        state["pattern_changed"] = True
    save_state()
    print(f"Pattern: {PATTERNS[idx]['name']}")

def request_fill(bars: int = 1):
    bars = int(bars)
    if bars < 1:
        return
    bars = min(FILL_MAX_BARS, bars)

    with _lock:
        if not state["playing"]:
            return
        # queue to start at the next bar boundary
        state["fill_pending_bars"] = min(FILL_MAX_BARS, state["fill_pending_bars"] + bars)

def next_button_action():
    # Stopped -> next pattern (current behavior)
    # Playing -> request 1 bar fill (press twice to request 2 bars)
    with _lock:
        playing = state["playing"]
    if playing:
        request_fill(1)
    else:
        next_pattern()


def next_pattern():
    with _lock:
        idx = state["current_idx"]
    set_pattern((idx + 1) % len(PATTERNS))


def toggle_play():
    global _tap_times
    with _lock:
        state["playing"] = not state["playing"]
        playing = state["playing"]
    if playing:
        _tap_times = []
    return playing


def handle_start():
    playing = toggle_play()
    with _lock:
        name = PATTERNS[state["current_idx"]]["name"]
        bpm = state["bpm"]
    if playing:
        print(f"Started: {name} at {bpm} BPM")
    else:
        print("Stopped")


def handle_tap():
    global _tap_times
    now = time.time()

    if _tap_times and (now - _tap_times[-1] > 2.0):
        _tap_times = []

    _tap_times.append(now)
    _tap_times = _tap_times[-4:]

    if len(_tap_times) >= 2:
        intervals = [t - s for s, t in zip(_tap_times, _tap_times[1:])]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval > 0:
            new_bpm = int(60.0 / avg_interval)
            if 30 < new_bpm < 300:
                set_bpm(new_bpm)
                print(f"Tap Tempo: {new_bpm} BPM")


def get_status():
    with _lock:
        return {
            "bpm": state["bpm"],
            "playing": state["playing"],
            "current_idx": state["current_idx"],
            "pattern_name": PATTERNS[state["current_idx"]]["name"],
            "step": state.get("step", 0),
            "pattern_len": len(PATTERNS[state["current_idx"]]["beats"]),
            "last_beat_type": state.get("last_beat_type", 0),
            "beat_count": state.get("beat_count", 0),
            "has_fill": bool(PATTERNS[state["current_idx"]].get("fill")),
            "fill_pending_bars": state.get("fill_pending_bars", 0),
            "fill_active_bars": state.get("fill_active_bars", 0),
        }


def run_sequencer(beat_callback=None):
    """
    beat_callback(beat_type, is_accent) -> optional hook for LEDs/terminal visuals.
    """
    step = 0
    last_beat_time = time.time()

    while True:
        with _lock:
            playing = state["playing"]
            bpm = state["bpm"]
            idx = state["current_idx"]
            changed = state["pattern_changed"]

        if not playing:
            time.sleep(0.05)
            continue

        if changed:
            step = 0
            with _lock:
                state["step"] = 0
                state["pattern_changed"] = False

        p = PATTERNS[idx]
        main = p["beats"]
        fill = p.get("fill")

        # At bar boundary (step==0), decide whether to start/continue a fill
        if step % len(main) == 0:
            with _lock:
                if state.get("fill_active_bars", 0) > 0:
                    # continue fill, decrement bar count now that a new bar is starting
                    state["fill_active_bars"] -= 1
                # if no active fill bars remaining, start queued fill
                if state.get("fill_active_bars", 0) <= 0 and state.get("fill_pending_bars", 0) > 0:
                    state["fill_active_bars"] = state["fill_pending_bars"]
                    state["fill_pending_bars"] = 0

        with _lock:
            fill_active = state.get("fill_active_bars", 0)

        use_fill = (fill_active > 0) and (fill is not None)
        pattern = fill if use_fill else main
        beat_type = pattern[step % len(pattern)]
        
        note = None
        is_accent = False
        if beat_type == 1:
            note = SOUNDS["accent"]
            is_accent = True
        elif beat_type == 2:
            note = SOUNDS["click"]
        elif beat_type == 0:
            note = None  # set to SOUNDS["subdiv"] if you want audible subdivisions

        with _lock:
            state["last_beat_type"] = beat_type
            state["beat_count"] = step
            state["step"] = step % len(pattern)

        if beat_callback is not None:
            try:
                beat_callback(beat_type, is_accent)
            except Exception as e:
                print(f"beat_callback error: {e}")

        if note is not None:
            _send_note(note, velocity=110, on_time=0.05)

        # timing
        sleep_time = 60.0 / max(30, bpm)
        if len(pattern) > 4:
            sleep_time /= 2  # simple heuristic for 8th-note grids

        elapsed = time.time() - last_beat_time
        remaining = sleep_time - elapsed
        if remaining > 0:
            time.sleep(remaining)
        last_beat_time = time.time()

        step = (step + 1) % len(pattern)


def start_engine(beat_callback=None):
    global _thread_started
    if _thread_started:
        return
    load_state()
    load_patterns()
    init_midi()
    t = threading.Thread(target=run_sequencer, args=(beat_callback,), daemon=True)
    t.start()
    _thread_started = True
