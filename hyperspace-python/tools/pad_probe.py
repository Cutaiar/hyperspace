"""Watch a gamepad's raw buttons, hat and axes in a terminal.

    uv run python tools/pad_probe.py          # GLFW, else a wired 360 pad over USB
    uv run python tools/pad_probe.py --no-usb # GLFW only

The pad is read exactly as the app reads it (`gamepad.Pad`), so the
indices printed here are the ones `gamepad.py`'s map and a `pad:<NAME>`
binding mean. Press a button and the line says which raw index went down
and what name — if any — this build calls it: that is how a pad whose
firmware numbers its buttons differently gets caught.

A small window is opened (and focused) because macOS only delivers
joystick state to an app that is pumping events.
"""

from __future__ import annotations

import argparse
import sys
import time

import glfw

from hyperspace import gamepad as gp

FPS = 60
NAMES = {i: n for n, i in gp.BUTTONS.items()}
HAT_NAMES = {bit: n for n, bit in gp.HATS.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--no-usb", action="store_true", help="don't look over libusb")
    args = ap.parse_args()
    if not glfw.init():
        raise SystemExit("glfw: init failed")
    glfw.window_hint(glfw.RESIZABLE, False)
    win = glfw.create_window(420, 80, "pad probe — keep me focused", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("glfw: no window")
    pad = gp.Pad(usb=not args.no_usb)
    print("press buttons; Ctrl-C or close the window to stop\n", file=sys.stderr)
    was = None
    try:
        while not glfw.window_should_close(win):
            glfw.poll_events()
            pad.poll()
            if pad.source != was:
                print(f"-- pad: {pad.source or 'none'}"
                      f"{f' (jid {pad.jid})' if pad.source == 'glfw' else ''}"
                      f", {len(pad.buttons)} buttons", file=sys.stderr)
                was = pad.source
            for i in range(len(pad.buttons)):
                if pad.pressed(i):
                    name = NAMES.get(i)
                    print(f"button {i:>2} down   "
                          f"{'pad:' + name if name else 'UNMAPPED — no pad:<NAME> for this index'}")
            for bit, name in HAT_NAMES.items():
                if pad.hat_pressed(bit):
                    print(f"hat {bit:>5} down   hat:{name}")
            _draw(pad)
            time.sleep(1 / FPS)
    except KeyboardInterrupt:
        pass
    finally:
        print()
        if pad.usb_pad is not None:
            pad.usb_pad.close()
        glfw.terminate()


def _draw(pad: gp.Pad) -> None:
    """One live line: the axes as their routing lanes, and what is held."""
    lanes = " ".join(f"{n} {u:4.2f}" for n, u in zip(gp.AXES, pad.lanes()))
    held = ",".join(NAMES.get(i, str(i)) for i in range(len(pad.buttons)) if pad.down(i))
    held += ("+" if held else "") + ",".join(n for b, n in HAT_NAMES.items() if pad.hat & b)
    sys.stdout.write(f"\r{lanes}  held: {held.strip('+') or '-':<28}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
