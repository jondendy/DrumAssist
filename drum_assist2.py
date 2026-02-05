# drum_assist2.py
import time

try:
    from gpiozero import Button, LED
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    print("GPIO not available - buttons/LEDs disabled")

import engine

# GPIO pins (same as your current file)
PIN_START = 17   # Red
PIN_TAP = 27     # Blue
PIN_NEXT = 22    # White
PIN_BEAT_LED = 18
PIN_STATUS_LED = 23

led_beat = None
led_status = None


def beat_led_callback(beat_type, is_accent):
    # Only show LED when a real beat/click happens
    if not GPIO_AVAILABLE or led_beat is None:
        return
    if beat_type in (1, 2):
        led_beat.on()
        time.sleep(0.15 if is_accent else 0.05)
        led_beat.off()


def set_status_led(on: bool):
    if not GPIO_AVAILABLE or led_status is None:
        return
    if on:
        led_status.on()
    else:
        led_status.off()


if GPIO_AVAILABLE:
    btn_start = Button(PIN_START)
    btn_tap = Button(PIN_TAP)
    btn_next = Button(PIN_NEXT)

    led_beat = LED(PIN_BEAT_LED)
    led_status = LED(PIN_STATUS_LED)

    def _startstop():
        engine.handle_start()
        set_status_led(engine.state["playing"])

    btn_start.when_pressed = _startstop
    btn_tap.when_pressed = engine.handle_tap
    btn_next.when_pressed = engine.next_button_action

if __name__ == "__main__":
    engine.start_engine(beat_callback=beat_led_callback)
    st = engine.get_status()
    print(f"Drum Assistant Ready! Pattern: {st['pattern_name']}, BPM: {st['bpm']}")
    print("Red button: Start/Stop, Blue button: Tap Tempo, White button: Next Pattern")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        set_status_led(False)
        if led_beat:
            led_beat.off()
