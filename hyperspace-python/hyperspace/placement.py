"""Where the windows open at launch: the config's screen, else where they were.

Two sources, in this order (plan 16 WP4, fork F4):

- ``[output] monitor`` / ``control_monitor`` in config.toml — a screen
  index. At 0 or above the window opens on that screen.
- ``<home>/windows.json`` — the windowed rects at the last quit (or ⌘R).
  It fills in what the config leaves at −1, and on a configured screen it
  still supplies the spot when the last position was on that screen.

With neither, the windows open where they always did: render top-left of
the primary screen, controls flush right, both inset by MARGIN.

A remembered rect is only ever used when enough of it is on a connected
screen to be grabbed (`usable`); anything else — an unplugged projector, a
hand-edited file, a rect off every screen — falls back to the default spot
and says so in a note. Nothing here can leave a window unreachable.

The file::

    {"schema": "hyperspace.windows/1",
     "control": {"x": 2100, "y": 60, "w": 960, "h": 900, "screen": "Built-in Retina Display"},
     "render": [{"x": 1744, "y": 41, "w": 1280, "h": 820, "screen": "DELL U2720Q"}]}

``x, y, w, h`` are GLFW screen coordinates of the content area, always the
*windowed* rect (never a fullscreen or overlay cover: whether a launch is
fullscreen is the config's say, fork F6). ``render`` is a list — one entry
today, one per output later — and `place` is called once per window, so
nothing here assumes how many render windows there are. ``screen`` is the
name of the screen the rect was on, kept for the note; placement is decided
by geometry alone. The file is written on quit and on restart only (fork
F5); delete it to forget.

No GL, no imgui, and nothing imported from the package: `glfw` is passed
in, and the home folder is the caller's (app.py takes it from
`library.home()`, where `config.load` looks).
"""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

FILE = "windows.json"
SCHEMA = "hyperspace.windows/1"
MIN_VISIBLE = (120, 80)        # px of a window that must be on a screen
MIN_SIZE = (320, 240)          # a remembered size never opens smaller
MARGIN = 16                    # the default spot's inset

Rect = tuple[int, int, int, int]            # x, y, w, h


@dataclass(frozen=True)
class Screen:
    """One monitor's work area (the screen less the menu bar and dock)."""

    name: str
    x: int
    y: int
    w: int
    h: int


def screens(glfw) -> list[Screen]:
    """Every connected screen in `glfw.get_monitors()` order — the primary
    first, the order the config's indices count in. [] when there are none
    or the window system will not say."""
    try:
        mons = list(glfw.get_monitors())
    except Exception:  # noqa: BLE001 — no screens is an answer; a launch must not die here
        return []
    out = []
    for i, m in enumerate(mons):
        try:
            x, y, w, h = (int(v) for v in glfw.get_monitor_workarea(m))
            name = glfw.get_monitor_name(m)
            name = name.decode(errors="replace") if isinstance(name, bytes) else str(name or "")
        except Exception:  # noqa: BLE001 — as above
            return []      # indices must keep meaning what the config says: all or nothing
        if w <= 0 or h <= 0:
            return []
        out.append(Screen(name or f"screen {i + 1}", x, y, w, h))
    return out


# ---- the file ----

def load(home: Path) -> dict:
    """The remembered file; {} when missing, unreadable, or another schema.
    Each window's entry is checked where it is used (`place`), so one bad
    entry costs only that window's memory."""
    try:
        doc = json.loads((Path(home) / FILE).read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        return {}
    if not isinstance(doc.get("render", []), list):
        return {}
    return doc


def save(home: Path, control: Rect | None, render: list[Rect | None],
         scr: list[Screen]) -> None:
    """Write the windowed rects. A None (a minimised window) keeps that
    window's old entry. Atomic — a temp file, then a rename — and a failed
    write costs only the memory: it is said on stderr and never raised."""
    home = Path(home)
    old = load(home)
    olds = old.get("render", [])
    entries = []
    for i in range(max(len(render), len(olds))):
        new = _entry(render[i], scr) if i < len(render) else None
        entries.append(new if new is not None else olds[i] if i < len(olds) else None)
    doc = {"schema": SCHEMA,
           "control": _entry(control, scr) or old.get("control"),
           "render": entries}
    tmp = home / f"{FILE}.{os.getpid()}.tmp"     # its own: two instances may share a home
    try:
        tmp.write_text(json.dumps(doc, indent=1) + "\n")
        os.replace(tmp, home / FILE)
    except (OSError, TypeError, ValueError) as e:
        print(f"placement: could not write {home / FILE} ({e}) — "
              "the windows' positions are not remembered", file=sys.stderr)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _entry(rect, scr: list[Screen]) -> dict | None:
    """A file entry for a rect; None for a None, a rect that is not one, or
    one no launch would restore (not `usable` on the screens as they are —
    a window in the OS's own fullscreen sits above the work area): the old
    entry is worth more than that."""
    r = _rect(dict(zip("xywh", rect, strict=False))) if rect is not None else None
    if r is None or not usable(r, scr):
        return None
    on = _centre_screen(r, scr) or _landing(r, scr)
    return {"x": r[0], "y": r[1], "w": r[2], "h": r[3], "screen": on.name if on else ""}


def _rect(entry) -> Rect | None:
    """The rect in a file entry, or None when it is not four sane numbers."""
    if not isinstance(entry, dict):
        return None
    out = []
    for k in "xywh":
        v = entry.get(k)
        if isinstance(v, bool) or not isinstance(v, int | float):
            return None
        # the bound first: isfinite() raises on an int too big for a float,
        # and a NaN fails the comparison
        if not abs(v) <= 1_000_000 or not math.isfinite(v):
            return None
        out.append(round(v))
    if out[2] <= 0 or out[3] <= 0:
        return None
    return out[0], out[1], out[2], out[3]


# ---- geometry ----

def _overlap(rect: Rect, s: Screen) -> tuple[int, int]:
    x, y, w, h = rect
    return (min(x + w, s.x + s.w) - max(x, s.x), min(y + h, s.y + s.h) - max(y, s.y))


def _reachable(rect: Rect, s: Screen) -> bool:
    ow, oh = _overlap(rect, s)
    return ow >= MIN_VISIBLE[0] and oh >= MIN_VISIBLE[1] and s.y <= rect[1] < s.y + s.h


def usable(rect: Rect, scr: list[Screen]) -> bool:
    """Some screen's work area overlaps the rect by at least MIN_VISIBLE,
    and the rect's top edge is inside that work area — the title bar can be
    reached."""
    return any(_reachable(rect, s) for s in scr)


def _landing(rect: Rect, scr: list[Screen]) -> Screen | None:
    """The screen a usable rect is mostly on; None when it is not usable."""
    ok = [s for s in scr if _reachable(rect, s)]
    if not ok:
        return None
    return max(ok, key=lambda s: _overlap(rect, s)[0] * _overlap(rect, s)[1])


def _on(rect: Rect, s: Screen) -> bool:
    cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
    return s.x <= cx < s.x + s.w and s.y <= cy < s.y + s.h


def _centre_screen(rect: Rect, scr: list[Screen]) -> Screen | None:
    return next((s for s in scr if _on(rect, s)), None)


def _fit(rect: Rect, scr: list[Screen]) -> Rect | None:
    """A remembered rect as it may open: its size clipped to the screen it
    lands on and never under MIN_SIZE; None when it is not usable (before
    or after the clip)."""
    x, y, w, h = rect
    w, h = max(MIN_SIZE[0], w), max(MIN_SIZE[1], h)
    s = _landing((x, y, w, h), scr)
    if s is None:
        return None
    out =(x, y, max(MIN_SIZE[0], min(w, s.w)), max(MIN_SIZE[1], min(h, s.h)))
    return out if usable(out, scr) else None


def default_rect(kind: str, size: tuple[int, int], s: Screen) -> Rect:
    """The default spot on a screen. Render (and anything else): top-left
    + MARGIN. Control: flush right − MARGIN, top + MARGIN. The size is the
    one asked for, as it always was: on a screen smaller than the window
    it overhangs, and a clipped size would be remembered at the quit and
    follow the window to a bigger screen."""
    w, h = int(size[0]), int(size[1])
    x = s.x + MARGIN
    if kind == "control":
        x = max(s.x + s.w - w - MARGIN, x)
    return x, s.y + MARGIN, w, h


# ---- the decision ----

def _key(kind: str) -> str:
    return "control_monitor" if kind == "control" else "monitor"


def place(kind: str, size: tuple[int, int], scr: list[Screen],
          monitor: int, remembered: dict | None) -> tuple[Rect, str]:
    """Where one window opens: (rect, note or "").

    `kind` is "render" or "control"; `monitor` is that window's config
    index (−1: no say); `remembered` is its entry from the file, or None.

    1. `monitor` ≥ 0 and that screen exists: the remembered rect if it is
       usable and its centre is on that screen; else the default spot there.
    2. `monitor` −1, or no such screen (with a note): the remembered rect
       if usable; else the default spot on the primary screen.
    3. A remembered size is kept, clipped to the screen it lands on.

    With no screens at all the default size comes back at the margin; the
    caller sets no position then."""
    if not scr:
        return (MARGIN, MARGIN, int(size[0]), int(size[1])), ""
    notes = []
    target = None
    try:
        # read as app._make_output reads it for `output.monitor`, so the
        # screen a window opens on and the one fullscreen covers agree
        monitor = int(monitor)
    except (TypeError, ValueError, OverflowError):
        notes.append(f"config: [output] {_key(kind)} = {monitor!r} is not a screen index — "
                     "using the last position")
        monitor = -1
    if monitor >= len(scr):
        n = len(scr)
        have = "0" if n == 1 else f"0–{n - 1}"
        notes.append(f"config: [output] {_key(kind)} = {monitor}, but {n} "
                     f"screen{'s are' if n != 1 else ' is'} connected ({have}) — "
                     "using the last position")
    elif monitor >= 0:
        target = scr[monitor]
    rect = _rect(remembered)
    if remembered is not None and rect is None:
        notes.append(f"placement: the {kind} window's entry in {FILE} is not a rect — ignored")
    if rect is not None:
        fitted = _fit(rect, scr)
        if fitted is None:
            notes.append(_gone(kind, remembered, rect, target or scr[0], scr))
        elif target is None or _on(fitted, target):
            return fitted, "; ".join(notes)
        # else the config names another screen than the one it was on: the
        # config wins (fork F4), and that is what was asked — no note
    return default_rect(kind, size, target or scr[0]), "; ".join(notes)


def _gone(kind: str, remembered: dict, rect: Rect, to: Screen, scr: list[Screen]) -> str:
    was = remembered.get("screen")
    if isinstance(was, str) and was and was not in {s.name for s in scr}:
        return (f'placement: the {kind} window was last on "{was}", which is not '
                f'connected — opening on "{to.name}"')
    return (f"placement: the {kind} window's last position ({rect[0]}, {rect[1]}) is on "
            f'no screen — opening on "{to.name}"')
