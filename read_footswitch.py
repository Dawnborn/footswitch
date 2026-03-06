#!/usr/bin/env python3
"""
PCsensor FootSwitch reader.

Pedals are pre-programmed to F22/F23/F24 (harmless keys that won't
interfere with normal use). This script listens for those key events
and maps them back to pedal numbers.

Setup (one-time):
    1. Install system dependency:
           sudo apt-get install libhidapi-dev
    2. Build and install the footswitch CLI tool:
           cd /home/robot/git/ws_footpedal/footswitch
           make && sudo make install
    3. Reload udev rules and replug the device:
           sudo udevadm control --reload-rules && sudo udevadm trigger
    4. Program pedals to F22/F23/F24:
           footswitch -1 -k f22 -2 -k f23 -3 -k f24
    5. Install Python packages (into the project venv):
           pip install hidapi evdev

Usage:
    python3 read_footswitch.py             # Monitor pedal press/release
    python3 read_footswitch.py --read-config  # Show current pedal config via HID
"""

import sys
import time
import argparse

import hid
import evdev
from evdev import ecodes

SUPPORTED_DEVICES = [
    (0x0C45, 0x7403),
    (0x0C45, 0x7404),
    (0x413D, 0x2107),
    (0x1A86, 0xE026),
    (0x3553, 0xB001),
]

PEDAL_KEY_CODES = {
    ecodes.KEY_F22: 1,
    ecodes.KEY_F23: 2,
    ecodes.KEY_F24: 3,
}

KEYMAP = {
    0x04: "a", 0x05: "b", 0x06: "c", 0x07: "d", 0x08: "e", 0x09: "f",
    0x0A: "g", 0x0B: "h", 0x0C: "i", 0x0D: "j", 0x0E: "k", 0x0F: "l",
    0x10: "m", 0x11: "n", 0x12: "o", 0x13: "p", 0x14: "q", 0x15: "r",
    0x16: "s", 0x17: "t", 0x18: "u", 0x19: "v", 0x1A: "w", 0x1B: "x",
    0x1C: "y", 0x1D: "z",
    0x1E: "1", 0x1F: "2", 0x20: "3", 0x21: "4", 0x22: "5", 0x23: "6",
    0x24: "7", 0x25: "8", 0x26: "9", 0x27: "0",
    0x28: "enter", 0x29: "esc", 0x2A: "backspace", 0x2B: "tab",
    0x2C: "space", 0x39: "capslock",
    0x3A: "f1", 0x3B: "f2", 0x3C: "f3", 0x3D: "f4", 0x3E: "f5",
    0x3F: "f6", 0x40: "f7", 0x41: "f8", 0x42: "f9", 0x43: "f10",
    0x44: "f11", 0x45: "f12", 0x68: "f13", 0x69: "f14", 0x6A: "f15",
}

MODIFIERS = {
    0x01: "l_ctrl", 0x02: "l_shift", 0x04: "l_alt", 0x08: "l_win",
    0x10: "r_ctrl", 0x20: "r_shift", 0x40: "r_alt", 0x80: "r_win",
}

MOUSE_BUTTONS = {1: "mouse_left", 2: "mouse_right", 4: "mouse_middle"}


# ---------------------------------------------------------------------------
# Read config via HID interface 1
# ---------------------------------------------------------------------------

def find_hid_device(interface_number):
    for vid, pid in SUPPORTED_DEVICES:
        for info in hid.enumerate(vid, pid):
            if info["interface_number"] == interface_number:
                dev = hid.device()
                dev.open_path(info["path"])
                return dev
    return None


def decode_key_response(data):
    parts = [name for mask, name in MODIFIERS.items() if data[2] & mask]
    if data[3] != 0:
        parts.append(KEYMAP.get(data[3], f"<0x{data[3]:02x}>"))
    return "+".join(parts) if parts else "<none>"


def decode_mouse_response(data):
    parts = []
    if data[4] in MOUSE_BUTTONS:
        parts.append(MOUSE_BUTTONS[data[4]])
    x = data[5] - 256 if data[5] > 127 else data[5]
    y = data[6] - 256 if data[6] > 127 else data[6]
    w = data[7] - 256 if data[7] > 127 else data[7]
    if x or y or w:
        parts.append(f"X={x} Y={y} W={w}")
    return " ".join(parts) if parts else "<none>"


def read_config():
    dev = find_hid_device(interface_number=1)
    if dev is None:
        print("Error: footswitch not found.")
        sys.exit(1)
    try:
        query = [0x01, 0x82, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00]
        print("=== Pedal Configuration ===")
        for i in range(3):
            query[3] = i + 1
            dev.write(query)
            time.sleep(0.03)
            resp = dev.read(8, timeout_ms=1000)
            if not resp or len(resp) < 2:
                print(f"  [pedal {i + 1}]: read error")
                continue
            t = resp[1]
            if t == 0:
                desc = "unconfigured"
            elif t in (1, 0x81):
                desc = decode_key_response(resp)
            elif t == 2:
                desc = decode_mouse_response(resp)
            elif t == 3:
                desc = f"{decode_key_response(resp)} {decode_mouse_response(resp)}"
            else:
                desc = f"raw: {[f'0x{b:02x}' for b in resp]}"
            print(f"  [pedal {i + 1}]: {desc}")
    finally:
        dev.close()


# ---------------------------------------------------------------------------
# Monitor pedal events via evdev (no grab, no side-effects with F22/F23/F24)
# ---------------------------------------------------------------------------

def find_evdev_keyboard():
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if any(
            dev.info.vendor == vid and dev.info.product == pid
            for vid, pid in SUPPORTED_DEVICES
        ):
            caps = dev.capabilities()
            if 1 in caps and any(k < 200 for k in caps[1]):
                return dev
        dev.close()
    return None


def monitor_pedals():
    dev = find_evdev_keyboard()
    if dev is None:
        print("Error: footswitch keyboard device not found.")
        sys.exit(1)

    print(f"Device: {dev.name} ({dev.path})")
    print("Monitoring pedal events (Ctrl+C to stop) ...")
    print("-" * 50)

    try:
        for event in dev.read_loop():
            if event.type != ecodes.EV_KEY or event.value == 2:
                continue

            pedal = PEDAL_KEY_CODES.get(event.code)
            ts = time.strftime("%H:%M:%S")
            state = "PRESSED" if event.value == 1 else "RELEASED"

            if pedal is not None:
                print(f"  [{ts}] Pedal {pedal} {state}")
            else:
                key_name = ecodes.KEY.get(event.code, event.code)
                if isinstance(key_name, list):
                    key_name = key_name[0]
                print(f"  [{ts}] Unknown key ({key_name}) {state}")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        dev.close()


def main():
    parser = argparse.ArgumentParser(description="PCsensor FootSwitch reader")
    parser.add_argument("--read-config", action="store_true",
                        help="Read current pedal configuration via HID")
    args = parser.parse_args()

    if args.read_config:
        read_config()
    else:
        monitor_pedals()


if __name__ == "__main__":
    main()
