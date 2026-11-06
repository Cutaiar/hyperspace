#!/usr/bin/env python3
"""The on-screen pad for an Xbox pad and for a DualSense Edge, as PNGs (plan 42).

Not the app: `tools/label_menu_shot.py`'s hidden control window with the
real Panel, the panel hidden so the pad diagram has the room. The Edge is
read from a tape this script writes (`pads.hid.Recorder`): a finger on
the touchpad's upper right, a second one for a pinch, the pad tipped
right side down and its far edge up, the right back button held — read
by `gamepad.Pad` exactly as a pad entry with ``tape =`` reads one. A few
rows light the extras the way plan 42's ideas would map them.

  uv run python tools/pad_shots.py     # → docs/plans/assets/42-controllers/pad-{xbox,edge}[-view].png

Each face in each of the pad window's views (ui_pad_views.VIEWS).
"""

# label_menu_shot (and through it undo_demo) is imported
# first, on purpose: it sets HYPERSPACE_HOME and points pyGLFW at imgui_bundle's libglfw
from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import label_menu_shot as shot
from label_menu_shot import Hidden

from hyperspace import gamepad, ui_pad_views
from hyperspace.pads import hid, sony
from hyperspace.routing import Binding

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "42-controllers"
JOYCON_OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "46-joycon"
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


def joycon_tape(path: Path, kind: str = "l") -> Path:
    """A second of a Joy-Con held like a remote (plan 46): the stick pushed
    up-right, ZL (ZR) most of the way (it is digital: on), SL and ↓ (A)
    held, the far end lifted and the right side down a little, the
    sensors' z up out of the face."""
    from hyperspace.pads import nintendo
    rec = hid.Recorder(path, f"joycon-{kind}", "bluetooth")
    for k in range(60):
        r = bytearray(49)
        r[0], r[1], r[2] = nintendo.REPORT_FULL, k & 0xFF, 0x60     # battery medium
        if kind == "l":
            r[5] = 0x01 | 0x20 | 0x80                                 # ↓, SL, ZL
        else:
            r[3] = 0x08 | 0x20 | 0x80                                 # A, SL, ZR
        x, y = 2048 + 900, 2048 + 700
        packed = bytes((x & 0xFF, ((x >> 8) & 0x0F) | ((y & 0x0F) << 4), (y >> 4) & 0xFF))
        r[6:9] = packed if kind == "l" else bytes(3)
        r[9:12] = packed if kind == "r" else bytes(3)
        # the chip's x along the long axis (the far end lifted: +x), y
        # across (right side down: +y → the pad's −x), z up out of the face
        for off in (13, 25, 37):
            struct.pack_into("<6h", r, off, 1800, 900, 3500, 0, 0, 0)
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
        if table.owner(b.target) is None:      # the loaded loadable patch may perform it already
            table.add(b)

    views = ui_pad_views.VIEWS
    panel.pad = gamepad.Pad()                 # no pad connected: the Xbox face
    for k, view in enumerate(views):
        panel.reg["ui.pad_view"].set(k)
        h.draw(6)
        name = "pad-xbox.png" if view == "map" else f"pad-xbox-{view}.png"
        print(f"wrote {crop(h.save(name))}")

    with tempfile.TemporaryDirectory() as tmp:
        pad = gamepad.Pad(tape=str(edge_tape(Path(tmp) / "edge.jsonl")))
        panel.pad = pad
        # as the device would send it: a sink row on R2's resistance and the heavy motor
        sent = sony.Effects(light=(255, 0, 128), players=sony.player_bits(1), rumble_low=0.6,
                            right=sony.Trigger("resist", 0.15, 0.75))
        for k, view in enumerate(views):
            panel.reg["ui.pad_view"].set(k)
            for _ in range(45):               # long enough for the tilt to settle
                pad.poll(1 / 60)
                pad.effects = sent
                h.draw(1)
            name = "pad-edge.png" if view == "map" else f"pad-edge-{view}.png"
            print(f"wrote {crop(h.save(name))}  ({pad.model.name}, {pad.link})")
        # a Joy-Con (L), one per role (plan 46): the lights and the light band on
        shot.OUT = JOYCON_OUT
        JOYCON_OUT.mkdir(parents=True, exist_ok=True)
        pad = gamepad.Pad(tape=str(joycon_tape(Path(tmp) / "joycon.jsonl")))
        panel.pad = pad
        sent = sony.Effects(players=sony.player_bits(1), rumble_high=0.4)
        for k, view in enumerate(views):
            panel.reg["ui.pad_view"].set(k)
            for _ in range(45):
                pad.poll(1 / 60)
                pad.effects = sent
                h.draw(1)
            name = "pad-joycon.png" if view == "map" else f"pad-joycon-{view}.png"
            print(f"wrote {crop(h.save(name))}  ({pad.model.name}, {pad.link})")
    h.close()


if __name__ == "__main__":
    main()
