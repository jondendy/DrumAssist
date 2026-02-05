#!/usr/bin/env python3
import time
import threading

import engine

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


def visual_beat(beat_type, is_accent):
    # simple terminal flash
    if beat_type == 1:
        print("\r\033[K▮▮▮▮▮ BEAT 1 ▮▮▮▮▮", end="", flush=True)
    elif beat_type == 2:
        print("\r\033[K▯▯ • ▯▯", end="", flush=True)


def print_header():
    st = engine.get_status()
    print("\n" + "=" * 60)
    print("DRUM ASSISTANT - LAPTOP MODE")
    print("=" * 60)
    print(f"Pattern: {st['pattern_name']}")
    print(f"BPM: {st['bpm']}")
    print("Controls: SPACE=tap, ENTER=start/stop, N=next pattern, +/- bpm, Q=quit")
    print("=" * 60 + "\n")


def main():
    engine.start_engine(beat_callback=visual_beat)
    print_header()

    if not KEYBOARD_AVAILABLE:
        print("Install 'keyboard' for best control: pip install keyboard")
        while True:
            cmd = input("> ").strip().lower()
            if cmd in ("q", "quit", "exit"):
                break
            if cmd in ("tap", "t"):
                engine.handle_tap()
            elif cmd in ("start", "stop", "s"):
                engine.handle_start()
            elif cmd in ("next", "n"):
                engine.next_pattern()
            elif cmd in ("+", "up"):
                engine.adjust_bpm(5)
            elif cmd in ("-", "down"):
                engine.adjust_bpm(-5)
        return

    keyboard.on_press_key("space", lambda _: engine.handle_tap())
    keyboard.on_press_key("enter", lambda _: engine.handle_start())
    keyboard.on_press_key("n", lambda _: engine.next_pattern())
    keyboard.on_press_key("+", lambda _: engine.adjust_bpm(5))
    keyboard.on_press_key("-", lambda _: engine.adjust_bpm(-5))

    while True:
        if keyboard.is_pressed("q"):
            break
        time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    finally:
        print("\n\nGoodbye!\n")
