# drum_assist2.py - Raspberry Pi entry point.
# One process: GPIO buttons + LEDs + the phone web UI (drum_assist_web.py), sharing one engine.
import threading
import time

try:
    from gpiozero import Button, LED
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    print("GPIO not available - buttons/LEDs disabled, web UI still runs")

import engine
from drum_assist_web import app

# GPIO pins (BCM numbering, as in the code before the merge)
PIN_START = 17   # Red: start/stop
PIN_TAP = 27     # Blue: tap tempo
PIN_NEXT = 22    # White: next pattern (stopped) / request fill (playing)
PIN_BEAT_LED = 18
PIN_STATUS_LED = 23

led_beat = None
led_status = None


def beat_led_callback(beat_type, is_accent):
    # Runs on the sequencer thread just before the MIDI note goes out,
    # so it must not block. blink(background=True) returns immediately.
    if led_beat is None or beat_type not in (1, 2):
        return
    led_beat.blink(on_time=0.15 if is_accent else 0.05, off_time=0, n=1, background=True)


def _status_led_loop():
    # Keep the status LED in step with play/stop, whichever source changed it
    # (button, phone UI or keyboard).
    last = None
    while True:
        playing = engine.state["playing"]
        if playing != last and led_status is not None:
            if playing:
                led_status.on()
            else:
                led_status.off()
            last = playing
        time.sleep(0.1)


if GPIO_AVAILABLE:
    btn_start = Button(PIN_START)
    btn_tap = Button(PIN_TAP)
    btn_next = Button(PIN_NEXT)

    led_beat = LED(PIN_BEAT_LED)
    led_status = LED(PIN_STATUS_LED)

    btn_start.when_pressed = engine.handle_start
    btn_tap.when_pressed = engine.handle_tap
    btn_next.when_pressed = engine.next_button_action


def main():
    engine.start_engine(beat_callback=beat_led_callback)
    if GPIO_AVAILABLE:
        threading.Thread(target=_status_led_loop, daemon=True).start()

    st = engine.get_status()
    print(f"DrumAssist ready! Pattern: {st['pattern_name']}, BPM: {st['bpm']}")
    print("Red: start/stop, Blue: tap tempo, White: next pattern (or fill while playing)")
    print("Phone UI: http://drumpi.local:5000 or http://<pi-ip>:5000")

    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        if GPIO_AVAILABLE:
            led_status.off()
            led_beat.off()


if __name__ == "__main__":
    main()
