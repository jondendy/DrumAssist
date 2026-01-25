# DrumAssist

Simple metronomic sample generation to drive sample pad or drum machine for in-ear click track.

Designed for live performance and practice with flexible deployment options:
- **Raspberry Pi Zero** with hardware buttons and LEDs
- **Laptop mode** with keyboard controls and terminal feedback
- **Web interface** with browser-based controls and visual metronome

## Features

- Tap tempo functionality
- Multiple rhythm patterns (4/4, 6/8, 7/8, subdivisions)
- Real-time BPM display
- MIDI output support (targets Alesis SamplePad Pro)
- Multi-device support with automatic GPIO fallback
- Keyboard shortcuts: SPACE (tap), ENTER (toggle)
- High-performance polling for accurate visual syncing

## Installation

### Initial Setup

```bash
# Install git if not already installed (Raspberry Pi)
sudo apt-get update
sudo apt-get install git

# Clone the repository
git clone https://github.com/jondendy/DrumAssist.git
cd DrumAssist

# Install Python dependencies
pip3 install -r requirements.txt
```

### Updating to Latest Version

To pull the latest updates from the repository:

```bash
cd DrumAssist
git pull origin main
pip3 install -r requirements.txt  # Update dependencies if changed
```

## Usage

### Option 1: Raspberry Pi with Hardware (drum_assist2.py)

Full hardware mode with GPIO buttons and LEDs.

**Hardware Setup:**
- GPIO 17: Tap Tempo button (connect to GND)
- GPIO 27: Start/Stop button (connect to GND)
- GPIO 22: Status LED
- GPIO 23: Beat LED
- USB OTG adapter for MIDI connection to Alesis SamplePad

**Run:**
```bash
python3 drum_assist2.py
```

**Note:** Automatically falls back to laptop mode if GPIO is unavailable.

### Option 2: Laptop Mode (drum_assist_laptop.py)

Terminal-based with keyboard controls and visual feedback.

**Controls:**
- **SPACEBAR**: Tap tempo
- **ENTER**: Start/Stop
- **ESC**: Exit

**Run:**
```bash
python3 drum_assist_laptop.py
```

**Visual Feedback:** Screen flashes in terminal for beat indication.

### Option 3: Web Interface (drum_assist_web.py)

Browser-based control with screen flashes.

**Run:**
```bash
python3 drum_assist_web.py
```

Then open your browser to:
- **Local:** http://localhost:5000
- **Network:** http://[your-ip]:5000

**Features:**
- Pattern selection dropdown
- Start/Stop button
- Tap tempo functionality (click anywhere or press SPACE)
- Full-screen visual metronome with color flashes
- Real-time BPM display

## Headless Raspberry Pi Setup

To run automatically on boot:

```bash
sudo nano /etc/systemd/system/drumassist.service
```

Add:
```ini
[Unit]
Description=DrumAssist Metronome
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/DrumAssist
ExecStart=/usr/bin/python3 /home/pi/DrumAssist/drum_assist_web.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable drumassist.service
sudo systemctl start drumassist.service
```

## Wi-Fi Hotspot Setup (Optional)

For gigs/practice without existing Wi-Fi:

```bash
sudo apt-get install hostapd dnsmasq
# Or use RaspAP: https://raspap.com/
```

Connect your phone/tablet to the Pi's hotspot and access the web interface at `192.168.4.1` or `drumpi.local`.

## Patterns

- **4/4 Basic**: Standard quarter notes with accent on 1
- **4/4 Subdivisions**: Eighth note subdivisions
- **6/8 Feel**: Two groups of three
- **3/4 Waltz**: Three quarter notes
- **7/8 Prog Rock**: 2+2+3 grouping

## Dependencies

- Flask (web interface)
- waitress (production WSGI server)
- mido (MIDI handling)
- python-rtmidi (MIDI backend)
- gpiozero (Raspberry Pi GPIO)
- RPi.GPIO (Raspberry Pi hardware)
- pynput (laptop keyboard/mouse support)

## Troubleshooting

**MIDI Not Working:**
- Check `mido.get_output_names()` to list available devices
- Ensure USB MIDI device is connected
- On Pi: `sudo apt-get install python3-rtmidi`

**GPIO Errors on Laptop:**
- Use `drum_assist_laptop.py` or `drum_assist_web.py` instead
- `drum_assist2.py` automatically falls back to non-GPIO mode

**Web Interface Port 80 Access Denied:**
- Run with sudo: `sudo python3 drum_assist_web.py`
- Or use port 5000 (default) without sudo

## License

Open source - feel free to modify and adapt for your needs.

## Author

jon@dendy.me.uk
