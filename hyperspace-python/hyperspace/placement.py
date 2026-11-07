"""Where the windows open at launch: the config's screen, else where they were.

Two sources, in this order (plan 16 WP4, fork F4):

- ``[output] monitor`` / ``control_monitor`` in config.toml — a screen
  index, or a screen's name (row 771: `match`). At 0 or above, or on a name
  that is connected, the window opens on that screen.
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
fullscreen is the config's say, fork F6). ``render`` is a list, one entry
per render output in the config's order (plan 21: ``[[output.screens]]``;
one entry with no list), and `place` is called once per window, so
nothing here assumes how many render windows there are. A file with one
entry still loads for an install with two: the second opens at its default spot. ``screen`` is the
name of the screen the rect was on, kept for the note; placement is decided
by geometry alone. The file is written on quit and on restart only (fork
F5); delete it to forget.

**Since each display's row says what it shows (`displays.py`, SC2),** an output can move
between displays, so a place in ``render`` says little: a window's spot goes under
``displays``, by the display's label, ``{"displays": {"TV #2": {"x": ...}}}``, and that's read
first (`spot`). The file stays ``/1``: ``render`` is still written, an older build reads it,
and it's where a display with no entry of its own looks once.

No GL, no imgui, and nothing imported from the package: `glfw` is passed
in, and the home folder is the caller's (app.py takes it from
`library.home()`, where `config.load` looks).
"""

from __future__ import annotations

import json
import math
import os
import re
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
    at: tuple[int, int] | None = None     # the monitor's own frame, Dock or no Dock


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
            px, py = (int(v) for v in glfw.get_monitor_pos(m))
            name = glfw.get_monitor_name(m)
            name = name.decode(errors="replace") if isinstance(name, bytes) else str(name or "")
            name = name.strip()            # what `match` compares a trimmed value with
        except Exception:  # noqa: BLE001 — as above
            return []      # indices must keep meaning what the config says: all or nothing
        if w <= 0 or h <= 0:
            return []
        out.append(Screen(name or f"screen {i + 1}", x, y, w, h, (px, py)))
    return out


# ---- GRAPH's start zoom (plan 58 SM2) ----
#
# Read off the display the control window opens on. The rule takes the
# display's density and its usable height, never its reported millimetres (a
# 48-inch panel on the owner's Mac says it is 598 mm wide).

ZOOM_HEIGHT = 1080.0    # a display this many points tall starts at 1:1 ...
ZOOM_DENSE = 1.3        # ... and a 2x one, whose points are small, this much bigger
ZOOM_MAX = 1.5          # by eye: 1.38 reads well in a 900-point window, 1.89 held two nodes


def start_zoom(density: float, height: float) -> float:
    """GRAPH's first zoom on a display, in screen points per canvas unit: the
    larger of what a dense panel wants and what the display's height wants,
    from 1 to `ZOOM_MAX`. The height counts by its square root: a taller
    screen is seen from further off, but a window on it needn't fill it."""
    dense = 1.0 + (ZOOM_DENSE - 1.0) * (min(max(density, 1.0), 2.0) - 1.0)
    return min(max(dense, math.sqrt(max(height, 0.0) / ZOOM_HEIGHT)), ZOOM_MAX)


def window_zoom(glfw, win) -> float:
    """`start_zoom` for the display `win` is on: the one its centre is over,
    else the one it lands on. 1.0 when the window system won't say: a launch
    must not die for a zoom."""
    scr = screens(glfw)
    try:
        rect = (*glfw.get_window_pos(win), *glfw.get_window_size(win))
        on = on_screen(rect, scr)
        if on is None:
            return 1.0
        # the monitor's, not the window's: the window's is stale until an event
        # is pumped after it was moved, and this runs before any is
        mon = glfw.get_monitors()[scr.index(on)]
        return start_zoom(float(glfw.get_monitor_content_scale(mon)[0]), on.h)
    except Exception:  # noqa: BLE001 — as above
        return 1.0


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
         scr: list[Screen], spots: dict[str, Rect | None] | None = None) -> None:
    """Write the windowed rects. A None (a minimised window) keeps that
    window's old entry. `spots`: each window's rect by the label of the display
    it's on (`spot`). Atomic — a temp file, then a rename — and a failed
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
    kept = old.get("displays")
    kept = dict(kept) if isinstance(kept, dict) else {}
    for tag, rect in (spots or {}).items():
        new = _entry(rect, scr)
        if new is not None:
            kept[memory(tag)] = new
    if kept:
        doc["displays"] = kept
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


def spot(seen: dict, tag: str, n: int) -> dict | None:
    """Where a window on the display labelled `tag` was, showing output `n`, as `load`
    gave it: its own entry, else that output's old place in ``render``. `place` says
    whether it's any use there."""
    own = seen.get("displays")
    if isinstance(own, dict) and memory(tag) in own:
        return own[memory(tag)]
    old = seen.get("render") or []
    return old[n - 1] if 0 <= n - 1 < len(old) else None


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


def on_screen(rect: Rect, scr: list[Screen]) -> Screen | None:
    """The screen a rect's centre is over, else the one it lands on."""
    return _centre_screen(rect, scr) or _landing(rect, scr)


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
    one asked for: on a screen smaller than the window it overhangs, and a
    clipped size would be remembered at the quit and follow the window to
    a bigger screen. The control window's width is the one exception: it
    is two panes side by side (app.CONTROL_SIZE), wider than a laptop, so
    it is clipped to the screen less a MARGIN each side — the panel keeps
    its width and the desk diagram left of it takes what is left
    (ui.panel_w), so a narrower window is still whole."""
    w, h = int(size[0]), int(size[1])
    x = s.x + MARGIN
    if kind == "control":
        w = max(MIN_SIZE[0], min(w, s.w - 2 * MARGIN))
        x = max(s.x + s.w - w - MARGIN, x)
    return x, s.y + MARGIN, w, h


# ---- the decision ----

def _key(kind: str) -> str:
    return "control_monitor" if kind == "control" else "monitor"


def named(value) -> str:
    """The screen name a config value asks for, "" when it asks by index:
    a string `int()` will not read. "1" is an index written as text."""
    if isinstance(value, str):
        v = value.strip()
        if v:
            try:
                int(v)
            except ValueError:
                return v
    return ""


def _family(name: str) -> str:
    """A screen's name less the " (n)" a Mac may add to tell twins apart
    ("DELL (2)"): that number can follow the plug order, so it is not what
    an ordinal counts. A year in brackets is not such a number."""
    return re.sub(r" \(\d{1,2}\)$", "", name)


def _along(i: int, scr: list[Screen]) -> tuple:
    """Left to right across the desk, then top to bottom: the arrangement
    in System Settings, by the monitor's frame, since a Dock moves the work
    area. `glfw.get_monitors()` order can change with the plug order."""
    s = scr[i]
    return (*(s.at or (s.x, s.y)), i)


def arranged(scr: list[Screen]) -> list[int]:
    """The screens' indices left to right across the desk, then top to bottom."""
    return sorted(range(len(scr)), key=lambda i: _along(i, scr))


def _same(family: str, scr: list[Screen]) -> list[int]:
    """The indices of this family's screens, in the order an ordinal counts."""
    return sorted((i for i, s in enumerate(scr) if _family(s.name) == family),
                  key=lambda i: _along(i, scr))


def _ordinal(want: str) -> tuple[str, int] | None:
    """("TV", 2) for "TV #2"; None when it is not written that way."""
    base, hash_, n = want.rpartition(" #")
    if base and hash_ and n.isascii() and n.isdecimal() and len(n) <= 3 and int(n) >= 1:
        return base, int(n)
    return None


def match(asked: str, scr: list[Screen]) -> int:
    """The index of the screen a name asks for, −1 for none (row 771).

    In this order:
    1. "TV #2": the second of the "TV" family across the desk (`_same`).
       It comes first so that `labels` can always name every screen.
    2. The exact whole name, case and all: "TV" does not find "TV Samsung",
       and "DELL (2)" finds that name whatever the Mac means by it today.
       A screen really called "TV #2", beside two "TV", is "TV #2 #1".
    3. The family: "DELL" finds the first of "DELL (1)" and "DELL (2)".

    `resolve` says what this cannot be sure of."""
    want = asked.strip()
    n = _ordinal(want)
    if n:
        same = _same(n[0], scr)
        if n[1] <= len(same):
            return same[n[1] - 1]
    exact = [i for i, s in enumerate(scr) if s.name == want]
    if exact:
        return min(exact, key=lambda i: _along(i, scr))
    same = _same(want, scr)
    return same[0] if same else -1


def memory(label: str) -> str:
    """What a display's memory goes under, for a label `labels` gave: a lone display and the
    first of a pair are one, so "TV" carries on as "TV #1" when a second is plugged in, and
    back. "DELL (2)" alone is its family's first too: that number can follow the plug order."""
    base, hash_, n = label.rpartition(" #")
    return (_family(base) if hash_ and n == "1" else label if hash_ else _family(label))


def labels(scr: list[Screen]) -> list[str]:
    """What to write in the config for each screen, in `scr`'s order: its
    name when that is enough, and otherwise its family and ordinal. `match`
    finds each screen by its own label, always."""
    out = []
    for i, s in enumerate(scr):
        fam = _family(s.name)
        same = _same(fam, scr)
        if len(same) > 1:
            out.append(f"{fam} #{same.index(i) + 1}")
        else:
            out.append(s.name if match(s.name, scr) == i else f"{fam} #1")
    return out


def resolve(asked: str, scr: list[Screen]) -> tuple[int, str]:
    """`match`, and what to say about it: (index, words or ""). The words
    finish a sentence that begins with the config key and its value. The
    one place a name becomes an index: each value is resolved once."""
    want = asked.strip()
    i = match(want, scr)
    tags = labels(scr)
    n = _ordinal(want)
    many = _same(n[0], scr) if n else []
    if i < 0:
        have = f"connected: {', '.join(tags) or 'none'}"
        if many:
            return -1, f"asks for number {n[1]} of {n[0]!r}, and {len(many)} connected ({have})"
        return -1, f"matches no screen ({have})"
    if n and many == [i]:
        # a twin alone: the left of two and the right of two look the same
        return i, (f"asks for number 1 of {n[0]!r}, and only one is connected, which may be "
                   f"either of a pair — using it; if there is only ever one, write {tags[i]!r}")
    same = _same(_family(want), scr)
    if len(same) > 1:
        each = ", ".join(tags[k] for k in same)
        if sum(s.name == want for s in scr) != 1:
            return i, f"is {len(same)} screens ({each}) — using the first; say which to be sure"
        if _family(want) != want:
            return i, (f"is the Mac's own number for one of {len(same)} screens ({each}), and it "
                       f"can follow the plug order — say {tags[i]!r} to be sure")
    return i, ""


def settle(output: dict, scr: list[Screen]) -> list[str]:
    """`[output] monitor` and `control_monitor` as indices, where they are
    names: once, at the launch, in place, with the notes to show."""
    notes = []
    for key in ("monitor", "control_monitor"):
        name = named(output.get(key))
        if name:
            output[key], said = resolve(name, scr)
            if said:
                tail = " — using the last position" if output[key] < 0 else ""
                notes.append(f"config: [output] {key} = {name!r} {said}{tail}")
    return notes


def kept(key: str, monitor) -> tuple[int | str, str]:
    """A config value as `config.load` keeps it, before any window system:
    a name stays a name for the launch to `resolve`, and anything else is
    `read`."""
    name = named(monitor)
    return (name, "") if name else read(key, monitor)


def read(key: str, monitor) -> tuple[int, str]:
    """A config number as a screen index: (index, note or ""). The index
    is what `int()` reads of it, and −1 for anything under −1; a value
    `int()` will not read (None, a NaN, a name nobody resolved) is −1 with
    the note. The one reading of ``[output] monitor`` / ``control_monitor``
    (plan 16 WP7) — `config.load`, `place` below and `app._make_output` all
    go through it, so a window's screen and the one fullscreen covers agree.
    It never raises. Whether a screen has that index is `place`'s to say."""
    try:
        return max(int(monitor), -1), ""
    except (TypeError, ValueError, OverflowError):
        return -1, (f"config: [output] {key} = {monitor!r} is not a screen index — "
                    "using the last position")


def index(monitor, n: int | None = None) -> int:
    """`read`'s index alone; with `n` screens connected, −1 for an index
    none of them has. Says nothing: the notes are `read`'s and `place`'s."""
    i, _ = read("monitor", monitor)
    return -1 if n is not None and i >= n else i


def place(kind: str, size: tuple[int, int], scr: list[Screen],
          monitor: int, remembered: dict | None, what: str = "") -> tuple[Rect, str]:
    """Where one window opens: (rect, note or "").

    `kind` is "render" or "control"; `monitor` is that window's config
    index (−1: no say; `settle` has made any name one); `remembered` is its entry from the file, or None.
    `what` names the window in the notes in place of `kind` ("output 2",
    plan 21: one call per render output); it changes nothing else.

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
    # read as app._make_output reads it for `output.monitor`
    monitor, note = read(_key(kind), monitor)
    if note:
        notes.append(note)
    if monitor >= len(scr):
        n = len(scr)
        have = "0" if n == 1 else f"0–{n - 1}"
        key = f"{what} monitor" if what else f"[output] {_key(kind)}"
        notes.append(f"config: {key} = {monitor}, but {n} "
                     f"screen{'s are' if n != 1 else ' is'} connected ({have}) — "
                     "using the last position")
    elif monitor >= 0:
        target = scr[monitor]
    rect = _rect(remembered)
    if remembered is not None and rect is None:
        notes.append(f"placement: the {what or kind} window's entry in {FILE} is not a rect — "
                     "ignored")
    if rect is not None:
        fitted = _fit(rect, scr)
        if fitted is None:
            notes.append(_gone(what or kind, remembered, rect, target or scr[0], scr))
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
