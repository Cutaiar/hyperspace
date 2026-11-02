"""The on-screen pad's other readouts (plan 42's follow-up): the same pad,
three more ways to read it, picked by ``ui.pad_view`` beside the map.

  map       ui_pad's own picture: every control at its place, named with
            what it does — the mapping view (drawn there, not here)
  faithful  the controller drawn from above, every control lit where it
            sits: the touchpad with each finger, the light bar's colour,
            the player lights, the back and Fn buttons on an Edge
  lanes     every routing lane under the name a row uses (``axis:LX``,
            ``touch:pinch``, ``motion:shake``), its value as a bar and
            what it is mapped to, then what the pad is being sent
  cockpit   for a glance mid-set: big stick dials with a trail and the
            trigger round each as an arc (its resistance the outer
            band), the tilt as a level, the back buttons loud on the
            edges, the last presses scrolling along the foot

Designed in the browser lab (`prototypes/edge-lab/`, its three readouts)
and drawn in the room ui_pad gives it, so the desk under it never moves:
Faithful and Cockpit by `ui_pad_nvg` (the lab's canvas drawing ported to
NanoVG, into a texture shown here) wherever the control window's GL takes
it, else on the draw list by the versions here; Lanes always here. Read-only, like the map: a hover
names a control, its mapping and its source; Learn pad is still the way
onto one.

Everything a view reads comes through `read` (a `Reading`), so a pad that
has no touchpad, no sensors or no outputs — an Xbox pad, a test's fake —
draws the parts it has. A function over the Panel, like ui_pad: its
memory (the stick trails, the ticker) lives on the panel, and a save of
this file lands live (hotreload.MODULES).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from imgui_bundle import imgui

from . import gamepad, ui, ui_desk, ui_pad_nvg
from .pads import gesture, models

VIEWS = ("map", "faithful", "lanes", "cockpit")
VIEW_LABELS = ("Map", "Faithful", "Lanes", "Cockpit")
VIEW_TIP = ("How the pad window reads the pad. Map: every control at its place, "
            "named with what it does. Faithful: the controller from above, lit where "
            "pressed. Lanes: every lane a row can name, its value and its mapping. "
            "Cockpit: big dials, trigger arcs, the tilt, the last presses — for a "
            "glance mid-set. Click the view's name on the pad window to step through them.")

# colours: the panel's, and a few of the lab's
_DARK = imgui.ImVec4(0.09, 0.09, 0.10, 1.0)
_BODY = imgui.ImVec4(0.13, 0.13, 0.15, 1.0)
_WELL = imgui.ImVec4(0.17, 0.17, 0.19, 1.0)
_OFF = imgui.ImVec4(0.34, 0.34, 0.37, 1.0)
_STICK = imgui.ImVec4(0.42, 0.70, 1.0, 1.0)
_TRIG = imgui.ImVec4(1.0, 0.76, 0.35, 1.0)
_RESIST = imgui.ImVec4(1.0, 0.55, 0.20, 0.55)
_BLACK = imgui.ImVec4(0, 0, 0, 1)
# each face button's own ink: a DualSense's and an Xbox pad's
_SONY_INK = {"Y": (0.30, 0.80, 0.62), "B": (0.95, 0.38, 0.42), "A": (0.48, 0.64, 0.96),
             "X": (0.86, 0.52, 0.82)}
_XBOX_INK = {"Y": (0.98, 0.80, 0.25), "B": (0.95, 0.30, 0.30), "A": (0.40, 0.78, 0.35),
             "X": (0.30, 0.55, 0.95)}

TRAIL = 18                # a stick's trail in the cockpit: this many frames
TICKER_S = 3.0            # a press stays on the cockpit's ticker this long
TICKER_N = 6
LANE_PX = (12.0, 11.0, 10.0)   # the lanes' type sizes, the largest that fits


def _v(x: float, y: float) -> imgui.ImVec2:
    return imgui.ImVec2(x, y)


def _col(c, a: float | None = None) -> int:
    if isinstance(c, tuple):
        return ui.u32(imgui.ImVec4(*c, 1.0 if a is None else a))
    if a is None:
        return ui.u32(c)
    return ui.u32(imgui.ImVec4(c.x, c.y, c.z, a))


# ---------------------------------------------------------------- what is read

@dataclass
class Reading:
    """One frame of the pad as the views draw it."""

    on: bool = False
    model: object | None = None
    down: frozenset = frozenset()          # canonical button names held
    hat: int = 0
    axes: dict = field(default_factory=dict)   # LX … RT as routing lanes, 0–1
    touch: dict | None = None              # touch:… lanes, NaN where no finger
    motion: dict | None = None             # motion:… lanes
    degrees: tuple | None = None           # roll, pitch, yaw in degrees
    effects: object | None = None          # what the pad is being sent (sony.Effects)
    battery: int = -1
    link: str = ""

    @property
    def sony(self) -> bool:
        return getattr(self.model, "family", "") == "sony"

    def has(self, cap: str) -> bool:
        return models.is_model(self.model) and self.model.has(cap)

    def glyph(self, name: str, default: str) -> str:
        return models.glyph(self.model if models.is_model(self.model) else None, name, default)


def _lanes_of(pad, attr: str, names) -> dict | None:
    read = getattr(pad, attr, None)
    got = read() if callable(read) else None
    return dict(zip(names, got, strict=True)) if got is not None else None


def read(pad) -> Reading:
    """The pad as the views read it — whatever it lacks left empty."""
    if pad is None:
        return Reading(axes=dict(zip(gamepad.AXES, gamepad.AXIS_RESTS, strict=True)))
    on = bool(getattr(pad, "on", False))
    model = gamepad.shown_model(pad)
    named = getattr(pad, "buttons_named", None)
    named = named if isinstance(named, dict) else gamepad.BUTTONS
    down = frozenset(n for n, i in named.items() if on and pad.down(i))
    lanes = list(pad.lanes())[:6] if on else list(gamepad.AXIS_RESTS)
    touch = _lanes_of(pad, "touch_lanes", gesture.TOUCH_LANES) if on else None
    motion = _lanes_of(pad, "motion_lanes", gesture.MOTION_LANES) if on else None
    m = getattr(pad, "motion", None)
    degrees = None
    if motion is not None and isinstance(getattr(m, "roll", None), float):
        degrees = (m.roll, m.pitch, m.yaw)
    bat = getattr(getattr(pad, "report", None), "battery", -1)
    return Reading(on=on, model=model, down=down,
                   hat=int(getattr(pad, "hat", 0) or 0) if on else 0,
                   axes=dict(zip(gamepad.AXES, lanes, strict=True)), touch=touch,
                   motion=motion, degrees=degrees, effects=getattr(pad, "effects", None),
                   battery=bat if isinstance(bat, int) else -1,
                   link=str(getattr(pad, "link", "") or ""))


@dataclass
class Ctx:
    """What a view draws with: the panel, the draw list, its room, the
    reading, and `says(source)` → (the words, whether a row says them)."""

    panel: object
    dl: object
    x: float
    y: float
    w: float
    h: float
    r: Reading
    says: object
    hits: list = field(default_factory=list)     # (x0, y0, x1, y1, source) for the hover

    def hit(self, x0, y0, x1, y1, source: str) -> None:
        self.hits.append((x0, y0, x1, y1, source))


def _state(panel) -> dict:
    return panel.__dict__.setdefault("_pad_views", {})


def _text_left(dl, s: str, x: float, y: float, color: int, room: float) -> None:
    """`s` at (x, y), cut with … to fit `room` px."""
    if room <= 4 or not s:
        return
    if imgui.calc_text_size(s).x > room:
        while s and imgui.calc_text_size(s + "…").x > room:
            s = s[:-1]
        s = s + "…" if s else ""
    if s:
        dl.add_text(_v(x, y), color, s)


def _centred(dl, s: str, cx: float, cy: float, color: int, room: float = 1e9) -> None:
    ui_desk._text(dl, s, cx, cy, color, room)


def _held(r: Reading, source: str) -> bool:
    scheme, _, name = source.partition(":")
    if scheme == "pad":
        return name in r.down
    if scheme == "hat":
        return bool(r.hat & gamepad.HATS.get(name, 0))
    return False


def _button(c: Ctx, source: str, glyph: str, x0, y0, x1, y1, round_=4.0,
            ink=None, round_shape=False) -> None:
    """A button face: lit red while held; the glyph in its own ink when
    the face gives one, else the panel's (bright when a row maps it)."""
    held = _held(c.r, source)
    words, _row = c.says(source)
    face = ui.RED if held else (_OFF if words else _DARK)
    edge = _col(ui.DIM if words else ui.LINE)
    if round_shape:
        cx, cy, rad = (x0 + x1) / 2, (y0 + y1) / 2, min(x1 - x0, y1 - y0) / 2
        c.dl.add_circle_filled(_v(cx, cy), rad, _col(face))
        c.dl.add_circle(_v(cx, cy), rad, edge if ink is None else _col(ink), 0, 1.5)
    else:
        c.dl.add_rect_filled(_v(x0, y0), _v(x1, y1), _col(face), round_)
        c.dl.add_rect(_v(x0, y0), _v(x1, y1), edge, round_)
    color = _col(_BLACK) if held else _col(ink) if ink is not None else _col(
        ui.TEXT if words else ui.FAINT)
    _centred(c.dl, glyph, (x0 + x1) / 2, (y0 + y1) / 2, color, x1 - x0 + 6)
    c.hit(x0, y0, x1, y1, source)


def _well(c: Ctx, cx, cy, rad, which: str, held: bool) -> None:
    """A stick's well, the stick in it."""
    xa, ya = ("LX", "LY") if which == "L" else ("RX", "RY")
    dx, dy = 2 * c.r.axes[xa] - 1, 1 - 2 * c.r.axes[ya]
    c.dl.add_circle_filled(_v(cx, cy), rad, _col(_WELL))
    c.dl.add_circle(_v(cx, cy), rad, _col(ui.RED if held else ui.LINE), 0, 1.5)
    knob = max(3.0, rad * 0.32)
    col = ui.RED if held else _STICK if c.r.on else ui.DIM
    c.dl.add_circle_filled(_v(cx + dx * (rad - knob), cy + dy * (rad - knob)), knob, _col(col))
    c.hit(cx - rad, cy - rad, cx + rad, cy + rad, f"pad:{which}STICK")


def _touchpad(c: Ctx, x0, y0, x1, y1) -> None:
    held = _held(c.r, "pad:TOUCH")
    c.dl.add_rect_filled(_v(x0, y0), _v(x1, y1), _col(ui.RED if held else _DARK), 5.0)
    c.dl.add_rect(_v(x0, y0), _v(x1, y1), _col(ui.LINE), 5.0)
    t = c.r.touch or {}
    rad = max(2.5, 0.07 * (y1 - y0))
    for xs, ys in (("x", "y"), ("x2", "y2")):
        x, y = t.get(xs), t.get(ys)
        if x is None or y is None or not (math.isfinite(x) and math.isfinite(y)):
            continue
        c.dl.add_circle_filled(_v(x0 + x * (x1 - x0), y0 + (1 - y) * (y1 - y0)), rad,
                               _col(_BLACK if held else _STICK))
    c.hit(x0, y0, x1, y1, "pad:TOUCH")


def _tilt(c: Ctx, cx, cy, rad, horizon: bool = False) -> None:
    """The tilt: a level — a dot where the pad leans (right side down to
    the right, the far edge up upward), or a horizon that rolls with it;
    the ring red on a shake."""
    m = c.r.motion or {}
    c.dl.add_circle_filled(_v(cx, cy), rad, _col(_WELL))
    shake = bool(m.get("shake"))
    c.dl.add_circle(_v(cx, cy), rad, _col(ui.RED if shake else ui.LINE), 0, 2.0 if shake else 1.0)
    if not m:
        c.dl.add_line(_v(cx - rad, cy), _v(cx + rad, cy), _col(ui.LINE))
        return
    roll, pitch = 2 * m["roll"] - 1, 1 - 2 * m["pitch"]
    if horizon:
        a = roll * math.radians(gesture.TILT_DEG)
        ox, oy = math.cos(a) * rad * 0.9, math.sin(a) * rad * 0.9
        py = cy + pitch * rad * 0.6
        c.dl.add_line(_v(cx - ox, py - oy), _v(cx + ox, py + oy), _col(_STICK), 2.0)
    else:
        c.dl.add_line(_v(cx - rad, cy), _v(cx + rad, cy), _col(ui.LINE))
        c.dl.add_line(_v(cx, cy - rad), _v(cx, cy + rad), _col(ui.LINE))
        knob = max(3.0, rad * 0.2)
        c.dl.add_circle_filled(_v(cx + roll * (rad - knob), cy + pitch * (rad - knob)), knob,
                               _col(_STICK))
    c.hit(cx - rad, cy - rad, cx + rad, cy + rad, "motion:roll")


def _light(r: Reading):
    """The light bar's colour now, as an ImVec4, or None (nothing sent)."""
    rgb = getattr(r.effects, "light", None)
    if not rgb or not r.has("light"):
        return None
    return imgui.ImVec4(*(min(255, max(0, int(v))) / 255 for v in rgb), 1.0)


def _players(c: Ctx, cx, cy, step, rad) -> None:
    bits = int(getattr(c.r.effects, "players", 0) or 0) if c.r.has("players") else 0
    for k in range(5):
        on = bool(bits & (1 << k))
        c.dl.add_circle_filled(_v(cx + (k - 2) * step, cy), rad,
                               _col(ui.TEXT if on else ui.LINE))


def _hover(c: Ctx) -> None:
    """The hover over the control under the pointer: its mapping."""
    if not imgui.is_window_hovered():
        return
    m = imgui.get_mouse_pos()
    for x0, y0, x1, y1, source in reversed(c.hits):
        if x0 <= m.x < x1 and y0 <= m.y < y1:
            words, row = c.says(source)
            name = gamepad.control_name(source) or source
            if row is not None:
                tip = f"{name} · {words} · {row.describe()}"
            elif words:
                tip = f"{name} · {words} — the app's own, no row in the table"
            else:
                tip = f"{name} · free — right-click a param → Learn pad, then use it here"
            ui.tooltip(tip)
            return


# ---------------------------------------------------------------- faithful

def faithful(c: Ctx) -> None:
    """The controller from above, fitted in the room at its own shape."""
    aspect = 1.55
    w = min(c.w, c.h * aspect)
    h = w / aspect
    ox, oy = c.x + (c.w - w) / 2, c.y + (c.h - h) / 2
    r = c.r

    def P(u: float, v: float) -> imgui.ImVec2:
        return _v(ox + u * w, oy + v * h)

    def box(u0, v0, u1, v1) -> tuple:
        return ox + u0 * w, oy + v0 * h, ox + u1 * w, oy + v1 * h
    dl = c.dl
    body = _col(_BODY)
    # the grips, then the body over them
    for u in (0.2, 0.8):
        dl.add_circle_filled(P(u, 0.7), 0.16 * w, body)
    dl.add_rect_filled(P(0.06, 0.14), P(0.94, 0.66), body, 0.12 * h)
    dl.add_rect(P(0.06, 0.14), P(0.94, 0.66), _col(ui.LINE), 0.12 * h)
    # the triggers as bars above the bumpers, the bumpers
    for side, u0, u1 in (("LT", 0.12, 0.30), ("RT", 0.70, 0.88)):
        x0, y0, x1, y1 = box(u0, 0.0, u1, 0.055)
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), _col(_DARK), 3.0)
        fill = r.axes[side]
        if fill > 0.005:
            dl.add_rect_filled(_v(x0, y0), _v(x0 + fill * (x1 - x0), y1), _col(_TRIG), 3.0)
        dl.add_rect(_v(x0, y0), _v(x1, y1), _col(ui.LINE), 3.0)
        _centred(dl, r.glyph(side, side), (x0 + x1) / 2, (y0 + y1) / 2, _col(ui.TEXT))
        c.hit(x0, y0, x1, y1, f"axis:{side}")
    for name, u0, u1 in (("LB", 0.12, 0.30), ("RB", 0.70, 0.88)):
        _button(c, f"pad:{name}", r.glyph(name, name), *box(u0, 0.07, u1, 0.125))
    if r.sony:
        _faithful_sony(c, P, box, w, h)
    else:
        _faithful_xbox(c, P, box, w)
    # the corner words: model and link, battery
    words = getattr(r.model, "name", "") or ("no pad" if not r.on else "pad")
    if r.link:
        words += f" · {r.link}"
    _text_left(dl, words, ox + 4, oy + h - imgui.get_text_line_height() - 2, _col(ui.FAINT), w * 0.5)
    if r.battery > 0:
        s = f"{min(100, r.battery * 10)} %"
        _text_left(dl, s, ox + w - imgui.calc_text_size(s).x - 4, oy + 2, _col(ui.FAINT), w)


def _faithful_sony(c: Ctx, P, box, w: float, h: float) -> None:
    r, dl = c.r, c.dl
    x0, y0, x1, y1 = box(0.33, 0.16, 0.67, 0.42)
    _touchpad(c, x0, y0, x1, y1)
    light = _light(r)
    if light is not None:
        for u0 in (0.312, 0.676):
            lx0, ly0, lx1, ly1 = box(u0, 0.18, u0 + 0.012, 0.40)
            dl.add_rect_filled(_v(lx0, ly0), _v(lx1, ly1), _col(light), 2.0)
    _players(c, *P(0.5, 0.455), 0.022 * w, max(1.5, 0.006 * w))
    for name, u0 in (("VIEW", 0.245), ("MENU", 0.695)):
        bx0, by0, bx1, by1 = box(u0, 0.17, u0 + 0.06, 0.205)
        _button(c, f"pad:{name}", "", bx0, by0, bx1, by1, 3.0)
        word = r.glyph(name, name).capitalize()
        _centred(dl, word, (bx0 + bx1) / 2, by1 + imgui.get_text_line_height() * 0.6,
                 _col(ui.FAINT), (bx1 - bx0) * 2.2)
    # the D-pad, the face diamond (each in its own ink)
    cx, cy = P(0.2, 0.33).x, P(0.2, 0.33).y
    s = 0.04 * w
    for name, dx, dy, g in (("UP", 0, -1, "↑"), ("DOWN", 0, 1, "↓"), ("LEFT", -1, 0, "←"),
                            ("RIGHT", 1, 0, "→")):
        bx, by = cx + dx * s * 1.05, cy + dy * s * 1.05
        _button(c, f"hat:{name}", g, bx - s / 2, by - s / 2, bx + s / 2, by + s / 2, 3.0)
    cx, cy = P(0.8, 0.33).x, P(0.8, 0.33).y
    d, rad = 0.055 * w, 0.023 * w
    for name, dx, dy in (("Y", 0, -1), ("B", 1, 0), ("A", 0, 1), ("X", -1, 0)):
        bx, by = cx + dx * d, cy + dy * d
        _button(c, f"pad:{name}", r.glyph(name, name), bx - rad, by - rad, bx + rad, by + rad,
                ink=_SONY_INK[name], round_shape=True)
    # the sticks, the PS button and the mic between them
    rad = 0.062 * w
    for which, u in (("L", 0.36), ("R", 0.64)):
        p = P(u, 0.53)
        _well(c, p.x, p.y, rad, which, f"{which}STICK" in r.down)
    p = P(0.5, 0.52)
    _button(c, "pad:GUIDE", "PS", p.x - 0.02 * w, p.y - 0.02 * w, p.x + 0.02 * w, p.y + 0.02 * w,
            round_shape=True)
    _button(c, "pad:SHARE", r.glyph("SHARE", "MIC"), *box(0.475, 0.575, 0.525, 0.61), 3.0)
    if r.has("fn"):
        _button(c, "pad:LFN", "Fn", *box(0.335, 0.62, 0.385, 0.655), 3.0)
        _button(c, "pad:RFN", "Fn", *box(0.615, 0.62, 0.665, 0.655), 3.0)
    if r.has("back"):
        _button(c, "pad:LP", r.glyph("LP", "L4"), *box(0.15, 0.76, 0.25, 0.84), 4.0)
        _button(c, "pad:RP", r.glyph("RP", "R4"), *box(0.75, 0.76, 0.85, 0.84), 4.0)
    if r.has("motion"):
        p = P(0.5, 0.78)
        _tilt(c, p.x, p.y, min(0.06 * w, 0.12 * h))


def _faithful_xbox(c: Ctx, P, box, w: float) -> None:
    r = c.r
    rad = 0.062 * w
    for which, u, v in (("L", 0.26, 0.33), ("R", 0.62, 0.53)):
        p = P(u, v)
        _well(c, p.x, p.y, rad, which, f"{which}STICK" in r.down)
    cx, cy = P(0.38, 0.53).x, P(0.38, 0.53).y
    s = 0.04 * w
    for name, dx, dy, g in (("UP", 0, -1, "↑"), ("DOWN", 0, 1, "↓"), ("LEFT", -1, 0, "←"),
                            ("RIGHT", 1, 0, "→")):
        bx, by = cx + dx * s * 1.05, cy + dy * s * 1.05
        _button(c, f"hat:{name}", g, bx - s / 2, by - s / 2, bx + s / 2, by + s / 2, 3.0)
    cx, cy = P(0.76, 0.33).x, P(0.76, 0.33).y
    d, rb = 0.055 * w, 0.023 * w
    for name, dx, dy in (("Y", 0, -1), ("B", 1, 0), ("A", 0, 1), ("X", -1, 0)):
        bx, by = cx + dx * d, cy + dy * d
        _button(c, f"pad:{name}", name, bx - rb, by - rb, bx + rb, by + rb,
                ink=_XBOX_INK[name], round_shape=True)
    _button(c, "pad:VIEW", "BACK", *box(0.41, 0.26, 0.47, 0.30), 3.0)
    _button(c, "pad:MENU", "START", *box(0.53, 0.26, 0.59, 0.30), 3.0)
    p = P(0.5, 0.2)
    _button(c, "pad:GUIDE", "X", p.x - 0.025 * w, p.y - 0.025 * w, p.x + 0.025 * w,
            p.y + 0.025 * w, round_shape=True)
    _button(c, "pad:SHARE", "SHR", *box(0.475, 0.33, 0.525, 0.365), 3.0)


# ---------------------------------------------------------------- lanes

def _lane_rows(r: Reading) -> list[tuple]:
    """(group, rows): each row (source, glyph, value or None, rest, bipolar)."""
    out = []
    out.append(("sticks", [(f"axis:{n}", r.glyph(n, n), r.axes[n], 0.5, True)
                           for n in ("LX", "LY", "RX", "RY")]))
    out.append(("triggers", [(f"axis:{n}", r.glyph(n, n), r.axes[n], 0.0, False)
                             for n in ("LT", "RT")]))
    out.append(("d-pad", [(f"hat:{n}", g, 1.0 if r.hat & gamepad.HATS[n] else 0.0, 0.0, False)
                          for n, g in (("UP", "↑"), ("RIGHT", "→"), ("DOWN", "↓"),
                                       ("LEFT", "←"))]))
    names = list(gamepad.BUTTONS)
    for cap, extra in (("touch", ("TOUCH",)), ("back", ("LP", "RP")), ("fn", ("LFN", "RFN"))):
        if r.has(cap):
            names += list(extra)
    out.append(("buttons", [(f"pad:{n}", r.glyph(n, n), 1.0 if n in r.down else 0.0, 0.0, False)
                            for n in names]))
    for scheme, names_, rests, bip, have in (
            (gamepad.TOUCH_SCHEME, gesture.TOUCH_LANES, gesture.TOUCH_RESTS,
             gesture.TOUCH_BIPOLAR, r.touch),
            (gamepad.MOTION_SCHEME, gesture.MOTION_LANES, gesture.MOTION_RESTS,
             gesture.MOTION_BIPOLAR, r.motion)):
        if not r.has(scheme):
            continue
        rows = []
        for n, rest in zip(names_, rests, strict=True):
            v = have.get(n) if have else None
            rows.append((f"{scheme}:{n}", "", v if v is not None and math.isfinite(v) else None,
                         rest, n in bip))
        out.append((scheme, rows))
    e = r.effects
    if e is not None and r.has("light"):
        light = tuple(getattr(e, "light", (0, 0, 0)))
        bits = int(getattr(e, "players", 0) or 0)

        def trig(t) -> float:
            return float(getattr(t, "strength", 0.0) or 0.0) if getattr(t, "mode", "off") != "off" else 0.0
        out.append(("out (sent now)", [
            ("light", "#{:02x}{:02x}{:02x}".format(*light), max(light) / 255, 0.0, False),
            ("players", "", (bits).bit_count() / 5, 0.0, False),
            ("rumble heavy", "", float(getattr(e, "rumble_low", 0.0)), 0.0, False),
            ("rumble light", "", float(getattr(e, "rumble_high", 0.0)), 0.0, False),
            ("L2 resists", "", trig(getattr(e, "left", None)), 0.0, False),
            ("R2 resists", "", trig(getattr(e, "right", None)), 0.0, False),
            ("mic light", "", 1.0 if getattr(e, "mic", 0) else 0.0, 0.0, False)]))
    return out


def lanes(c: Ctx) -> None:
    """Every lane in columns, the groups in order: the address a row
    names, its glyph, a bar from its rest, the value, what maps it. The
    largest type that fits (`LANE_PX`); what never fits is cut at the foot."""
    groups = _lane_rows(c.r)
    n_lines = sum(1 + len(rows) for _, rows in groups)
    chosen = None
    for px in LANE_PX:
        imgui.push_font(ui._FONTS["ui"], px)
        lh = imgui.get_text_line_height() + 2
        imgui.pop_font()
        per_col = max(1, int(c.h // lh))
        cols = math.ceil(n_lines / per_col)
        if c.w / cols >= 18 * px or px == LANE_PX[-1]:
            chosen = (px, lh, per_col, cols)
            break
    px, lh, per_col, cols = chosen
    col_w = c.w / max(1, cols)
    imgui.push_font(ui._FONTS["ui"], px)
    try:
        lines: list = []
        for g, rows in groups:
            lines.append(("head", g))
            lines += [("row", row) for row in rows]
        dl = c.dl
        for k, (kind, item) in enumerate(lines[:per_col * cols]):
            col, at = divmod(k, per_col)
            x = c.x + col * col_w
            y = c.y + at * lh
            if kind == "head":
                _text_left(dl, item, x + 2, y + 1, _col(ui.DIM), col_w - 8)
                dl.add_line(_v(x + 2, y + lh - 1), _v(x + col_w - 8, y + lh - 1), _col(ui.LINE))
                continue
            _lane_line(c, item, x, y, col_w, lh)
        if len(lines) > per_col * cols:
            _text_left(dl, "…", c.x + c.w - 12, c.y + c.h - lh, _col(ui.FAINT), 12)
    finally:
        imgui.pop_font()


def _lane_widths(col_w: float) -> tuple[float, float, float, float]:
    """(name, glyph, bar, value) widths in a column `col_w` wide: the name
    as wide as the longest address needs (never past 0.42 of the column),
    the value as "0.00" is, the glyph only where the column is wide, the
    mapping the rest."""
    name_w = min(0.42 * col_w, imgui.calc_text_size("motion:spin.pitch").x + 8)
    val_w = imgui.calc_text_size("0.00").x + 8
    glyph_w = imgui.calc_text_size("OPTIONS").x + 6 if col_w > 300 else 0.0
    bar_w = max(24.0, min(0.22 * col_w, 90.0))
    return name_w, glyph_w, bar_w, val_w


def _lane_line(c: Ctx, item, x, y, col_w, lh) -> None:
    source, glyph, value, rest, bipolar = item
    dl = c.dl
    name_w, glyph_w, bar_w, val_w = _lane_widths(col_w)
    words, row = c.says(source) if ":" in source else ("", None)
    live = value is not None
    ink = _col(ui.TEXT if live else ui.FAINT)
    _text_left(dl, source, x + 2, y, ink, name_w - 4)
    if glyph_w:
        _text_left(dl, glyph, x + name_w, y, _col(ui.DIM), glyph_w - 2)
    bx0 = x + name_w + glyph_w
    bx1 = bx0 + bar_w - 4
    by0, by1 = y + lh * 0.25, y + lh * 0.75
    dl.add_rect_filled(_v(bx0, by0), _v(bx1, by1), _col(_DARK), 2.0)
    if live:
        v = min(1.0, max(0.0, value))
        a = bx0 + (rest if bipolar else 0.0) * (bx1 - bx0)
        b = bx0 + v * (bx1 - bx0)
        if abs(b - a) >= 1:
            lit = _TRIG if source in ("axis:LT", "axis:RT") or not bipolar else _STICK
            if source.startswith(("pad:", "hat:")) and value >= 0.5:
                lit = ui.RED
            if source == "light":
                lit = _light(c.r) or lit
            dl.add_rect_filled(_v(min(a, b), by0), _v(max(a, b), by1), _col(lit), 2.0)
        if bipolar:
            mid = bx0 + rest * (bx1 - bx0)
            dl.add_line(_v(mid, by0 - 1), _v(mid, by1 + 1), _col(ui.LINE))
    vs = f"{value:.2f}" if live else "—"
    vx = bx1 + 6
    _text_left(dl, vs, vx, y, ink, val_w)
    lx = vx + val_w
    shown = words or (glyph if source == "light" else "")
    _text_left(dl, shown, lx, y, _col(ui.TEXT if row is not None else ui.DIM), x + col_w - lx - 6)
    if ":" in source:
        c.hit(x, y, x + col_w, y + lh, source)


# ---------------------------------------------------------------- cockpit

def _arc(dl, cx, cy, rad, a0, a1, color, thick) -> None:
    if a1 - a0 < 1e-3:
        return
    dl.path_clear()
    dl.path_arc_to(_v(cx, cy), rad, a0, a1, max(8, int((a1 - a0) * 12)))
    dl.path_stroke(color, thick)


ARC0, ARC1 = math.radians(150), math.radians(390)     # a trigger's sweep: open at the foot


def _dial(c: Ctx, cx, cy, rad, which: str, trig: str, resist: float, trail: list) -> None:
    """A stick's dial: its trail, the stick, the trigger as an arc round
    it, the resistance the pad is sent as the outer band."""
    dl = c.dl
    dl.add_circle_filled(_v(cx, cy), rad, _col(_WELL))
    dl.add_circle(_v(cx, cy), rad, _col(ui.LINE), 0, 1.0)
    xa, ya = ("LX", "LY") if which == "L" else ("RX", "RY")
    dx, dy = 2 * c.r.axes[xa] - 1, 1 - 2 * c.r.axes[ya]
    knob = max(4.0, rad * 0.12)
    pos = (cx + dx * (rad - knob), cy + dy * (rad - knob))
    trail.append((dx, dy))
    del trail[:-TRAIL]
    for k, (tx, ty) in enumerate(trail[:-1]):
        a = (k + 1) / len(trail)
        dl.add_circle_filled(_v(cx + tx * (rad - knob), cy + ty * (rad - knob)),
                             knob * (0.3 + 0.5 * a), _col(_STICK, 0.25 * a))
    held = f"{which}STICK" in c.r.down
    dl.add_circle_filled(_v(*pos), knob, _col(ui.RED if held else _STICK if c.r.on else ui.DIM))
    c.hit(cx - rad, cy - rad, cx + rad, cy + rad, f"axis:{xa}")
    t = c.r.axes[trig]
    _arc(dl, cx, cy, rad + 8, ARC0, ARC1, _col(_DARK), 6.0)
    _arc(dl, cx, cy, rad + 8, ARC0, ARC0 + t * (ARC1 - ARC0), _col(_TRIG), 6.0)
    if resist > 0:
        _arc(dl, cx, cy, rad + 16, ARC0, ARC0 + resist * (ARC1 - ARC0), _col(_RESIST), 4.0)
    c.hit(cx - rad - 18, cy - rad - 18, cx + rad + 18, cy - rad + 4, f"axis:{trig}")
    label = f"{c.r.glyph(trig, trig)} {round(t * 100)}%"
    if resist > 0:
        label += f" · resists {round(resist * 8)}/8"
    _centred(dl, label, cx, cy + rad + 20, _col(_TRIG if t > 0.02 else ui.DIM))


def cockpit(c: Ctx) -> None:
    """Big dials, the tilt and touchpad between them, the back buttons on
    the edges, the D-pad and the face at the foot, the last presses."""
    r, dl = c.r, c.dl
    st = _state(c.panel)
    light = _light(r)
    top = c.y
    if light is not None:
        dl.add_rect_filled(_v(c.x, top), _v(c.x + c.w, top + 4), _col(light), 2.0)
    top += 8
    foot_h = imgui.get_text_line_height() + 8
    body_h = c.h - (top - c.y) - foot_h
    edge_w = 0.1 * c.w if r.has("back") else 0.0
    inner_x, inner_w = c.x + edge_w, c.w - 2 * edge_w
    rad = max(10.0, min(0.15 * inner_w, 0.28 * body_h))
    dial_y = top + rad + 18
    e = r.effects

    def resist(side) -> float:
        t = getattr(e, side, None)
        return float(getattr(t, "strength", 0.0) or 0.0) if getattr(t, "mode", "off") != "off" else 0.0
    trails = st.setdefault("trails", {"L": [], "R": []})
    _dial(c, inner_x + 0.2 * inner_w, dial_y, rad, "L", "LT", resist("left"), trails["L"])
    _dial(c, inner_x + 0.8 * inner_w, dial_y, rad, "R", "RT", resist("right"), trails["R"])
    # between them: the tilt (a rolling horizon), the touchpad, the middle chips
    mid = inner_x + inner_w / 2
    tr = max(8.0, min(0.09 * inner_w, 0.18 * body_h))
    if r.has("motion"):
        _tilt(c, mid, top + tr + 4, tr, horizon=True)
        if r.degrees is not None:
            s = f"roll {r.degrees[0]:+.0f}°  pitch {r.degrees[1]:+.0f}°"
            _centred(dl, s, mid, top + 2 * tr + 14, _col(ui.FAINT), inner_w * 0.36)
    ty = top + (2 * tr + 26 if r.has("motion") else 4)
    if r.has("touch"):
        tw = min(0.26 * inner_w, 2.0 * (body_h * 0.28))
        _touchpad(c, mid - tw / 2, ty, mid + tw / 2, ty + tw / 2.0)
        ty += tw / 2.0 + 6
    chips = [("VIEW", r.glyph("VIEW", "BACK")), ("GUIDE", r.glyph("GUIDE", "XBOX")),
             ("MENU", r.glyph("MENU", "START")), ("SHARE", r.glyph("SHARE", "SHR"))]
    ch = imgui.get_text_line_height() + 4
    widths = [imgui.calc_text_size(g).x + 10 for _, g in chips]
    room = 0.36 * inner_w
    if sum(widths) + 4 * len(chips) > room:              # too narrow for the words: the first letters
        chips = [(n, g[:3]) for n, g in chips]
        widths = [imgui.calc_text_size(g).x + 10 for _, g in chips]
    x = mid - (sum(widths) + 4 * (len(chips) - 1)) / 2
    for (name, g), cw in zip(chips, widths, strict=True):
        _button(c, f"pad:{name}", g, x, ty, x + cw, ty + ch, 3.0)
        x += cw + 4
    # the edges: the back buttons, loud; Fn under them; the rumble meters
    if r.has("back"):
        bh = min(0.3 * body_h, 80.0)
        by = dial_y - bh / 2
        for name, x0 in (("LP", c.x + 2), ("RP", c.x + c.w - edge_w + 2)):
            _button(c, f"pad:{name}", r.glyph(name, name), x0, by, x0 + edge_w - 4, by + bh, 6.0)
        if r.has("fn"):
            for name, x0 in (("LFN", c.x + 2), ("RFN", c.x + c.w - edge_w + 2)):
                _button(c, f"pad:{name}", "Fn", x0, by + bh + 6, x0 + edge_w - 4, by + bh + 6 + ch, 3.0)
        if r.has("rumble") and e is not None:
            for v, x0 in ((getattr(e, "rumble_low", 0.0), c.x + 2),
                          (getattr(e, "rumble_high", 0.0), c.x + c.w - edge_w + 2)):
                ry = by + bh + 2 * ch + 14
                dl.add_rect_filled(_v(x0, ry), _v(x0 + edge_w - 4, ry + 4), _col(_DARK), 2.0)
                dl.add_rect_filled(_v(x0, ry), _v(x0 + (edge_w - 4) * min(1.0, float(v)), ry + 4),
                                   _col(_TRIG), 2.0)
    # the foot: the D-pad left, the face right, the bumpers by them
    fy = top + body_h - ch - 2
    s = ch
    for k, (name, g) in enumerate((("LEFT", "←"), ("UP", "↑"), ("DOWN", "↓"), ("RIGHT", "→"))):
        x0 = inner_x + 0.04 * inner_w + k * (s + 3)
        _button(c, f"hat:{name}", g, x0, fy, x0 + s, fy + s, 3.0)
    ink = _SONY_INK if r.sony else _XBOX_INK
    for k, name in enumerate(("X", "Y", "A", "B")):
        x0 = inner_x + 0.96 * inner_w - (4 - k) * (s + 3)
        _button(c, f"pad:{name}", r.glyph(name, name), x0, fy, x0 + s, fy + s,
                ink=ink[name], round_shape=True)
    for name, x0 in (("LB", inner_x + 0.04 * inner_w + 4 * (s + 3) + 6),
                     ("RB", inner_x + 0.96 * inner_w - 4 * (s + 3) - 6 - 1.6 * s)):
        _button(c, f"pad:{name}", r.glyph(name, name), x0, fy, x0 + 1.6 * s, fy + s, 3.0)
    _ticker(c, st, c.y + c.h - foot_h + 4, foot_h - 6)


def _ticker(c: Ctx, st: dict, y: float, h: float) -> None:
    """The last presses, newest last, fading over `TICKER_S`."""
    now = time.monotonic()
    seen = st.get("down", frozenset())
    hats = {n for n, b in gamepad.HATS.items() if c.r.hat & b}
    held = frozenset(c.r.down | {f"hat:{n}" for n in hats})
    log = st.setdefault("ticker", [])
    for n in sorted(held - seen):
        name = n.partition(":")[2] if n.startswith("hat:") else n
        glyph = {"UP": "↑", "DOWN": "↓", "LEFT": "←", "RIGHT": "→"}.get(name) if n.startswith(
            "hat:") else c.r.glyph(name, name)
        log.append((glyph, now))
    st["down"] = held
    log[:] = [(g, t) for g, t in log if now - t < TICKER_S][-TICKER_N:]
    x = c.x + c.w / 2 - len(log) * 30
    for g, t in log:
        a = max(0.15, 1 - (now - t) / TICKER_S)
        w = max(48.0, imgui.calc_text_size(g).x + 16)
        c.dl.add_rect_filled(_v(x, y), _v(x + w, y + h), _col(_OFF, a), 4.0)
        _centred(c.dl, g, x + w / 2, y + h / 2, _col(ui.TEXT, a))
        x += w + 6


# ---------------------------------------------------------------- the door

def _nvg(c: Ctx, view: str) -> bool:
    """`view` drawn by NanoVG into a texture the size of the room (in the
    window's pixels), shown on the draw list; its hits mapped back. False
    where NanoVG cannot draw (no GL): the draw-list view instead."""
    surf = ui_pad_nvg.surface_of(c.panel)
    if c.w < 8 or c.h < 8 or not surf.ready():
        return False
    k = imgui.get_io().display_framebuffer_scale
    tex, pen = surf.render(view, c.r, _state(c.panel).setdefault("nvg", {}),
                           round(c.w * k.x), round(c.h * k.y))
    c.dl.add_image(imgui.ImTextureRef(tex), _v(c.x, c.y), _v(c.x + c.w, c.y + c.h))
    s = min(c.w / ui_pad_nvg.DESIGN_W, c.h / ui_pad_nvg.DESIGN_H)
    ox = c.x + (c.w - ui_pad_nvg.DESIGN_W * s) / 2
    oy = c.y + (c.h - ui_pad_nvg.DESIGN_H * s) / 2
    for hx, hy, hw, hh, source in pen.hits:
        c.hit(ox + hx * s, oy + hy * s, ox + (hx + hw) * s, oy + (hy + hh) * s, source)
    return True


DRAW = {"faithful": faithful, "lanes": lanes, "cockpit": cockpit}


def draw(view: str, panel, dl, x: float, y: float, w: float, h: float, pad, says) -> Ctx:
    """Draw `view` in the room (x, y, w, h) on `dl`; the hover after. The
    `Ctx` back, for the tests and the tools (its hits).

    Faithful and Cockpit are drawn with NanoVG (ui_pad_nvg — the lab's
    canvas drawing, ported) where the control window's GL will take it;
    elsewhere (a headless panel) with the draw-list versions here."""
    c = Ctx(panel, dl, x, y, w, h, read(pad), says)
    if view in ui_pad_nvg.VIEWS and _nvg(c, view):
        _hover(c)
        return c
    imgui.push_font(ui._FONTS["ui"], 12.0)
    try:
        DRAW[view](c)
    finally:
        imgui.pop_font()
    _hover(c)
    return c
