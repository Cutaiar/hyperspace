"""The lab's drawings: the pad window's Faithful and Cockpit (plan 42's readouts).

The browser lab (`prototypes/edge-lab/index.html`, `drawFaithful` /
`drawCockpit`) draws on an HTML canvas: curved paths, filled outlines,
round-capped arcs, glows. The port here follows it line for line, in its
own 1000 × 620 design space, through a `Pen` — the canvas's calls — so
the drawings do not care what draws them. The app's pen is NanoVG's
(`ui_pad_nvg.NvgPen`); the `Pen` here draws nothing and keeps only where
each control landed (the hover's hit areas, and what the tests read).
Another renderer is another pen: the calls it must make are `DRAW_CALLS`.

  `faithful` / `cockpit`   the drawings, from a `ui_pad_views.Reading`;
                           their memory (trails, ticker, pulses) in the
                           dict they are handed, kept on the panel
"""

from __future__ import annotations

import math
import random
import time

from . import gamepad
from .pads import nintendo

DESIGN_W, DESIGN_H = 1000.0, 620.0
FONT_K = 1.3                # the lab's type scale for these two views

# the lab's palette (index.html `COL`)
COL = {"body": "#1a1f2c", "bodyLine": "#3a4357", "idle": "#262d3c", "idleLine": "#465068",
       "text": "#d9dfea", "dim": "#7d879b", "faint": "#3d4556", "hot": "#ffd166",
       "back": "#ff9f43", "fn": "#c084fc", "S": "#7aa8ff", "E": "#ff5a6a", "W": "#ff7ad9",
       "N": "#40e0a0", "accent": "#6cb6ff", "ok": "#4ade80", "ground": "#0d0f14",
       "cockpit": "#0a0c11", "well": "#10141c"}
XBOX_INK = {"S": "#5fd35f", "E": "#ff5a5a", "W": "#4f8dff", "N": "#ffd23f"}
HAT_GLYPH = {"N": "▲", "S": "▼", "W": "◀", "E": "▶"}
PULSE_S = 0.26              # a one-frame trigger (tap, shake) shows this long
TRAIL = 26                  # the cockpit's stick trails, frames
TICKER_S = 2.2

def rgba(c: str | tuple, a: float = 1.0) -> tuple[float, float, float, float]:
    """``"#rrggbb"``, a `COL` name or an (r, g, b) of 0–255 as floats 0–1,
    alpha `a`."""
    if isinstance(c, str):
        c = COL.get(c, c)
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    else:
        r, g, b = (int(v) for v in c[:3])
    return r / 255, g / 255, b / 255, a


# what a pen draws with: every call the drawings make, beside `hit`
DRAW_CALLS = ("path", "move", "line", "bez", "quad", "close", "rr", "circle", "arc", "lines",
              "fill", "stroke", "glow_stroke", "glow_rr", "text", "alpha", "save", "restore",
              "translate")


class Pen:
    """The drawings' pen, here drawing nothing: it keeps only where each
    control landed (`hits`, in the design space). A pen that draws
    overrides every one of `DRAW_CALLS`; `dashed_rr` is built from them."""

    def __init__(self):
        self.hits: list[tuple[float, float, float, float, str]] = []

    @property
    def live(self) -> bool:
        return False

    def hit(self, x, y, w, h, source: str) -> None:
        self.hits.append((x, y, w, h, source))

    def path(self) -> None: ...
    def move(self, x, y) -> None: ...
    def line(self, x, y) -> None: ...
    def bez(self, c1x, c1y, c2x, c2y, x, y) -> None: ...
    def quad(self, cx, cy, x, y) -> None: ...
    def close(self) -> None: ...
    def rr(self, x, y, w, h, r) -> None: ...
    def circle(self, cx, cy, r) -> None: ...

    def arc(self, cx, cy, r, a0, a1) -> None:
        """A clockwise arc, as canvas draws one (radians, y down)."""

    def lines(self, *pts) -> None: ...
    def fill(self, color, a: float = 1.0) -> None: ...

    def stroke(self, color, width: float = 1.0, a: float = 1.0, cap: str = "butt") -> None:
        """The current path's outline; `cap` "butt" or "round"."""

    def glow_stroke(self, color, width: float, blur: float) -> None:
        """The current path stroked with a soft glow round it (canvas's
        shadowBlur)."""

    def glow_rr(self, x, y, w, h, r, color, blur: float, a: float = 0.85) -> None:
        """A soft glow round a rounded box."""

    def text(self, s: str, x, y, *, size=13, color="text", align="center", weight=500,
             mono=False, a: float = 1.0) -> None:
        """`s` centred on y; `align` "center", "left" or "right" about x;
        `weight` ≥ 650 bold; `mono` the numbers' face."""

    def alpha(self, a: float) -> None: ...
    def save(self) -> None: ...
    def restore(self) -> None: ...
    def translate(self, x, y) -> None: ...

    def dashed_rr(self, x, y, w, h, color, width, dash=5.0, gap=4.0) -> None:
        """A rounded box's outline in dashes: its four straight runs dashed,
        its corners drawn whole."""
        if not self.live:
            return
        r = min(16.0, w / 2, h / 2)
        runs = (((x + r, y), (x + w - r, y)), ((x + w, y + r), (x + w, y + h - r)),
                ((x + w - r, y + h), (x + r, y + h)), ((x, y + h - r), (x, y + r)))
        for (ax, ay), (bx, by) in runs:
            length = math.hypot(bx - ax, by - ay)
            t = 0.0
            while t < length:
                t1 = min(length, t + dash)
                self.lines((ax + (bx - ax) * t / length, ay + (by - ay) * t / length),
                           (ax + (bx - ax) * t1 / length, ay + (by - ay) * t1 / length))
                self.stroke(color, width)
                t += dash + gap
        for cx, cy, a0 in ((x + r, y + r, math.pi), (x + w - r, y + r, -math.pi / 2),
                           (x + w - r, y + h - r, 0.0), (x + r, y + h - r, math.pi / 2)):
            self.arc(cx, cy, r, a0, a0 + math.pi / 2)
            self.stroke(color, width)


# ---------------------------------------------------------------- what the lab reads

def _pressed(r, name: str) -> bool:
    return name in r.down


def _hat(r, name: str) -> bool:
    return bool(r.hat & gamepad.HATS[name])


def _trig(t) -> tuple[str, int, int, int]:
    """A sent `sony.Trigger` as the lab reads one: (mode, start zone 0–9,
    level 1–8, Hz) — mode "off", "feedback" or "vibration"."""
    mode = getattr(t, "mode", "off") or "off"
    level = round(float(getattr(t, "strength", 0.0) or 0.0) * 8)
    if mode == "off" or level <= 0:
        return "off", -1, 0, 0
    start = round(min(1.0, max(0.0, float(getattr(t, "start", 0.0) or 0.0))) * 9)
    return ("feedback" if mode == "resist" else "vibration"), start, level, int(getattr(t, "freq", 0) or 0)


def _sent(r):
    """What the pad is being shown: (light rgb or None, players bits,
    rumble low, rumble high, left trigger, right trigger, mic)."""
    e = r.effects
    if e is None or not (r.has("light") or r.has("rumble") or r.has("players")):
        return None, None, 0.0, 0.0, _trig(None), _trig(None), 0
    return (tuple(e.light) if r.has("light") else None, int(e.players),
            float(e.rumble_low), float(e.rumble_high), _trig(e.left), _trig(e.right), int(e.mic))


def _pulse(st: dict, key: str, on: bool, now: float, hold: float = PULSE_S) -> bool:
    """A one-frame trigger held up for `hold` seconds, so it can be seen."""
    if on:
        st[key] = now
    return now - st.get(key, -1e9) < hold


_SONY_WORDS = {"VIEW": "Create", "MENU": "Options", "GUIDE": "PS", "SHARE": "mic",
               "CREATE": "Create", "OPTIONS": "Options", "MIC": "mic"}
_XBOX_WORDS = {"S": "A", "E": "B", "W": "X", "N": "Y", "VIEW": "View", "MENU": "Menu", "GUIDE": "Xbox", "SHARE": "Share",
               "LSTICK": "LS", "RSTICK": "RS"}


def _glyph(r, name: str) -> str:
    """What the pad's face calls `name`, in the lab's words."""
    if r.sony:
        g = r.glyph(name, name)
        return _SONY_WORDS.get(g, g)
    return r.glyph(name, _XBOX_WORDS.get(name, name))      # a Joy-Con's own words first


# a Joy-Con's inks: the (L)'s neon blue, the (R)'s neon red (plan 46)
JOYCON_INK = {"l": "#3fc1ff", "r": "#ff5f6d", "pro": "#9aa7bf"}
JOYCON_BODY = {"l": "#162738", "r": "#331a22", "pro": "#1a1f2c"}


def _ink(r, name: str) -> str:
    """A face button's own colour: the DualSense's, a Joy-Con's side's, or
    an Xbox pad's."""
    if r.sony:
        return COL[name]
    if getattr(r, "nintendo", False):
        return JOYCON_INK.get(r.kind, XBOX_INK[name])
    return XBOX_INK[name]


def _battery(p: Pen, r, x, y, below=False) -> None:
    lvl = r.battery / 10 if r.battery >= 0 else 0.0
    p.rr(x, y, 40, 18, 4)
    p.stroke("idleLine", 2)
    p.rr(x + 40, y + 5, 4, 8, 1)
    p.fill("idleLine")
    if r.battery >= 0:
        p.rr(x + 3, y + 3, max(0.5, 34 * lvl), 12, 2)
        p.fill("ok" if lvl > 0.25 else "#f87171")
    pct = f"{min(r.battery * 10 + 5, 100)}%" if r.battery >= 0 else "battery —"
    if below:
        p.text(pct, x, y + 32, size=11, color="dim", align="left")
    else:
        p.text(pct, x - 8, y + 9, size=12, color="dim", align="right")


def _clip(a, b, cx, cy, rad):
    """The part of the segment a–b inside the circle (cx, cy, rad), or None
    — the lab clips its horizon to the ring; a pen cannot clip to a
    circle, so the lines are cut to it."""
    (x0, y0), (x1, y1) = a, b
    dx, dy, fx, fy = x1 - x0, y1 - y0, x0 - cx, y0 - cy
    qa, qb, qc = dx * dx + dy * dy, 2 * (fx * dx + fy * dy), fx * fx + fy * fy - rad * rad
    if qa == 0:
        return None
    disc = qb * qb - 4 * qa * qc
    if disc <= 0:
        return None
    s = math.sqrt(disc)
    t0, t1 = max(0.0, (-qb - s) / (2 * qa)), min(1.0, (-qb + s) / (2 * qa))
    if t0 >= t1:
        return None
    return (x0 + dx * t0, y0 + dy * t0), (x0 + dx * t1, y0 + dy * t1)


def _attitude(p: Pen, r, st: dict, cx, cy, rad, big: bool, now: float) -> None:
    """The lab's `drawAttitude`: a horizon that rolls and lifts with the
    pad, the ring brightening with motion energy, yaw as a dot outside it."""
    m = r.motion
    live = m is not None and r.degrees is not None
    p.circle(cx, cy, rad)
    p.fill("well")
    p.lines((cx - rad, cy), (cx + rad, cy))
    p.stroke("#2a3242", 1)
    if live:
        roll, pitch, yaw = r.degrees
        dy = -max(-1.0, min(1.0, pitch / 60)) * rad * 0.7
        ca, sa = math.cos(math.radians(roll)), math.sin(math.radians(roll))

        def rot(x, y):
            return cx + x * ca - y * sa, cy + dy + x * sa + y * ca
        for (a, b), w in (((rot(-rad * 0.62, 0), rot(rad * 0.62, 0)), 5 if big else 3),
                          ((rot(-rad * 0.62, 0), rot(-rad * 0.5, rad * 0.3)), 4 if big else 2),
                          ((rot(rad * 0.62, 0), rot(rad * 0.5, rad * 0.3)), 4 if big else 2)):
            seg = _clip(a, b, cx, cy, rad - w / 2)
            if seg:
                p.lines(*seg)
                p.stroke("accent", w, cap="round")
    e = float(m.get("energy", 0.0)) if live else 0.0
    shake = _pulse(st, "shake_ring", bool(live and m.get("shake")), now, 0.3)
    p.circle(cx, cy, rad)
    if shake:
        p.stroke("hot", 5)
    else:
        p.stroke("accent", 2 + 4 * e, a=0.25 + 0.75 * e)
    if live:
        a = -math.pi / 2 + max(-1.0, min(1.0, yaw / 90)) * math.pi / 2
        o = rad + (9 if big else 5)
        p.circle(cx + math.cos(a) * o, cy + math.sin(a) * o, 5 if big else 3)
        p.fill("hot")
    if big:
        p.text(f"roll {roll:+.0f}°  pitch {pitch:+.0f}°" if live else "no motion data",
               cx, cy + rad + 20, size=10.5, color="dim", mono=True)
        if live:
            p.text(f"yaw {yaw:+.0f}°", cx, cy + rad + 36, size=10.5, color="dim", mono=True)
    p.hit(cx - rad, cy - rad, 2 * rad, 2 * rad, "motion:roll")


def _fingers(p: Pen, t, x0, y0, w, h, rad, numbered: bool) -> list:
    """The fingers on a touchpad drawn in (x0, y0, w, h): a line between
    two, a dot for each; the dots' places back."""
    pts = []
    for k, (xs, ys) in enumerate((("x", "y"), ("x2", "y2"))):
        x, y = t.get(xs), t.get(ys)
        if x is not None and y is not None and math.isfinite(x) and math.isfinite(y):
            pts.append((k, x0 + w * x, y0 + h * (1 - y)))
    if len(pts) == 2:
        p.lines(pts[0][1:], pts[1][1:])
        p.stroke("accent", 2, a=0.6)
    for k, px, py in pts:
        p.circle(px, py, rad)
        p.fill("W" if k else "accent", (0.85 if k else 0.9) if numbered else 1.0)
        if numbered:
            p.text(str(k + 1), px, py, size=10, color="#000", weight=700)
    return pts


# ---------------------------------------------------------------- (a) faithful

def _edge_body(p: Pen) -> None:
    """The lab's `edgeBody`: the controller's outline, one path."""
    p.path()
    p.move(500, 100)
    p.line(340, 100)
    p.bez(250, 98, 175, 108, 148, 170)
    p.bez(128, 220, 112, 330, 112, 420)
    p.bez(112, 520, 150, 600, 218, 600)
    p.bez(272, 600, 300, 560, 318, 520)
    p.bez(338, 476, 372, 446, 420, 446)
    p.line(580, 446)
    p.bez(628, 446, 662, 476, 682, 520)
    p.bez(700, 560, 728, 600, 782, 600)
    p.bez(850, 600, 888, 520, 888, 420)
    p.bez(888, 330, 872, 220, 852, 170)
    p.bez(825, 108, 750, 98, 660, 100)
    p.close()


def _stick(p: Pen, r, n: str, cx, cy, xa, ya) -> None:
    on = _pressed(r, n)
    p.circle(cx, cy, 50)
    p.fill("well")
    p.circle(cx, cy, 50)
    p.stroke("hot" if on else "idleLine", 4 if on else 1.5)
    p.lines((cx - 50, cy), (cx + 50, cy))
    p.stroke("#232a38", 1)
    p.lines((cx, cy - 50), (cx, cy + 50))
    p.stroke("#232a38", 1)
    x = cx + (r.axes[xa] - 0.5) * 2 * 36
    y = cy - (r.axes[ya] - 0.5) * 2 * 36
    p.circle(x, y, 22)
    p.fill("hot" if on else "#3a4560")
    p.circle(x, y, 22)
    p.stroke("accent", 2)
    p.text(_glyph(r, n), x, y, size=11, color="#000" if on else "dim", weight=700)
    for src in (f"pad:{n}", f"axis:{xa}", f"axis:{ya}"):      # the hover names all three
        p.hit(cx - 50, cy - 50, 100, 100, src)


def _dpad(p: Pen, r, cx, cy) -> None:
    for d, (dx, dy) in (("N", (0, -40)), ("S", (0, 40)), ("W", (-40, 0)),
                        ("E", (40, 0))):
        x, y, on = cx + dx, cy + dy, _hat(r, d)
        p.rr(x - 19, y - 19, 38, 38, 7)
        p.fill("hot" if on else "idle")
        p.rr(x - 19, y - 19, 38, 38, 7)
        p.stroke("idleLine", 1)
        p.text(HAT_GLYPH[d], x, y, size=13, color="#000" if on else "dim")
        p.hit(x - 19, y - 19, 38, 38, f"hat:{d}")


def _pill(p: Pen, r, n: str, x, y, w, h, word_y=None) -> None:
    """A small button (Create, Options, View, Menu), its name under it."""
    on = _pressed(r, n)
    p.rr(x, y, w, h, min(w, h) / 2)
    p.fill("hot" if on else "idle")
    if word_y is not None:
        p.text(_glyph(r, n), x + w / 2, word_y, size=10, color="dim")
    p.hit(x - 6, y - 4, w + 12, h + 8, f"pad:{n}")


def faithful(p: Pen, r, st: dict) -> None:
    """The lab's `drawFaithful`: the pad from above, every control lit
    where it sits. A DualSense as the lab draws it; an Xbox pad (or no
    pad) in the same hand, its sticks offset and no touchpad."""
    now = time.monotonic()
    light, players, r_low, r_high, left, right, mic = _sent(r)
    if getattr(r, "nintendo", False) and r.kind in ("l", "r"):
        _faithful_joycon(p, r, st, now, players, r_low, r_high)   # one Joy-Con, upright (plan 46)
        return
    sony = r.sony
    edge = r.has("back")
    p.rr(0, 0, DESIGN_W, DESIGN_H, 0)
    p.fill("ground")
    p.save()
    shake = r_low * 3 + r_high * 1.4           # the lab's rumble jitter
    if shake > 0.01:
        p.translate((random.random() - 0.5) * shake, (random.random() - 0.5) * shake)
    # the triggers: travel, and the resistance zone the pad is sent
    for side, x, tr in (("LT", 195, left), ("RT", 675, right)):
        u = r.axes[side]
        p.rr(x, 26, 130, 42, 10)
        p.fill("idle")
        mode, start, level, hz = tr
        if mode != "off" and start >= 0:
            p.rr(x + 130 * start / 9, 26, 130 * (1 - start / 9), 42, 0)
            p.fill("back" if mode == "feedback" else "fn",
                   (0.15 if mode == "feedback" else 0.2) + 0.5 * level / 8)
        p.rr(x, 26, max(0.001, 130 * u), 42, 10)
        p.fill("hot" if u > 0.98 else "accent", 0.85)
        p.rr(x, 26, 130, 42, 10)
        p.stroke("idleLine", 1.5)
        p.text(f"{_glyph(r, side)} {round(u * 100)}%", x + 65, 47, size=14, weight=700,
               color="#10131a" if u > 0.55 else "text")
        if mode != "off":
            p.text(f"resist {level}/8 from zone {start}" if mode == "feedback"
                   else f"vibrate {level}/8 {hz} Hz", x + 65, 15, size=11, color="back")
        p.hit(x, 26, 130, 42, f"axis:{side}")
    for n, x in (("LB", 185), ("RB", 665)):
        on = _pressed(r, n)
        p.rr(x, 76, 150, 18, 8)
        p.fill("hot" if on else "idle")
        p.text(_glyph(r, n), x + 75, 85, size=11, color="#000" if on else "dim", weight=700)
        p.hit(x, 76, 150, 18, f"pad:{n}")
    # the body
    _edge_body(p)
    p.fill("body")
    _edge_body(p)
    p.stroke("bodyLine", 2.5)
    # the back buttons, on the grips' underside (an Edge; dim on a DualSense)
    if sony:
        for n, x, word in (("LP", 178, "back L"), ("RP", 762, "back R")):
            on = _pressed(r, n)
            p.rr(x, 520, 60, 52, 16)
            p.fill("back", 0.85 if on else 0.05)
            if on:
                p.rr(x, 520, 60, 52, 16)
                p.stroke("back", 2)
            else:
                p.dashed_rr(x, 520, 60, 52, "#5b6378" if edge else "#2a303d", 2)
            p.text(word, x + 30, 540, size=11, color="#000" if on else "dim", weight=700)
            p.text(f"pad:{n}", x + 30, 556, size=10, color="#000" if on else "faint", mono=True)
            if edge:
                p.hit(x, 520, 60, 52, f"pad:{n}")
        if edge:
            p.text("(underside)", 500, 590, size=10, color="faint")
    if sony:
        _faithful_sony(p, r, st, now, light, players, mic)
    else:
        _faithful_xbox(p, r)
    # the face buttons, each in its own ink
    for n, (x, y) in (("N", (765, 198)), ("E", (817, 250)), ("S", (765, 302)), ("W", (713, 250))):
        on, ink = _pressed(r, n), _ink(r, n)
        p.circle(x, y, 23)
        p.fill(ink if on else "idle")
        p.circle(x, y, 23)
        p.stroke(ink, 2)
        p.text(_glyph(r, n), x, y + 1, size=20, color="#000" if on else ink, weight=700)
        p.hit(x - 23, y - 23, 46, 46, f"pad:{n}")
    # rumble, as rings by the grips
    if r_low > 0.01:
        for i in range(3):
            p.arc(150, 470, 30 + i * 12, 2.2, 4.0)
            p.stroke("back", 3, a=0.3 + 0.7 * r_low)
        p.text(f"low {r_low:.2f}", 90, 470, size=11, color="back")
    if r_high > 0.01:
        for i in range(3):
            p.arc(850, 470, 24 + i * 9, -0.9, 0.9)
            p.stroke("fn", 2, a=0.3 + 0.7 * r_high)
        p.text(f"high {r_high:.2f}", 912, 470, size=11, color="fn")
    p.restore()
    # the tilt between the triggers, the battery, the corner words
    if r.has("motion"):
        _attitude(p, r, st, 500, 46, 28, False, now)
    if r.battery >= 0 or sony:
        _battery(p, r, 14, 10, below=True)
    name = getattr(r.model, "name", "") if r.on else "no pad"
    p.text(f"{name or 'pad'} · {r.link or '—'}", 12, 610, size=12, color="dim", align="left")
    if r.has("light"):
        p.text("light #{:02x}{:02x}{:02x}".format(*light) if light is not None
               else "light not set yet",
               988, 610, size=12, color="dim", align="right", mono=True)
    if r.motion is not None and _pulse(st, "shake_word", bool(r.motion.get("shake")), now):
        p.text("SHAKE", 500, 500, size=22, color="hot", weight=800)


def _faithful_sony(p: Pen, r, st, now, light, players, mic) -> None:
    """The DualSense's middle: touchpad, light bar, player lights, the
    D-pad, the sticks side by side, PS, the mic, Fn on an Edge."""
    t = r.touch
    p.rr(335, 112, 330, 170, 22)
    p.fill("#2c3a55" if _pressed(r, "TOUCH") else "#151a25")
    p.rr(335, 112, 330, 170, 22)
    p.stroke("idleLine", 1.5)
    p.hit(335, 112, 330, 170, "pad:TOUCH")
    p.text("touchpad", 500, 198, size=11, color="#2b3344")
    if t is not None:
        _fingers(p, t, 335, 112, 330, 170, 13, True)
        pin, tw = t.get("pinch"), t.get("twist")
        if pin is not None and math.isfinite(pin):
            p.text(f"pinch {pin:.2f}  twist {tw:.2f}", 500, 270, size=11, color="dim", mono=True)
        if _pulse(st, "tap", bool(t.get("tap")), now):
            p.text("TAP", 500, 130, size=13, color="hot", weight=800)
    elif r.on:
        p.text("no touch in the simple report", 500, 220, size=11, color="faint")
    # the light bar, both sides of the touchpad
    for (x0, y0), (qx, qy), (x1, y1) in (((327, 128), (320, 200), (330, 272)),
                                        ((673, 128), (680, 200), (670, 272))):
        p.path()
        p.move(x0, y0)
        p.quad(qx, qy, x1, y1)
        if light is not None:
            p.glow_stroke(light, 6, 16)
        else:
            p.stroke((90, 98, 115), 6, cap="round")
    for i in range(5):
        on = players is not None and (players >> i) & 1
        p.circle(468 + i * 16, 296, 4)
        p.fill("#ffffff" if on else "#2b3242")
    _pill(p, r, "VIEW", 292, 116, 16, 32, word_y=160)
    _pill(p, r, "MENU", 692, 116, 16, 32, word_y=160)
    _dpad(p, r, 235, 250)
    _stick(p, r, "LSTICK", 380, 372, "LX", "LY")
    _stick(p, r, "RSTICK", 620, 372, "RX", "RY")
    on = _pressed(r, "GUIDE")
    p.circle(500, 368, 16)
    p.fill("hot" if on else "idle")
    p.text("PS", 500, 368, size=10, color="#000" if on else "dim", weight=700)
    p.hit(484, 352, 32, 32, "pad:GUIDE")
    on = _pressed(r, "SHARE")
    if mic and not on:
        p.glow_rr(482, 398, 36, 12, 6, "#ff8a3d", 12)
    p.rr(482, 398, 36, 12, 6)
    p.fill("hot" if on else "#ff8a3d" if mic else "idle")
    p.text("mic", 500, 420, size=10, color="dim")
    p.hit(478, 394, 44, 20, "pad:SHARE")
    edge = r.has("fn")
    for n, x in (("LFN", 366), ("RFN", 606)):
        on = _pressed(r, n)
        p.rr(x, 428, 28, 13, 6)
        p.fill("fn" if on else "idle" if edge else "#1c212c")
        p.text("Fn", x + 14, 435, size=9, color="#000" if on else "dim", weight=700)
        if edge:
            p.hit(x - 4, 424, 36, 21, f"pad:{n}")


def _faithful_xbox(p: Pen, r) -> None:
    """An Xbox pad's middle, in the lab's hand: the left stick high and
    the D-pad low, the guide button between View and Menu."""
    _stick(p, r, "LSTICK", 235, 250, "LX", "LY")
    _dpad(p, r, 380, 372)
    _stick(p, r, "RSTICK", 620, 372, "RX", "RY")
    on = _pressed(r, "GUIDE")
    p.circle(500, 170, 26)
    p.fill("hot" if on else "idle")
    p.circle(500, 170, 26)
    p.stroke("idleLine", 1.5)
    p.text(_glyph(r, "GUIDE"), 500, 170, size=10, color="#000" if on else "dim", weight=700)
    p.hit(474, 144, 52, 52, "pad:GUIDE")
    _pill(p, r, "VIEW", 418, 238, 30, 18, word_y=270)
    _pill(p, r, "MENU", 552, 238, 30, 18, word_y=270)
    _pill(p, r, "SHARE", 485, 300, 30, 14, word_y=328)


# ---------------------------------------------------------------- (c) cockpit

def _dial(p: Pen, r, st: dict, cx, cy, side: str, tr, stick: str | None = None,
          ax: str | None = None, ay: str | None = None) -> None:
    """The lab's `dial`: the trigger as a thick arc round the stick's
    well, the resistance sent as the outer band, the bumper as a cap, the
    stick with its trail. `stick`, `ax`, `ay` name the stick drawn when it
    is not the side's own (a Joy-Con (R)'s one stick is the left stick)."""
    big = 125
    trig = "LT" if side == "L" else "RT"
    stick = stick or f"{side}STICK"
    ax, ay = ax or f"{side}X", ay or f"{side}Y"
    u = r.axes[trig]
    a0, sweep = math.pi * 0.75, math.pi * 1.5
    col = COL["accent"] if side == "L" else "#ff9f6c"
    p.arc(cx, cy, big, a0, a0 + sweep)
    p.stroke("#1b212d", 16, cap="round")
    mode, start, level, _hz = tr
    if mode != "off" and start >= 0:
        p.arc(cx, cy, big + 15, a0 + sweep * start / 9, a0 + sweep)
        p.stroke(COL["back"] if mode == "feedback" else COL["fn"], 5,
                 a=0.25 + 0.6 * level / 8, cap="round")
    if u > 0.003:
        p.arc(cx, cy, big, a0, a0 + sweep * u)
        p.stroke(COL["hot"] if u > 0.98 else col, 16, cap="round")
    p.hit(cx - big - 16, cy - big - 16, 2 * big + 32, 40, f"axis:{trig}")
    bump = "LB" if side == "L" else "RB"
    on = _pressed(r, bump)
    p.arc(cx, cy, big + 30, -math.pi / 2 - 0.42, -math.pi / 2 + 0.42)
    p.stroke(COL["hot"] if on else "#232a38", 10, cap="round")
    p.text(_glyph(r, bump), cx, cy - big - 30, size=10, color="#000" if on else COL["dim"], weight=800)
    p.hit(cx - 60, cy - big - 40, 120, 20, f"pad:{bump}")
    on = _pressed(r, stick)
    rad = big - 30
    p.circle(cx, cy, rad)
    p.fill("#3a3216" if on else "#11151d")
    for a, b in (((cx - rad, cy), (cx + rad, cy)), ((cx, cy - rad), (cx, cy + rad))):
        p.lines(a, b)
        p.stroke("#212836", 1)
    p.circle(cx, cy, rad / 2)
    p.stroke("#212836", 1)
    x = cx + (r.axes[ax] - 0.5) * 2 * (rad - 12)
    y = cy - (r.axes[ay] - 0.5) * 2 * (rad - 12)
    trail = st.setdefault("trails", {}).setdefault(side, [])
    trail.append((x, y))
    del trail[:-TRAIL]
    for i in range(1, len(trail)):
        p.lines(trail[i - 1], trail[i])
        p.stroke(col, 1 + 3 * i / len(trail), a=i / len(trail) * 0.6)
    p.circle(x, y, 13)
    p.fill(COL["hot"] if on else col)
    for src in (f"pad:{stick}", f"axis:{ax}", f"axis:{ay}"):   # the hover names all three
        p.hit(cx - rad, cy - rad, 2 * rad, 2 * rad, src)
    p.text(f"{_glyph(r, trig)} {round(u * 100)}%", cx, cy + big + 4, size=14,
           weight=700, color=col if u > 0.003 else COL["faint"])
    if mode != "off":
        p.text(f"pushes back {level}/8" if mode == "feedback" else f"buzz {level}/8",
               cx, cy + big + 22, size=11, color=COL["back"])


def _cluster(p: Pen, r, cx, cy, items, hot) -> None:
    for src, g, dx, dy, c in items:
        scheme, _, name = src.partition(":")
        on = _hat(r, name) if scheme == "hat" else _pressed(r, name)
        x, y = cx + dx * 34, cy + dy * 30
        p.circle(x, y, 16)
        p.fill((c or hot) if on else "#161b26")
        p.circle(x, y, 16)
        p.stroke(c or "#3a4357", 1.5)
        p.text(g, x, y + 1, size=14, color="#000" if on else (c or COL["dim"]), weight=700)
        p.hit(x - 16, y - 16, 32, 32, src)


def cockpit(p: Pen, r, st: dict) -> None:
    """The lab's `drawCockpit`: for a glance mid-set."""
    now = time.monotonic()
    light, players, r_low, r_high, left, right, mic = _sent(r)
    if getattr(r, "nintendo", False) and r.kind in ("l", "r"):
        _cockpit_joycon(p, r, st, now, players, r_low, r_high)    # one dial, the tilt big (plan 46)
        return
    edge = r.has("back")
    p.rr(0, 0, DESIGN_W, DESIGN_H, 0)
    p.fill("cockpit")
    # the light bar's colour, full width
    if light is not None:
        p.glow_rr(20, 12, 960, 10, 5, light, 18)
        p.rr(20, 12, 960, 10, 5)
        p.fill(light)
    elif r.has("light"):
        p.rr(20, 12, 960, 10, 5)
        p.fill((90, 98, 115), 0.4)
    if not r.on:
        word = "NO PAD"
    else:
        word = {"edge": "EDGE", "dualsense": "DUALSENSE"}.get(getattr(r.model, "id", ""))
        word = word or (getattr(r.model, "name", "") or "pad").upper()
    p.text(f"{word} · {(r.link or '—').upper()}", 22, 40, size=12, align="left",
           color="dim", weight=700)
    if r.has("players"):
        for i in range(5):
            on = players is not None and (players >> i) & 1
            p.circle(468 + i * 16, 40, 4.5)
            p.fill("#ffffff" if on else "#262d3c")
    if r.battery >= 0 or r.sony:
        _battery(p, r, 935, 31)
    _dial(p, r, st, 245, 270, "L", left)
    _dial(p, r, st, 755, 270, "R", right)
    if r.has("motion"):
        _attitude(p, r, st, 500, 220, 78, True, now)
    # the touchpad, small
    if r.has("touch"):
        tx, ty, tw, th = 420, 350, 160, 80
        p.rr(tx, ty, tw, th, 10)
        p.fill("#24324c" if _pressed(r, "TOUCH") else "#121722")
        p.rr(tx, ty, tw, th, 10)
        p.stroke("#2b3446", 1.5)
        p.hit(tx, ty, tw, th, "pad:TOUCH")
        t = r.touch
        if t is not None:
            _fingers(p, t, tx, ty, tw, th, 8, False)
            pin, tw2 = t.get("pinch"), t.get("twist")
            tap = _pulse(st, "tap", bool(t.get("tap")), now, 0.4)
            if pin is not None and math.isfinite(pin):
                s = f"pinch ×{2 ** ((pin - 0.5) * 4):.2f}  twist {(tw2 - 0.5) * 360:+.0f}°"
            elif tap:
                s = "TAP"
            elif t.get("x") is not None and math.isfinite(t["x"]):
                s = f"x {t['x']:.2f}  y {t['y']:.2f}"
            else:
                s = "touchpad"
            p.text(s, tx + tw / 2, ty + th + 14, size=12, color="hot" if tap else "dim",
                   mono=True)
    # the middle row
    for i, n in enumerate(("VIEW", "GUIDE", "MENU", "SHARE")):
        x, on = 405 + i * 64, _pressed(r, n)
        p.rr(x - 28, 456, 56, 22, 11)
        p.fill("hot" if on else "#5a2e14" if n == "SHARE" and mic else "#161b26")
        p.text(_glyph(r, n), x, 467, size=11, color="#000" if on else "dim", weight=600)
        p.hit(x - 28, 456, 56, 22, f"pad:{n}")
    # the D-pad and the face
    _cluster(p, r, 245, 500, [("hat:N", "▲", 0, -1, None), ("hat:E", "▶", 1, 0, None),
                              ("hat:S", "▼", 0, 1, None), ("hat:W", "◀", -1, 0, None)],
             COL["hot"])
    _cluster(p, r, 755, 500, [(f"pad:{n}", _glyph(r, n), dx, dy, _ink(r, n))
                              for n, dx, dy in (("N", 0, -1), ("E", 1, 0), ("S", 0, 1),
                                                ("W", -1, 0))], COL["hot"])
    # the back and Fn tabs, loud (an Edge; dim on a DualSense); the rumble meters
    if r.sony:
        for n, x, lbl in (("LP", 22, "BACK L"), ("RP", 918, "BACK R")):
            on = _pressed(r, n)
            p.rr(x, 170, 60, 110, 14)
            p.fill("back" if on else "#171c27" if edge else "#101319")
            p.rr(x, 170, 60, 110, 14)
            p.stroke("#ffd1a0" if on else "#2b3446", 2)
            p.text(lbl, x + 30, 215, size=10, color="#000" if on else "dim" if edge else "faint",
                   weight=800)
            p.text(_glyph(r, n), x + 30, 236, size=11, color="#000" if on else "faint", mono=True)
            if edge:
                p.hit(x, 170, 60, 110, f"pad:{n}")
        for n, x in (("LFN", 22), ("RFN", 918)):
            on = _pressed(r, n)
            p.rr(x, 292, 60, 40, 12)
            p.fill("fn" if on else "#171c27" if edge else "#101319")
            p.text("Fn", x + 30, 312, size=13, color="#000" if on else "dim" if edge else "faint",
                   weight=800)
            if edge:
                p.hit(x, 292, 60, 40, f"pad:{n}")
    if r.has("rumble"):
        for x, v, lbl, c in ((22, r_low, "heavy", "back"), (918, r_high, "light", "fn")):
            p.rr(x, 346, 60, 10, 5)
            p.fill("#161b26")
            if v > 0.005:
                p.rr(x, 346, max(0.5, 60 * v), 10, 5)
                p.fill(c)
            p.text(f"rumble {lbl}", x + 30, 368, size=8, color="faint")
    _ticker(p, r, st, now)


def _ticker(p: Pen, r, st: dict, now: float) -> None:
    """Presses, taps and shakes, newest last, fading over `TICKER_S`."""
    hats = {f"hat:{n}" for n, b in gamepad.HATS.items() if r.hat & b}
    held = frozenset({f"pad:{n}" for n in r.down} | hats)
    if r.motion is not None and r.motion.get("shake"):
        held |= {"motion:shake"}
    if r.touch is not None and r.touch.get("tap"):
        held |= {"touch:tap"}
    seen = st.get("held", frozenset())
    log = st.setdefault("events", [])
    for k in sorted(held - seen):
        log.append((k, now))
    st["held"] = held - {"motion:shake", "touch:tap"}
    log[:] = [(k, t) for k, t in log if now - t < TICKER_S][-9:]
    x = 500 - len(log) * 52
    for k, t in log:
        a = 1 - (now - t) / TICKER_S
        scheme, _, n = k.partition(":")
        label = (HAT_GLYPH[n] if scheme == "hat" else _glyph(r, n) if scheme == "pad"
                 else n.upper())
        loud = k in ("motion:shake", "pad:LP", "pad:RP")
        p.alpha(0.25 + 0.75 * a)
        p.rr(x, 572, 96, 30, 8)
        p.fill(COL["back"] if loud else "#2a3550")
        p.text(label, x + 48, 587, size=13, weight=700, color="#ffffff")
        x += 104
    p.alpha(1.0)
    if not log:
        p.text("presses, taps and shakes scroll here", 500, 587, size=12, color="#2b3446")


# ---------------------------------------------------------------- a Joy-Con (plan 46)

def _rumble_rings(p: Pen, r_low: float, r_high: float, lx, ly, rx, ry) -> None:
    """The rumble as rings: the heavy band at (lx, ly), the light at (rx, ry)."""
    if r_low > 0.01:
        for i in range(3):
            p.arc(lx, ly, 30 + i * 12, 2.2, 4.0)
            p.stroke("back", 3, a=0.3 + 0.7 * r_low)
        p.text(f"low {r_low:.2f}", lx - 60, ly, size=11, color="back")
    if r_high > 0.01:
        for i in range(3):
            p.arc(rx, ry, 24 + i * 9, -0.9, 0.9)
            p.stroke("fn", 2, a=0.3 + 0.7 * r_high)
        p.text(f"high {r_high:.2f}", rx + 62, ry, size=11, color="fn")


def _faithful_joycon(p: Pen, r, st: dict, now: float, players, r_low, r_high) -> None:
    """One Joy-Con from above, upright as a hand holds it like a remote:
    the trigger and the shoulder along its top edge, − (or +) by the rail,
    the stick and the four face buttons, capture (or HOME), SL and SR on
    the rail with the four player lights between them. Beside it what a
    calibration needs at a glance: the stick's well with the deadzone
    ring, its raw reading and the centre in use on the left; the tilt,
    big, with the sensors' numbers on the right."""
    kind = r.kind
    left = kind == "l"
    ink = JOYCON_INK[kind]
    p.rr(0, 0, DESIGN_W, DESIGN_H, 0)
    p.fill("ground")
    p.save()
    shake = r_low * 3 + r_high * 1.4
    if shake > 0.01:
        p.translate((random.random() - 0.5) * shake, (random.random() - 0.5) * shake)
    bx, by, bw, bh = 395, 70, 210, 530
    trig, bump = ("LT", "LB") if left else ("RT", "RB")
    # the trigger (ZL / ZR) and the shoulder (L / R) along the top edge
    u = r.axes[trig]
    p.rr(410, 14, 180, 30, 9)
    p.fill("idle")
    p.rr(410, 14, max(0.001, 180 * u), 30, 9)
    p.fill("hot" if u > 0.98 else "accent", 0.85)
    p.rr(410, 14, 180, 30, 9)
    p.stroke("idleLine", 1.5)
    p.text(f"{_glyph(r, trig)} {round(u * 100)}%", 500, 29, size=13, weight=700,
           color="#10131a" if u > 0.55 else "text")
    p.hit(410, 14, 180, 30, f"axis:{trig}")
    on = _pressed(r, bump)
    p.rr(410, 50, 180, 16, 8)
    p.fill("hot" if on else "idle")
    p.text(_glyph(r, bump), 500, 58, size=11, color="#000" if on else "dim", weight=700)
    p.hit(410, 50, 180, 16, f"pad:{bump}")
    # the body, the rail marked on its inner edge
    p.rr(bx, by, bw, bh, 46)
    p.fill(JOYCON_BODY[kind])
    p.rr(bx, by, bw, bh, 46)
    p.stroke("bodyLine", 2.5)
    rail_x = bx + bw if left else bx
    p.lines((rail_x, by + 60), (rail_x, by + bh - 60))
    p.stroke(ink, 3, a=0.5)
    # − / +, the stick and the face (the (L)'s stick above its arrows, the
    # (R)'s face above its stick), capture / HOME
    if left:
        _pill(p, r, "VIEW", 548, 96, 26, 8, word_y=118)
        _stick(p, r, "LSTICK", 500, 205, "LX", "LY")
        face_cy = 345
    else:
        _pill(p, r, "MENU", 426, 96, 26, 8, word_y=118)
        face_cy = 235
        _stick(p, r, "LSTICK", 500, 420, "LX", "LY")
    for n, (dx, dy) in (("N", (0, -48)), ("W", (-48, 0)), ("E", (48, 0)), ("S", (0, 48))):
        x, y = 500 + dx, face_cy + dy
        on = _pressed(r, n)
        p.circle(x, y, 23)
        p.fill(ink if on else "idle")
        p.circle(x, y, 23)
        p.stroke(ink, 2)
        p.text(_glyph(r, n), x, y + 1, size=20, color="#000" if on else ink, weight=700)
        p.hit(x - 23, y - 23, 46, 46, f"pad:{n}")
    if left:
        on = _pressed(r, "SHARE")
        p.rr(538, 505, 24, 24, 5)
        p.fill("hot" if on else "idle")
        p.text(_glyph(r, "SHARE"), 550, 517, size=12, color="#000" if on else "dim")
        p.text("capture", 550, 545, size=10, color="dim")
        p.hit(532, 499, 36, 36, "pad:SHARE")
    else:
        on = _pressed(r, "GUIDE")
        p.circle(450, 525, 14)
        p.fill("hot" if on else "idle")
        p.circle(450, 525, 14)
        p.stroke("idleLine", 1.5)
        p.text("HOME", 450, 551, size=10, color="dim")
        p.hit(436, 511, 28, 28, "pad:GUIDE")
    # SL and SR on the rail, the four player lights between them
    for n, y0 in (("LP", 150), ("RP", 330)):
        on = _pressed(r, n)
        p.rr(rail_x - 7, y0, 14, 90, 6)
        p.fill("back" if on else "idle")
        p.rr(rail_x - 7, y0, 14, 90, 6)
        p.stroke("back" if on else "idleLine", 1.5)
        p.text(_glyph(r, n), rail_x + (22 if left else -22), y0 + 45, size=11,
               color="back" if on else "dim", weight=700)
        p.hit(rail_x - 10, y0 - 4, 20, 98, f"pad:{n}")
    lit = nintendo.player_leds(players) if players is not None else 0
    for i in range(4):
        p.rr(rail_x - 5, 252 + i * 16, 10, 10, 2)
        p.fill("#ffffff" if (lit >> i) & 1 else "#2b3242")
    _rumble_rings(p, r_low, r_high, 200, 470, 200, 555)        # under the stick's well
    p.restore()
    # the tilt (what the lanes make of it), then all six axes as traces
    if r.has("motion"):
        _attitude(p, r, st, 800, 118, 50, True, now)
        m = r.motion
        if m is not None and _pulse(st, "shake_word", bool(m.get("shake")), now):
            p.text("SHAKE", 930, 60, size=20, color="hot", weight=800)
        _scope(p, r, st, 648, 236, 336, 55)
    # the stick's calibration: its well with the deadzone ring, the reading
    cx, cy, rad = 200, 200, 70
    p.circle(cx, cy, rad)
    p.fill("well")
    p.circle(cx, cy, rad)
    p.stroke("idleLine", 1.5)
    p.circle(cx, cy, rad * gamepad.DEADZONE)
    p.stroke("#2a3242", 1)
    for a, b in (((cx - rad, cy), (cx + rad, cy)), ((cx, cy - rad), (cx, cy + rad))):
        p.lines(a, b)
        p.stroke("#232a38", 1)
    sx, sy = r.axes["LX"], r.axes["LY"]
    x = cx + (sx - 0.5) * 2 * rad
    y = cy - (sy - 0.5) * 2 * rad
    inside = math.hypot(sx - 0.5, sy - 0.5) * 2 < gamepad.DEADZONE
    p.circle(x, y, 6)
    p.fill("dim" if inside else ink)
    p.text("stick", cx, cy - rad - 14, size=11, color="dim")
    p.text(f"LX {sx:.2f}  LY {sy:.2f}", cx, cy + rad + 18, size=11, color="dim", mono=True)
    if r.stick_raw is not None and r.stick_centre is not None:
        (rx, ry), (ccx, ccy) = r.stick_raw, r.stick_centre
        p.text(f"raw {rx}, {ry}", cx, cy + rad + 36, size=11, color="dim", mono=True)
        p.text(f"centre {ccx}, {ccy} ({r.centre_from})", cx, cy + rad + 52, size=11,
               color="dim", mono=True)
    p.hit(cx - rad, cy - rad, 2 * rad, 2 * rad, "axis:LX")
    if r.battery >= 0 or r.on:
        _battery(p, r, 14, 10, below=True)
    name = getattr(r.model, "name", "") if r.on else "no pad"
    p.text(f"{name or 'pad'} · {r.link or '—'}", 12, 610, size=12, color="dim", align="left")


def _cockpit_joycon(p: Pen, r, st: dict, now: float, players, r_low, r_high) -> None:
    """A Joy-Con's cockpit: its one dial (the trigger's arc, the shoulder's
    cap, the stick's trail), the tilt big beside it, the buttons it has,
    SL and SR loud on the edges, the rumble meters, the ticker."""
    kind = r.kind
    left = kind == "l"
    ink = JOYCON_INK[kind]
    p.rr(0, 0, DESIGN_W, DESIGN_H, 0)
    p.fill("cockpit")
    word = f"JOY-CON ({kind.upper()}) · {(r.link or '—').upper()}" if r.on else "NO PAD"
    p.text(word, 22, 40, size=12, align="left", color="dim", weight=700)
    lit = nintendo.player_leds(players) if players is not None else 0
    for i in range(4):
        p.circle(476 + i * 16, 40, 4.5)
        p.fill("#ffffff" if (lit >> i) & 1 else "#262d3c")
    if r.battery >= 0 or r.on:
        _battery(p, r, 935, 31)
    _dial(p, r, st, 245, 270, "L" if left else "R", _trig(None), stick="LSTICK", ax="LX", ay="LY")
    if r.has("motion"):
        _attitude(p, r, st, 640, 240, 115, True, now)
        _six_bars(p, r, 104, 438, 282)             # all six axes, as bars, under the dial
    names = ("VIEW", "SHARE") if left else ("MENU", "GUIDE")
    for i, n in enumerate(names):
        x, on = 608 + i * 64, _pressed(r, n)
        p.rr(x - 28, 456, 56, 22, 11)
        p.fill("hot" if on else "#161b26")
        p.text(_glyph(r, n), x, 467, size=11, color="#000" if on else "dim", weight=600)
        p.hit(x - 28, 456, 56, 22, f"pad:{n}")
    _cluster(p, r, 755, 500, [(f"pad:{n}", _glyph(r, n), dx, dy, ink)
                              for n, dx, dy in (("N", 0, -1), ("E", 1, 0), ("S", 0, 1),
                                                ("W", -1, 0))], COL["hot"])
    for n, x in (("LP", 22), ("RP", 918)):
        on = _pressed(r, n)
        p.rr(x, 170, 60, 110, 14)
        p.fill("back" if on else "#171c27")
        p.rr(x, 170, 60, 110, 14)
        p.stroke("#ffd1a0" if on else "#2b3446", 2)
        p.text(_glyph(r, n), x + 30, 225, size=14, color="#000" if on else "dim", weight=800)
        p.hit(x, 170, 60, 110, f"pad:{n}")
    for x, v, lbl, c in ((22, r_low, "heavy", "back"), (918, r_high, "light", "fn")):
        p.rr(x, 346, 60, 10, 5)
        p.fill("#161b26")
        if v > 0.005:
            p.rr(x, 346, max(0.5, 60 * v), 10, 5)
            p.fill(c)
        p.text(f"rumble {lbl}", x + 30, 368, size=8, color="faint")
    _ticker(p, r, st, now)


# the six axes: (key, label, unit, full scale), accel in g then gyro in deg/s,
# in the pad's axes — x right, y up out of the face, z toward the player
SCOPE_N = 180                 # samples kept per trace (~3 s at the pad window's rate)
ACCEL_FS, GYRO_FS = 2.0, 720.0
SIX_AXES = (("ax", "accel x", "g", ACCEL_FS), ("ay", "accel y", "g", ACCEL_FS),
            ("az", "accel z", "g", ACCEL_FS), ("gx", "gyro x", "°/s", GYRO_FS),
            ("gy", "gyro y", "°/s", GYRO_FS), ("gz", "gyro z", "°/s", GYRO_FS))
SIX_INK = {"ax": "#6cb6ff", "ay": "#40e0a0", "az": "#ff7ad9", "gx": "#6cb6ff", "gy": "#40e0a0",
           "gz": "#ff7ad9"}
SIX_WORDS = {"ax": "right +", "ay": "out of the face +", "az": "toward you +",
             "gx": "about x: far end rises +", "gy": "about y: turns left +",
             "gz": "about z: right side rises +"}


def _six(r) -> dict[str, float] | None:
    """The six axes this frame, by key, or None without sensor data."""
    s = r.sensors
    if s is None:
        return None
    (gx, gy, gz), (ax, ay, az) = s
    return {"ax": ax, "ay": ay, "az": az, "gx": gx, "gy": gy, "gz": gz}


def _scope(p: Pen, r, st: dict, x, y, w, row_h) -> None:
    """All six degrees of freedom as traces (plan 46): the accelerometer's
    x, y, z in g and the gyro's x, y, z in deg/s, each row the last
    `SCOPE_N` frames scrolling left, its baseline at zero, the value now
    and the chip's own count at the right. The traces are the state kept
    on the panel (`st["scope"]`)."""
    six = _six(r)
    traces = st.setdefault("scope", {k: [] for k, *_ in SIX_AXES})
    raw = r.raw_sensors
    raw_by = {}
    if raw is not None:
        (rgx, rgy, rgz), (rax, ray, raz) = raw
        raw_by = {"ax": rax, "ay": ray, "az": raz, "gx": rgx, "gy": rgy, "gz": rgz}
    p.text("six axes · the pad's x right, y out of the face, z toward you", x + w / 2,
           y - 10, size=10.5, color="dim")
    label_w, val_w = 58, 96
    tx0, tw = x + label_w, w - label_w - val_w
    for k, (key, label, unit, fs) in enumerate(SIX_AXES):
        ry = y + k * row_h
        mid = ry + row_h / 2
        tr = traces.setdefault(key, [])
        if six is not None:
            tr.append(float(six[key]))
            del tr[:-SCOPE_N]
        ink = SIX_INK[key]
        p.rr(tx0, ry + 4, tw, row_h - 8, 4)
        p.fill("well")
        p.lines((tx0, mid), (tx0 + tw, mid))
        p.stroke("#2a3242", 1)
        for frac in (0.5, -0.5):                          # half scale, faint
            p.lines((tx0, mid - frac * (row_h / 2 - 6)), (tx0 + tw, mid - frac * (row_h / 2 - 6)))
            p.stroke("#1c2230", 1)
        if len(tr) >= 2:
            n = len(tr)
            pts = [(tx0 + tw * (i / (SCOPE_N - 1)) + tw * (1 - (n - 1) / (SCOPE_N - 1)),
                    mid - max(-1.0, min(1.0, v / fs)) * (row_h / 2 - 6)) for i, v in enumerate(tr)]
            p.lines(*pts)
            p.stroke(ink, 1.6, cap="round")
        p.text(label, x + label_w - 6, mid - 6, size=11, color=ink, align="right", weight=700)
        p.text(f"±{fs:g} {unit}", x + label_w - 6, mid + 8, size=9, color="faint", align="right")
        if six is not None:
            v = six[key]
            p.text(f"{v:+.2f}" if unit == "g" else f"{v:+.0f}", x + w, mid - 6, size=12,
                   color=ink, align="right", mono=True, weight=700)
            if key in raw_by:
                p.text(f"raw {raw_by[key]:+d}", x + w, mid + 8, size=9, color="faint",
                       align="right", mono=True)
        else:
            p.text("—", x + w, mid, size=12, color="faint", align="right")
    p.text("  ·  ".join(f"{k}: {SIX_WORDS[k]}" for k in ("ax", "ay", "az")), x + w / 2,
           y + 6 * row_h + 6, size=9, color="faint")
    p.text("  ·  ".join(f"{k}: {SIX_WORDS[k]}" for k in ("gx", "gy", "gz")), x + w / 2,
           y + 6 * row_h + 18, size=9, color="faint")
    p.hit(x, y, w, 6 * row_h, "motion:spin.roll")


def _six_bars(p: Pen, r, x, y, w) -> None:
    """The six axes as bipolar bars, for a glance: a bar from the centre
    for each, the accelerometer's in g, the gyro's in deg/s."""
    six = _six(r)
    row_h = 17
    label_w = 52
    bx, bw = x + label_w, w - label_w - 44
    for k, (key, label, unit, fs) in enumerate(SIX_AXES):
        ry = y + k * row_h
        ink = SIX_INK[key]
        p.rr(bx, ry + 4, bw, row_h - 8, 4)
        p.fill("#161b26")
        cx = bx + bw / 2
        p.lines((cx, ry + 3), (cx, ry + row_h - 3))
        p.stroke("#2b3446", 1)
        p.text(label, bx - 5, ry + row_h / 2, size=9.5, color=ink, align="right", weight=700)
        if six is None:
            continue
        u = max(-1.0, min(1.0, six[key] / fs))
        if abs(u) > 0.004:
            x0, x1 = (cx, cx + u * bw / 2) if u > 0 else (cx + u * bw / 2, cx)
            p.rr(x0, ry + 5, max(0.5, x1 - x0), row_h - 10, 3)
            p.fill(ink, 0.9)
        v = six[key]
        p.text(f"{v:+.2f}" if unit == "g" else f"{v:+.0f}", x + w, ry + row_h / 2, size=9.5,
               color=ink, align="right", mono=True)
    p.hit(x, y, w, 6 * row_h, "motion:spin.roll")


VIEWS = {"faithful": faithful, "cockpit": cockpit}
