# FootSwitch Setup Guide

## Prerequisites

- PCsensor FootSwitch (VID:PID `3553:b001` or other supported devices)
- Ubuntu / Debian Linux

## 1. Install System Dependency

```bash
sudo apt-get install libhidapi-dev
```

## 2. Build and Install the FootSwitch CLI

```bash
cd /home/robot/git/ws_footpedal/footswitch
make
sudo make install
```

`make install` also installs udev rules so the device can be accessed without root.

Reload udev rules and replug the device:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## 3. Program Pedals to F22/F23/F24

F22/F23/F24 are chosen because they have no default binding in any desktop environment, avoiding accidental triggers.

```bash
footswitch -1 -k f22 -2 -k f23 -3 -k f24
```

Verify:

```bash
footswitch -r
```

Expected output:

```
[switch 1]: f22
[switch 2]: f23
[switch 3]: f24
```

This configuration is persisted in the pedal firmware and survives power cycles.

## 4. Install Python Packages

```bash
cd /home/robot/git/ws_footpedal/footswitch
source venv/bin/activate
pip install hidapi evdev
```

| Package | Purpose |
|---------|---------|
| `hidapi` | Read pedal configuration via HID interface |
| `evdev` | Monitor real-time pedal press/release events |

## 5. Usage

Monitor pedal press/release events:

```bash
python read_footswitch.py
```

Read current pedal configuration:

```bash
python read_footswitch.py --read-config
```

## Pedal Mapping

| Pedal | Bound Key | evdev Code |
|-------|-----------|------------|
| 1 | F22 | `KEY_F22` |
| 2 | F23 | `KEY_F23` |
| 3 | F24 | `KEY_F24` |

## Notes

- The script reads events passively (no exclusive grab), so it does not conflict with other input listeners.
- F22/F23/F24 are not used by GNOME, KDE, or any common desktop environment. Avoid F13/F14 as they map to `XF86Tools` / `XF86Launch5` in GNOME and will open the Settings window.
