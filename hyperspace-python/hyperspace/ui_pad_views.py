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
Faithful and Cockpit are the lab's own drawings (`ui_pad_lab`, its canvas
code ported line for line), drawn by NanoVG (`ui_pad_nvg`) — where it
cannot run the room says why; Lanes is drawn here. Read-only, like the map: a hover
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
from dataclasses import dataclass, field

from imgui_bundle import imgui

from . import gamepad, ui, ui_pad_lab, ui_pad_nvg
from .pads import gesture, models
from .routing_sources import pair_poles

VIEWS = ("map", "faithful", "lanes", "cockpit")
VIEW_LABELS = ("Map", "Faithful", "Lanes", "Cockpit")
VIEW_TIP = ("How the pad window reads the pad. Map: every control at its place, "
            "named with what it does. Faithful: the controller from above, lit where "
            "pressed. Lanes: every lane a row can name, its value and its mapping. "
            "Cockpit: big dials, trigger arcs, the tilt, the last presses — for a "
            "glance mid-set. Click the view's name on the pad window to step through them.")

# colours: the panel's, and a few of the lab's
_DARK = imgui.ImVec4(0.09, 0.09, 0.10, 1.0)
_STICK = imgui.ImVec4(0.42, 0.70, 1.0, 1.0)
_TRIG = imgui.ImVec4(1.0, 0.76, 0.35, 1.0)

LANE_PX = (12.0, 11.0, 10.0)   # the lanes' type sizes, the largest that fits
LANE_COL_MIN = 170.0           # a lanes column never narrower: an address, a bar, a value


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
    axes: dict = field(default_factory=dict)   # every axis lane (LX … RT, L.N …), 0–1
    touch: dict | None = None              # touch:… lanes, NaN where no finger
    motion: dict | None = None             # motion:… lanes
    degrees: tuple | None = None           # roll, pitch, yaw in degrees
    effects: object | None = None          # what the pad is being sent (sony.Effects)
    battery: int = -1
    link: str = ""
    # plan 46, a Joy-Con's calibration at a glance: the sensors as the lanes
    # see them (gyro deg/s, accel g, in the pad's axes), the stick's raw
    # 12-bit reading, the centre in use and where it came from
    sensors: tuple | None = None           # ((gx, gy, gz), (ax, ay, az))
    raw_sensors: tuple | None = None       # the chip's own counts, ((gx, gy, gz), (ax, ay, az))
    stick_raw: tuple | None = None         # (x, y) raw
    stick_centre: tuple | None = None      # (cx, cy) raw
    stick_cal: object | None = None        # the nintendo.StickCal in use (its reach each way)
    centre_from: str = ""                  # "rest", "user", "flash", "nominal"

    @property
    def sony(self) -> bool:
        return getattr(self.model, "family", "") == "sony"

    @property
    def nintendo(self) -> bool:
        return getattr(self.model, "family", "") == "nintendo"

    @property
    def kind(self) -> str:
        """A Joy-Con's side: "l", "r", or "pro" (anything else "")."""
        if not self.nintendo:
            return ""
        from .pads import nintendo
        return nintendo.kind_of(getattr(self.model, "id", ""))

    def has(self, cap: str) -> bool:
        return models.is_model(self.model) and self.model.has(cap)

    def has_control(self, name: str) -> bool:
        """Does the pad have the canonical control at all (a single Joy-Con
        has no right stick, no D-pad)? Everything, with no model."""
        return not models.is_model(self.model) or self.model.has_control(name)

    def glyph(self, name: str, default: str) -> str:
        return models.glyph(self.model if models.is_model(self.model) else None, name, default)


def _lanes_of(pad, attr: str, names) -> dict | None:
    read = getattr(pad, attr, None)
    got = read() if callable(read) else None
    return dict(zip(names, got, strict=True)) if got is not None else None


def read(pad) -> Reading:
    """The pad as the views read it — whatever it lacks left empty."""
    if pad is None:
        return Reading(axes=dict(zip(gamepad.LANES, gamepad.LANE_RESTS, strict=True)))
    on = bool(getattr(pad, "on", False))
    model = gamepad.shown_model(pad)
    named = getattr(pad, "buttons_named", None)
    named = named if isinstance(named, dict) else gamepad.BUTTONS
    down = frozenset(n for n, i in named.items() if on and pad.down(i))
    got = list(pad.lanes())[:len(gamepad.LANES)] if on else []
    lanes = got + list(gamepad.LANE_RESTS[len(got):])      # every lane, its rest where unread
    touch = _lanes_of(pad, "touch_lanes", gesture.TOUCH_LANES) if on else None
    motion = _lanes_of(pad, "motion_lanes", gesture.MOTION_LANES) if on else None
    m = getattr(pad, "motion", None)
    degrees = None
    if motion is not None and isinstance(getattr(m, "roll", None), float):
        degrees = (m.roll, m.pitch, m.yaw)
    report = getattr(pad, "report", None)
    bat = getattr(report, "battery", -1)
    sensors, raw, centre, stick_cal, centre_from = _calibration_of(pad, report, model) if on else (
        None, None, None, None, "")
    return Reading(on=on, model=model, down=down,
                   hat=int(getattr(pad, "hat", 0) or 0) if on else 0,
                   axes=dict(zip(gamepad.LANES, lanes, strict=True)), touch=touch,
                   motion=motion, degrees=degrees, effects=getattr(pad, "effects", None),
                   battery=bat if isinstance(bat, int) else -1,
                   link=str(getattr(pad, "link", "") or ""),
                   sensors=sensors, stick_raw=raw, stick_centre=centre, stick_cal=stick_cal,
                   centre_from=centre_from,
                   raw_sensors=((tuple(report.gyro), tuple(report.accel))
                                if on and getattr(report, "full", False) else None))


def _calibration_of(pad, report, model):
    """What the pad's reader knows past the lanes (plan 46): the sensors in
    the pad's axes through its calibration and axis map, and a Joy-Con's
    raw stick with the centre in use — (sensors, raw, centre, from)."""
    reader = getattr(pad, "hid_pad", None)
    cal = getattr(reader, "calibration", None)
    if report is None or cal is None or not hasattr(cal, "gyro_dps"):
        return None, None, None, None, ""
    sensors = None
    if getattr(report, "full", False):
        amap = gesture.axis_map_of(getattr(pad, "axis_map", None), reader)   # the one rule
        try:
            sensors = (tuple(amap.pick(cal.gyro_dps(report.gyro), amap.gyro)),
                       tuple(amap.pick(cal.accel_g(report.accel), amap.accel)))
        except (TypeError, ValueError, AttributeError):
            sensors = None
    raw = centre = stick = None
    where = ""
    sticks = getattr(report, "raw_sticks", ())
    if sticks and getattr(model, "family", "") == "nintendo":
        from .pads import nintendo
        kind = nintendo.kind_of(getattr(model, "id", ""))
        raw = tuple(sticks[1] if kind == "r" else sticks[0])
        stick = getattr(cal, "right" if kind == "r" else "left", None)
        if stick is not None:
            centre = (stick.cx, stick.cy)
            where = ("rest" if getattr(reader, "recentred", False)
                     else "nominal" if getattr(cal, "nominal", True)
                     else "user" if getattr(cal, "user_stick", False) else "flash")
    return sensors, raw, centre, stick, where


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


def _light(r: Reading):
    """The light bar's colour now, as an ImVec4, or None (nothing sent)."""
    rgb = getattr(r.effects, "light", None)
    if not rgb or not r.has("light"):
        return None
    return imgui.ImVec4(*(min(255, max(0, int(v))) / 255 for v in rgb), 1.0)


def _tip(c: Ctx, source: str) -> str:
    words, row = c.says(source)
    name = gamepad.control_name(source) or source
    if row is not None:
        return f"{name} · {words} · {row.describe()}"
    if words:
        return f"{name} · {words} — the app's own, no row in the table"
    return f"{name} · free — right-click a param → Learn pad, then use it here"


def tip_at(c: Ctx, x: float, y: float) -> str | None:
    """What the controls under (x, y) do, a line each — a stick is its
    click and its two axes — or None where there is none."""
    seen: list[str] = []
    for x0, y0, x1, y1, source in reversed(c.hits):
        if x0 <= x < x1 and y0 <= y < y1 and source not in seen:
            seen.append(source)
    return "\n".join(_tip(c, s) for s in seen) if seen else None


def _hover(c: Ctx) -> None:
    """The hover over the controls under the pointer: their mappings."""
    if not imgui.is_window_hovered():
        return
    m = imgui.get_mouse_pos()
    tip = tip_at(c, m.x, m.y)
    if tip:
        ui.tooltip(tip)


# ---------------------------------------------------------------- lanes

def _lane_rows(r: Reading, routed=frozenset()) -> list[tuple]:
    """(group, rows): each row (source, glyph, value or None, rest, bipolar).
    A stick's direction lanes (``axis:L.N`` …) only where `routed` names
    them: sixteen idle lines would crowd the rest out."""
    out = []
    has = r.has_control               # a single Joy-Con: one stick, no D-pad (plan 46)
    out.append(("sticks", [(f"axis:{n}", r.glyph(n, n), r.axes[n], 0.5, True)
                           for n in ("LX", "LY", "RX", "RY") if has(n)]))
    out.append(("triggers", [(f"axis:{n}", r.glyph(n, n), r.axes[n], 0.0, False)
                             for n in ("LT", "RT") if has(n)]))
    dials = [(f"axis:{n}", "", r.axes.get(n, 0.0), 0.0, False)
             for n in gamepad.DIAL_LANES if f"axis:{n}" in routed]
    if dials:
        out.append(("stick directions", dials))
    hats = [(f"hat:{n}", g, 1.0 if r.hat & gamepad.HATS[n] else 0.0, 0.0, False)
            for n, g in (("N", "↑"), ("E", "→"), ("S", "↓"), ("W", "←"))
            if has(f"{models.HAT_PREFIX}{n}")]
    if hats:
        out.append(("d-pad", hats))
    model = r.model if models.is_model(r.model) else None

    def pole(name: str) -> int:
        if not models.control_free(model, name):
            return 0
        hat = name.removeprefix(models.HAT_PREFIX)
        return (int(bool(r.hat & gamepad.HATS[hat])) if hat != name and hat in gamepad.HATS
                else int(name in r.down))
    # plan 56: each one lane, one degree of freedom: the model's, and any a row names
    shown = list(models.natural_pairs(model))
    for s in sorted(routed):
        scheme, _, addr = s.partition(":")
        a, _, b = addr.partition("/")
        if scheme == gamepad.PAIR_SCHEME and pair_poles(addr) is not None and (a, b) not in shown:
            shown.append((a, b))
    pairs = [(f"{gamepad.PAIR_SCHEME}:{a}/{b}", models.pair_label(model, a, b),
              0.5 + 0.5 * (pole(a) - pole(b)), 0.5, True) for a, b in shown]
    if pairs:
        out.append(("pairs", pairs))
    names = list(gamepad.BUTTONS)
    for cap, extra in (("touch", ("TOUCH",)), ("back", ("LP", "RP")), ("fn", ("LFN", "RFN"))):
        if r.has(cap):
            names += list(extra)
    out.append(("buttons", [(f"pad:{n}", r.glyph(n, n), 1.0 if n in r.down else 0.0, 0.0, False)
                            for n in names if has(n)]))
    if r.stick_raw is not None and r.stick_centre is not None and r.stick_cal is not None:
        # a Joy-Con's stick as the chip counts it, over the reach the
        # calibration in use gives it (so the bar agrees with the LX row)
        (x, y), (cx, cy) = r.stick_raw, r.stick_centre
        nx, ny = r.stick_cal.norm(x, y)
        out.append(("stick calibration", [
            ("raw x", str(x), nx / 2 + 0.5, 0.5, True),
            ("raw y", str(y), ny / 2 + 0.5, 0.5, True),
            (f"centre ({r.centre_from})", f"{cx}, {cy}", None, 0.5, False)]))
    if r.sensors is not None:
        (gx, gy, gz), (ax, ay, az) = r.sensors
        a_fs, g_fs = ui_pad_lab.ACCEL_FS, ui_pad_lab.GYRO_FS      # the lab's full scales

        def u(v: float, fs: float) -> float:
            return min(1.0, max(0.0, v / (2 * fs) + 0.5))
        out.append(("sensors (pad axes)", [
            ("accel x", f"{ax:+.2f} g", u(ax, a_fs), 0.5, True),
            ("accel y", f"{ay:+.2f} g", u(ay, a_fs), 0.5, True),
            ("accel z", f"{az:+.2f} g", u(az, a_fs), 0.5, True),
            ("gyro x", f"{gx:+.0f}°/s", u(gx, g_fs), 0.5, True),
            ("gyro y", f"{gy:+.0f}°/s", u(gy, g_fs), 0.5, True),
            ("gyro z", f"{gz:+.0f}°/s", u(gz, g_fs), 0.5, True)]))
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
    if e is not None and (r.has("light") or r.has("rumble") or r.has("players")):
        light = tuple(getattr(e, "light", (0, 0, 0)))
        bits = int(getattr(e, "players", 0) or 0)
        lights = 4 if r.nintendo else 5

        def trig(t) -> float:
            return float(getattr(t, "strength", 0.0) or 0.0) if getattr(t, "mode", "off") != "off" else 0.0
        rows = []
        if r.has("light"):
            rows.append(("light", "#{:02x}{:02x}{:02x}".format(*light), max(light) / 255, 0.0, False))
        if r.has("players"):
            rows.append(("players", "", min(lights, bits.bit_count()) / lights, 0.0, False))
        if r.has("rumble"):
            rows += [("rumble heavy", "", float(getattr(e, "rumble_low", 0.0)), 0.0, False),
                     ("rumble light", "", float(getattr(e, "rumble_high", 0.0)), 0.0, False)]
        if r.has("triggers"):
            rows += [("L2 resists", "", trig(getattr(e, "left", None)), 0.0, False),
                     ("R2 resists", "", trig(getattr(e, "right", None)), 0.0, False)]
        if r.has("mic"):
            rows.append(("mic light", "", 1.0 if getattr(e, "mic", 0) else 0.0, 0.0, False))
        out.append(("out (sent now)", rows))
    return out


def _routed(says) -> frozenset:
    """The stick-direction lanes a row maps, and the pairs a row names."""
    return frozenset(s for s in (f"axis:{n}" for n in gamepad.DIAL_LANES)
                     if says(s)[1] is not None) | frozenset(getattr(says, "pairs", ()))


def _line_h(px: float) -> float:
    imgui.push_font(ui._FONTS["ui"], px)
    lh = imgui.get_text_line_height() + 2
    imgui.pop_font()
    return lh


def lanes_height(w: float, pad, says) -> float:
    """How tall Lanes must be, `w` wide, for every line at the largest type
    in columns no narrower than `LANE_COL_MIN` — GRAPH's side panel gives
    it that (it scrolls), where the pad window's room is fixed."""
    groups = _lane_rows(read(pad), _routed(says))
    n_lines = sum(1 + len(rows) for _, rows in groups)
    cols = max(1, int(w // LANE_COL_MIN))
    return math.ceil(n_lines / cols) * _line_h(LANE_PX[0])


def lanes(c: Ctx) -> None:
    """Every lane in columns, the groups in order: the address a row
    names, its glyph, a bar from its rest, the value, what maps it. The
    largest type that fits (`LANE_PX`) in columns no narrower than
    `LANE_COL_MIN`; what never fits is cut at the foot."""
    groups = _lane_rows(c.r, _routed(c.says))
    n_lines = sum(1 + len(rows) for _, rows in groups)
    most = max(1, int(c.w // LANE_COL_MIN))
    chosen = None
    for px in LANE_PX:
        lh = _line_h(px)
        per_col = max(1, int(c.h // lh))
        cols = min(most, math.ceil(n_lines / per_col))
        if (per_col * cols >= n_lines and c.w / cols >= 18 * px) or px == LANE_PX[-1]:
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


# ---------------------------------------------------------------- the door

def _lab(c: Ctx, view: str) -> None:
    """`view` — one of the lab's drawings (ui_pad_lab) — drawn by NanoVG
    (ui_pad_nvg) into a texture the size of the room in the window's
    pixels, its design space fitted and centred; its hits mapped back for
    the hover. Where NanoVG cannot draw, the room says why instead."""
    surf = ui_pad_nvg.surface_of(c.panel)
    if c.w < 8 or c.h < 8 or not surf.ready():
        _not_drawn(c, VIEW_LABELS[VIEWS.index(view)], surf.why_not())
        return
    k = imgui.get_io().display_framebuffer_scale
    room = imgui.get_id("##pad.lab")    # this window's: the pad window, or GRAPH's side panel
    st = _state(c.panel).setdefault("lab", {}).setdefault(room, {})   # each room its own trails
    tex, pen = surf.render(view, c.r, st, round(c.w * k.x), round(c.h * k.y), room,
                           imgui.get_frame_count())
    c.dl.add_image(imgui.ImTextureRef(tex), _v(c.x, c.y), _v(c.x + c.w, c.y + c.h))
    s = min(c.w / ui_pad_lab.DESIGN_W, c.h / ui_pad_lab.DESIGN_H)
    ox = c.x + (c.w - ui_pad_lab.DESIGN_W * s) / 2
    oy = c.y + (c.h - ui_pad_lab.DESIGN_H * s) / 2
    for hx, hy, hw, hh, source in pen.hits:
        c.hit(ox + hx * s, oy + hy * s, ox + (hx + hw) * s, oy + (hy + hh) * s, source)


def _not_drawn(c: Ctx, name: str, why: str) -> None:
    """The room's note where NanoVG cannot draw `name`: why, and the views
    that still work."""
    lh = imgui.get_text_line_height_with_spacing()
    y = c.y + max(0.0, c.h / 2 - 1.5 * lh)
    for words, col in ((f"{name} is drawn with NanoVG.", ui.TEXT), (why, ui.DIM),
                       ("Map and Lanes still work.", ui.DIM)):
        _text_left(c.dl, words, c.x + 12, y, _col(col), c.w - 24)
        y += lh


DRAW = {"faithful": lambda c: _lab(c, "faithful"), "lanes": lanes,
        "cockpit": lambda c: _lab(c, "cockpit")}


def draw(view: str, panel, dl, x: float, y: float, w: float, h: float, pad, says) -> Ctx:
    """Draw `view` in the room (x, y, w, h) on `dl`; the hover after. The
    `Ctx` back, for the tests and the tools (its hits)."""
    c = Ctx(panel, dl, x, y, w, h, read(pad), says)
    imgui.push_font(ui._FONTS["ui"], 12.0)
    try:
        DRAW[view](c)
    finally:
        imgui.pop_font()
    _hover(c)
    return c
