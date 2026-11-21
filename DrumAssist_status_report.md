# DrumAssist technical status report

Source of truth: `github.com/jondendy/DrumAssist`, HEAD `3db06f4` ("Import sys and set MIDI backend for Windows if present"). The clone is shallow (depth 1), so earlier history is not available. Checked by reading all files and running `py_compile` on each Python file (all pass). Nothing has been run on hardware, and the repo has no tests.

Note: the earlier draft report in the uploaded file said the code could not be retrieved and treated `drummer_assist.py` as the main entry point. Both are out of date. The repo has five Python files and `drummer_assist.py` is not the main path.

## 1. Hardware

| Item | Documented or found in code | Status |
|---|---|---|
| Target sound module | Alesis SamplePad Pro (code matches "USB" or "Alesis" in MIDI port name) | Not verified on hardware |
| Host for hardware mode | Raspberry Pi Zero, USB OTG adapter to the SamplePad (README) | Not verified |
| Laptop / Dell host | Laptop mode via keyboard; Windows MIDI backend set in `engine.py` | Last run believed on an old Dell (per owner); not verified |
| Hardware buttons | Start/stop, tap tempo, next pattern (`drum_assist2.py`) | Pin map disagrees with README (see section 6) |
| Hardware LEDs | Beat LED and status LED (`drum_assist2.py`) | Pin map disagrees with README |
| Phone / web client | Any browser on the Pi's Wi-Fi, via `drum_assist_web.py` port 5000 | Not verified |

## 2. Software and files

| File | Role | Status |
|---|---|---|
| `engine.py` | Shared core: patterns (with optional fills), sequencer thread, MIDI output, tap tempo, BPM and pattern state, saving settings | Main logic. Compiles. Has fill support, pattern-file loading and the Windows backend, which the older transcript code lacks |
| `drum_assist2.py` | Raspberry Pi front end: GPIO buttons and LEDs | Calls `engine.start_engine`. Has no web server |
| `drum_assist_web.py` | Flask web UI on port 5000, with pattern editor, fills, BPM controls | Uses `engine` correctly. Has the keyboard bug in section 6 |
| `drum_assist_laptop.py` | Terminal and keyboard front end | Uses `engine`. Needs the `keyboard` library, which is not in `requirements.txt` |
| `drummer_assist.py` | Older standalone script that does GPIO plus Flask on port 80 | Duplicates the engine. Not part of the current design. Candidate for removal or archiving |
| `ASCII..txt` | Splash art | Not code. Its hostname (`drumhelper.local`) differs from the README (`drumpi.local`) |
| `requirements.txt` | Pinned dependencies | See section 5 |
| `README.md` | Install, run, systemd and hotspot notes | Partly out of date (pins, ports) |

## 3. File paths (runtime)

- Repo root: wherever cloned, e.g. `/home/pi/DrumAssist` (README's systemd example)
- `dh2_settings.json`: saved BPM and pattern index, written to the current working directory
- `patterns.json`: pattern editor output, written to the current working directory. Not present in the repo. It is created when a pattern is saved.

Both files are relative paths. They only land in the repo folder if the program is started from there. The systemd unit sets `WorkingDirectory`, which handles that.

## 4. Commands

```bash
# Clone and install
git clone https://github.com/jondendy/DrumAssist.git
cd DrumAssist
pip3 install -r requirements.txt

# Pi with GPIO buttons and LEDs (no web UI)
python3 drum_assist2.py

# Pi or any machine, web UI on port 5000
python3 drum_assist_web.py          # then open http://<host>:5000

# Laptop terminal and keyboard mode
python3 drum_assist_laptop.py

# Check MIDI output ports
python3 -c "import mido; print(mido.get_output_names())"
```

Port 80 needs root (`sudo`). The README's hotspot address `192.168.4.1` has no port, so it expects port 80, which the current web app does not serve.

## 5. Configuration and dependencies

- MIDI channel: 10 (`MIDI_CHANNEL = 9`, zero-based)
- Sounds (note numbers): click 37 (side stick), accent 49 (crash), subdivision 42 (hi-hat, currently not sent)
- BPM range: 30 to 300. Default 85 on startup.
- Patterns (built-in): 4/4 Basic, 4/4 Subdivisions, 6/8 Feel, 3/4 Waltz, Prog Rock 7/8. Tokens: `A` accent, `x` click, `.` rest. Fill, if set, must be the same length as its main pattern.
- Fill: queued at the next bar, up to 2 bars (`FILL_MAX_BARS`)
- Windows: `mido.set_backend('mido.backends.winmm')` is set at import time
- `requirements.txt` lists: Flask 3.0.0, waitress 3.0.0, pynput 1.7.6, mido 1.3.0, python-rtmidi 1.5.8, gpiozero 2.0.1, RPi.GPIO 0.7.1

Dependency issues:
- `pynput` is not imported anywhere, and needs an X display on Linux. Remove it.
- `waitress` is listed but the app runs Flask's built-in server. Either use waitress or remove it.
- `keyboard` (used by laptop mode) is missing from the list.
- `python-rtmidi` may need compiling on a Pi Zero. Expect a long install. (Not tested.)

## 6. Known issues (from reading the code)

1. **Keyboard shortcuts hijack the pattern editor (`drum_assist_web.py`).** The page listens for Space and Enter on the whole document. Typing a pattern there fires tap and start/stop, and you cannot enter spaces or new lines. High priority for the editor.
2. **Hardware accent lands late (`drum_assist2.py`).** The LED callback sleeps 150 ms for accents and 50 ms for clicks, and it runs before the MIDI note is sent. The downbeat sounds about 100 ms after the clicks. This matters for an in-ear click.
3. **GPIO pin map disagrees with the README.** Code: start 17, tap 27, next 22, beat LED 18, status LED 23. README: tap 17, start 27, status LED 22, beat LED 23. Wiring must match the code, or the README must change.
4. **Port mismatch.** The README hotspot address `192.168.4.1` implies port 80. The web app uses port 5000, and the systemd example runs it on port 5000 as user `pi`. Either put the URL with `:5000` or change the port and handle the port-80 permission.
5. **No single program for hardware buttons plus phone web UI.** `drum_assist2.py` (buttons) and `drum_assist_web.py` (phone) each start their own engine. Running both at once would try to open the MIDI port twice and send double notes. Needs one entry point.
6. **Phone flash timing.** The browser polls `/status` every 100 ms and flashes when the beat counter changes. Over Wi-Fi this will jitter. The README's claim of "accurate visual syncing" is not met.
7. **No authentication.** Anyone on the Pi's network can change BPM and patterns, and the GET routes for toggle and pattern make it easy to trigger by accident.
8. **`drummer_assist.py` is a second engine.** It binds GPIO 17 to tap and 27 to start, which is the reverse of `drum_assist2.py`. It has no lock around shared state and runs on port 80.
9. **Earlier code in the uploaded chat is older than the repo.** Pasting those files would drop fills, pattern-file loading, the Windows MIDI backend and the pattern editor. Its advice to start `run_sequencer` in a separate thread as well as via `start_engine` would start two sequencers and double every note. Do not paste it over the repo.

## 7. Next steps

1. Confirm the physical wiring (section 6, item 3) and fix the README or the code to match.
2. Fix the editor key bug (item 1) and the LED delay (item 2). Both are small changes.
3. Decide on one Pi entry point that runs buttons, LEDs and the web UI together (item 5). Retire or archive `drummer_assist.py`.
4. Clean up `requirements.txt` (section 5) and the README (ports, pins, hotspot).
5. Bench test with the SamplePad: run `python3 -c "import mido; print(mido.get_output_names())"`, check that each pattern sends the expected notes, and time the click against a metronome app.
6. Decide later whether the phone flash should use server-sent events, or send a start time and BPM and let each phone run its own flash on a synced clock (item 6).
7. Add a `STATUS.md` in the repo root and update it after each change.
