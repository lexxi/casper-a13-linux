#!/usr/bin/env python3
"""Toggle Casper TAB-WB72 matchbox-keyboard using the physical LRADC HOME key."""

import fcntl
import os
import struct
import subprocess
import time

DEVICE = "/dev/input/event1"  # Confirm on the target; may change after input reordering
EV_KEY = 1
KEY_HOME = 102
EVIOCGRAB = 0x40044590

# Native input_event layout on this tablet (32-bit ARM, 16 bytes).
EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)
KEYBOARD_PATTERN = r"^(/usr/bin/)?matchbox-keyboard$"

ENV = os.environ.copy()
ENV["DISPLAY"] = ":0"
ENV["MB_KBD_CONFIG"] = "/root/casper-keyboard/keyboard.xml"

DEBOUNCE_SECONDS = 0.3
RETRY_SECONDS = 2


def keyboard_running():
    result = subprocess.run(
        ["pgrep", "-f", KEYBOARD_PATTERN],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def keyboard_stop():
    subprocess.run(
        ["pkill", "-f", KEYBOARD_PATTERN],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    print("Keyboard OFF", flush=True)


def keyboard_start():
    if keyboard_running():
        return
    subprocess.Popen(
        ["/usr/bin/matchbox-keyboard"],
        env=ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    print("Keyboard ON", flush=True)


def toggle_keyboard():
    if keyboard_running():
        keyboard_stop()
    else:
        keyboard_start()


def main():
    print("Casper keyboard toggle started", flush=True)
    print(f"Input device: {DEVICE}", flush=True)
    print(f"Event size: {EVENT_SIZE} bytes", flush=True)
    last_press = 0.0

    while True:
        try:
            with open(DEVICE, "rb", buffering=0) as device:
                # Exclusive access prevents Xorg/xterm from also receiving KEY_HOME.
                fcntl.ioctl(device.fileno(), EVIOCGRAB, 1)
                print("LRADC grabbed exclusively", flush=True)
                print("Waiting for HOME button...", flush=True)

                while True:
                    data = device.read(EVENT_SIZE)
                    if len(data) != EVENT_SIZE:
                        raise OSError("Incomplete input event")

                    _, _, event_type, code, value = struct.unpack(
                        EVENT_FORMAT, data
                    )
                    if event_type == EV_KEY and code == KEY_HOME and value == 1:
                        now = time.monotonic()
                        if now - last_press < DEBOUNCE_SECONDS:
                            continue
                        last_press = now
                        toggle_keyboard()
        except OSError as exc:
            print(f"Input error: {exc}", flush=True)
            time.sleep(RETRY_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCasper keyboard toggle stopped", flush=True)
