#!/usr/bin/env python3
"""The on-screen pad for an Xbox pad and for a DualSense Edge, as PNGs (plan 42).

Not the app: `tools/label_menu_shot.py`'s hidden control window with the
real Panel, the panel hidden so the pad diagram has the room. The Edge is
read from a tape this script writes (`pads.hid.Recorder`): a finger on
the touchpad's upper right, a second one for a pinch, the pad tipped
right side down and its far edge up, the right back button held — read
by `gamepad.Pad` exactly as a pad entry with ``tape =`` reads one. A few
rows light the extras the way plan 42's ideas would map them.

  uv run python tools/pad_shots.py     # → docs/plans/assets/42-controllers/pad-xbox.png, pad-edge.png
"""

# ruff: noqa: I001 — label_menu_shot (and through it undo_demo) is imported
# first, on purpose: it sets HYPERSPACE_HOME and points pyGLFW at imgui_bundle's libglfw
from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import label_menu_shot as shot
from label_menu_shot import Hidden

from hyperspace import gamepad
from hyperspace.pads import hid, sony
from hyperspace.routing import Binding

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "42-controllers"
ROWS = (  # plan 42's ideas 4 and 5, as rows
    Binding("touch:x", "fx.zoomblur.cx", "position"),
    Binding("touch:pinch", "camera.zoom", "push", 0.5),
    Binding("motion:roll", "fx.huecycle.speed", "position"),
    Binding("axis:RT", "fx.kaleido.mix", "position"),
)


def edge_tape(path: Path) -> Path:
    """A second of an Edge held tipped, two fingers down, R4 held."""
    rec = hid.Recorder(path, "edge", "usb")
    for k in range(60):
        r = bytearray(64)
        r[0] = 0x01
        p = memoryview(r)[1:]
        p[0:4] = bytes([0x80, 0x80, 0xC8, 0x50])          # the right stick up-right
        p[5] = 180                                         # R2 most of the way
        p[7] = 0x08                                        # hat released
        p[9] = 0x80                                        # the right back button
        for off, (x, y, i) in ((32, (1500, 260, 1)), (36, (1100, 700, 2))):
            p[off:off + 4] = bytes([i, x & 0xFF, (x >> 8) | ((y & 0x0F) << 4), y >> 4])
        struct.pack_into("<3h", p, 21, -3000, 7000, -2500)   # right down, far edge up
        rec.write(bytes(r), t=k / 60)
    rec.close()
    return path


def crop(path: Path) -> Path:
    """The picture cut to the pad's window (the rest of the hidden control
    window is black), with a margin."""
    import numpy as np
    from PIL import Image
    im = Image.open(path)
    px = np.asarray(im.convert("L"))
    ys, xs = np.nonzero(px > 8)
    if len(xs):
        m = 8
        im.crop((max(0, xs.min() - m), max(0, ys.min() - m),
                 min(im.width, xs.max() + m), min(im.height, ys.max() + m))).save(path, optimize=True)
    return path


def main() -> None:
    shot.OUT = OUT
    h = Hidden("pad shots")
    panel = h.panel
    panel.reg["ui.panel"].set(False)
    panel.pad_diagram = True
    table = h.r.router.table
    for b in ROWS:
        if table.owner(b.target) is None:      # the loaded preset may perform it already
            table.add(b)

    panel.pad = gamepad.Pad()                 # no pad connected: the Xbox face
    h.draw(6)
    print(f"wrote {crop(h.save('pad-xbox.png'))}")

    with tempfile.TemporaryDirectory() as tmp:
        pad = gamepad.Pad(tape=str(edge_tape(Path(tmp) / "edge.jsonl")))
        panel.pad = pad
        for _ in range(45):                   # long enough for the tilt to settle
            pad.poll(1 / 60)
            pad.effects = sony.Effects(light=(255, 0, 128))   # as the device would send it
            h.draw(1)
        print(f"wrote {crop(h.save('pad-edge.png'))}  ({pad.model.name}, {pad.link})")
    h.close()


if __name__ == "__main__":
    main()
