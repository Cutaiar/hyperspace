"""The APC40's sequencer page (plan 31 §A, decisions 7 and 10).

A **surface page**, not a third layer: while it is up its rows shadow every
row on their controls — the bank's pads, SAVE, the render toggles, the
SHIFT layer's scene pads — on both layers (`Bindings.page`, `dispatch`,
`active`). The rows live here, in memory: they are never in
`table.bindings`, never saved, and no Learn takes one of their controls
(`Bindings.is_invariant` says so while the page is up).

  SEND A          enters and leaves, latched (`seq.page`, an invariant row
                  of apc40.DEFAULT_MAP); its LED is lit while the page is up
  clip rows 1–5   lane 1–5's eight steps: a pad toggles ``seq.<l>.<s>``.
                  A column past ``seq.length`` is dark and does nothing
  scene 1–5       select the lane (`seq.select`); a tap on the lane already
                  selected toggles its mute (``seq.<l>.mute``)
  clip stop k     the pattern's length: ``seq.length = k``

Everything else on the desk — faders, knobs, SHIFT and its layers, the
transport, TAP / NUDGE, QUANT, OVERDUB, the track strips, STOP ALL and
MASTER — is as it was. A preset load does not leave the page.

Lights (one rule, `routing.led_shade`, read by midi.py and ui_desk.py):

  a step on                     on (green)
  a step on, its lane muted     muted (red)
  the playhead on a lit step    hit (yellow), on an unmuted lane
  clip stop k                   on while the playhead is in column k
  scene k                       on = the lane selected, muted (a blink)

The page reads the sequencer only through the registry (``seq.*``, declared
by sequencer.register), so it needs nothing of the app's wiring: until the
sequencer's params exist SEND A does nothing.

Below routing.py, which imports it to declare `seq.page` with the desk's
other params (`register_desk`): `Binding` is imported where a row is made.
"""

from __future__ import annotations

from collections.abc import Callable

from . import apc40
from .sequencer import LANES, STEPS

NAME = "seq"
PARAM = "seq.page"              # SEND A's latch (routing.SEQ_PAGE_PARAM)
SELECT_PARAM = "seq.select"     # the lane the scene buttons have selected


def row(source: str, target: str, op: str, value: float = 1.0, *, words: str,
        shade: Callable, **kw):
    """A row of a surface page: a `routing.Binding` with its own light
    (`shade`: the param → one of routing.SHADES, read by `led_shade`) and
    its own words on the on-screen desk (`words`, "L1·3")."""
    from .routing import Binding

    b = Binding(source, target, op, value, feedback="led", **kw)
    b.words, b.shade = words, shade
    return b


class SeqPage:
    """The page's state (the lane selected) and its rows, rebuilt only when
    what they say changes: the lane selected or the length."""

    name = NAME

    def __init__(self, reg):
        self.reg = reg
        self.lane = 0                   # 0-based, like the router's addresses
        self._key: tuple | None = None
        self._rows: list = []

    # ---- the sequencer, read off the registry ----

    def ready(self) -> bool:
        """Are the sequencer's params there to be a page of?"""
        return "seq.length" in self.reg and "seq.1.1" in self.reg

    def _value(self, pid: str, default):
        p = self.reg.get(pid)
        return default if p is None else p.value

    def length(self) -> int:
        return int(self._value("seq.length", STEPS))

    def playhead(self) -> int:
        """The 1-based step under the playhead, 0 while stopped (`seq.step`)."""
        return int(self._value("seq.step", 0))

    def muted(self, lane: int) -> bool:
        return bool(self._value(f"seq.{lane + 1}.mute", False))

    def header(self) -> str:
        """The on-screen desk's line: "SEQ · lane 2 · L=8"."""
        return f"SEQ · lane {self.lane + 1} · L={self.length()}"

    # ---- the rows ----

    def rows(self) -> list:
        """The page's rows as they stand. The same objects until the lane
        selected or the length changes; a rebuild keeps each control's last
        sent light, so midi.py still sends only what changed."""
        key = (self.lane, self.length())
        if key != self._key:
            sent = {b.control: b.last_out for b in self._rows}
            self._rows = self._build(*key)
            for b in self._rows:
                b.last_out = sent.get(b.control)
            self._key = key
        return self._rows

    def _build(self, lane: int, length: int) -> list:
        out = []
        for li in range(LANES):
            for si in range(STEPS):
                out.append(row(f"note:{si}:{apc40.N_CLIP[li]}", f"seq.{li + 1}.{si + 1}",
                               "toggle", enabled=si < length, on=apc40.GREEN,
                               words=f"L{li + 1}·{si + 1}", shade=self._step_shade(li, si)))
        for li in range(LANES):
            source, shade = f"note:0:{apc40.N_SCENE[li]}", self._scene_shade(li)
            if li == lane:      # the lane selected: a tap mutes it
                out.append(row(source, f"seq.{li + 1}.mute", "toggle",
                               words=f"mute {li + 1}", shade=shade))
            else:
                out.append(row(source, SELECT_PARAM, "set", float(li),
                               words=f"lane {li + 1}", shade=shade))
        for k in range(STEPS):
            out.append(row(f"note:{k}:{apc40.N_CLIPSTOP}", "seq.length", "set",
                           k / (STEPS - 1), words=f"L={k + 1}", shade=self._stop_shade(k)))
        return out

    def _step_shade(self, li: int, si: int) -> Callable:
        def shade(p) -> str:
            if si >= self.length() or not p.value:
                return "off"
            if self.muted(li):
                return "muted"
            return "hit" if self.playhead() == si + 1 else "on"
        return shade

    def _scene_shade(self, li: int) -> Callable:
        def shade(_p) -> str:
            if self.muted(li):
                return "muted"
            return "on" if li == self.lane else "off"
        return shade

    def _stop_shade(self, k: int) -> Callable:
        def shade(_p) -> str:
            return "on" if self.playhead() == k + 1 else "off"
        return shade


def page_of(table) -> SeqPage | None:
    """The sequencer page if it is the one up on `table`, else None."""
    page = getattr(table, "page", None)
    return page if isinstance(page, SeqPage) else None


def register(reg, table) -> SeqPage | None:
    """`seq.page` — SEND A's latch, a session toggle over the table like
    `desk.shift`: on puts the page up (once the sequencer's params exist),
    off takes it down — and `seq.select`, the lane the scene buttons pick.
    Neither is saved or modulated. The first table a registry meets keeps
    them (routing.register_desk calls this). Returns the page made, or
    None when the registry has one already."""
    if PARAM in reg:
        return None
    page = SeqPage(reg)

    def put(v) -> None:
        table.set_page(page if v and page.ready() else None)

    reg.toggle(PARAM, "Sequencer page", lambda: table.page is page, put,
               group="desk", persist=False, modulatable=False,
               tip="The APC40's SEND A, latched: on, the clip grid is the step "
                   "sequencer's — rows 1–5 the lanes' steps, scene 1–5 select a lane "
                   "(again: mute it), clip stop k the length. Off, the bank, SAVE and the "
                   "render toggles are back. A preset load leaves it as it is.")
    reg.enum(SELECT_PARAM, "Seq lane", lambda: page.lane,
             lambda v: setattr(page, "lane", min(max(int(v), 0), LANES - 1)),
             [f"lane {i + 1}" for i in range(LANES)], group="desk", persist=False,
             modulatable=False,
             tip="The lane the sequencer page's scene buttons have selected; a tap "
                 "on it again mutes it.")
    return page
