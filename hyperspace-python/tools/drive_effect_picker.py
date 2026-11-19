"""tools/app_driver.py script (plan 65): GRAPH's effect picker in the real
app — opened as the right-click picker's **effects…** opens it, the tiles
filling in as the renderer makes their previews, a search, a hovered tile
playing its loop, a click adding the effect unwired, and that node's
thumbnail: the test card through it, though it reaches nothing.

    uv run python tools/app_driver.py tools/drive_effect_picker.py --out /tmp/picker

The frames worth a look are named in ``<out>/marks.json`` (written when
``EFFECT_PICKER_MARKS`` names a file; app_driver's frame numbers).
"""

import json
import os

from hyperspace import ui_effect_picker as fxpick
from hyperspace import ui_graph

MARKS: dict[str, int] = {}


def _mark(panel, name: str) -> None:
    MARKS[name] = _mark.n
    path = os.environ.get("EFFECT_PICKER_MARKS")
    if path:
        with open(path, "w") as f:
            json.dump(MARKS, f)


_mark.n = 0


def _wait(d, k):
    for _ in range(k):
        _mark.n += 1
        yield


def script(d, panel):
    st = ui_graph._state(panel)
    _mark.n = 20                         # app_driver's settle: the frame the script starts on
    # (the party show has every effect bypassed, `fx.on` off: an effect that is
    # off passes its picture through, so its unwired thumbnail would be the
    # plain card. On here, in the run's scratch home)
    panel.reg["fx.on"].set(True)
    yield from d.park()
    yield from _wait(d, 30)
    at = ui_graph.in_view(panel)
    fxpick.open_picker(st, "add", (at[0] + 600.0, at[1] + 360.0))   # (the menu row's action)
    yield from _wait(d, 50)              # the previews: 3 passes a frame, stills first
    _mark(panel, "open")
    yield from _wait(d, 4)
    for ch in "wave":
        yield from d.type(ch)
        _mark.n += 1
    yield from _wait(d, 6)
    _mark(panel, "searched")
    yield from _wait(d, 2)
    for _ in "wave":
        yield from d.key(__import__("imgui_bundle").imgui.Key.backspace)
        _mark.n += 2
    yield from _wait(d, 6)
    for k in range(20):                  # glide onto Kaleidoscope's tile
        yield from d.move(fxpick.TILE.format("kaleido"), frames=1)
        _mark.n += 1
        if k == 0:
            break
    yield from _wait(d, 30)              # its loop made (24 cells) and playing
    _mark(panel, "hovered")
    yield from _wait(d, 1)
    _mark(panel, "hovered.2")
    yield from _wait(d, 3)
    _mark(panel, "hovered.3")
    yield from d.press(True)
    yield from d.press(False)
    _mark.n += 2
    yield from d.park()
    _mark.n += 1
    yield from _wait(d, 40)
    _mark(panel, "added")
    yield from _wait(d, 4)
    # the effects that read an aux (Blend, Displace): their tips say so, and
    # their previews have a known disc wired in
    fxpick.open_picker(st, "add", (at[0] + 600.0, at[1] + 520.0))
    yield from _wait(d, 6)
    for ch in "aux":
        yield from d.type(ch)
        _mark.n += 1
    yield from _wait(d, 4)
    yield from d.move(fxpick.TILE.format("displace"), frames=1)
    _mark.n += 1
    yield from _wait(d, 30)
    _mark(panel, "aux")
    yield from _wait(d, 4)
