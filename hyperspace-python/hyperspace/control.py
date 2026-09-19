"""Headless panel state — the non-visual logic behind the control surface.

Ported semantics (ENGINEERING §4): scenes are the unit of intent, so Reset
resolves to the currently selected scene, never to hard-coded defaults;
Reset-all is guarded by an 8 s undo (the button relabels itself) whose
snapshot is discarded on a scene change because it belongs to the old
scene. Knob edits and transfer changes never move the scene selection.

The analyzer has N bands (plan 07), so the panel also adds, removes and
moves them and applies a preset's layout. Every one of those changes the
set of `band.*` ids the registry declares; `on_layout` is the hook
build_registry installs to rebuild them, and every path that can change
the layout — including a scene or an undo that carries one — calls it.

Kept free of imgui so tests can drive it directly; ui.py only draws it.
"""

from __future__ import annotations

import time
from dataclasses import replace

from .analyzer import Analyzer
from .bands import PRESETS

UNDO_S = 8.0


class Control:
    def __init__(self, chain: Analyzer, clock=time.monotonic):
        self.chain = chain
        self.clock = clock
        self.selb = 0            # band whose strip is open
        self.scene = 0           # the live scene — source of truth for resets
        self.on_layout = None    # rebuilds the band.* params; set by build_registry
        self._undo_snap = None
        self._undo_at = 0.0

    # ---- layout ----

    def _layout_changed(self) -> None:
        self.selb = max(0, min(self.selb, self.chain.n - 1))
        if self.on_layout is not None:
            self.on_layout()

    def _keeping_layout(self, fn) -> None:
        """Run fn; if it reshaped the band set, rebuild what depends on it."""
        before = self.chain.layout_version
        fn()
        if self.chain.layout_version != before:
            self._layout_changed()

    def apply_layout(self, layout: dict) -> None:
        """A preset's layout: applied before its values (plan 07 contract)."""
        self.clear_undo()        # the snapshot's bands may no longer exist
        self.chain.apply_layout(layout)
        self._layout_changed()

    def add_band(self) -> int:
        """A new band in the widest gap; it becomes the open strip."""
        self.clear_undo()
        self.selb = self.chain.add_band()
        self._layout_changed()
        return self.selb

    def remove_band(self, i: int | None = None) -> None:
        if self.chain.n <= 1:
            return               # the last band stays
        self.clear_undo()
        self.chain.remove_band(self.selb if i is None else i)
        self._layout_changed()

    def move_band(self, i: int, j: int) -> None:
        """Strip order; the open strip follows the band it was on."""
        if i == j:
            return
        self.clear_undo()
        sel = self.selb
        self.chain.move_band(i, j)
        order = list(range(self.chain.n))
        order.insert(j, order.pop(i))
        self.selb = order.index(sel)
        self._layout_changed()

    # ---- scenes ----

    def select_scene(self, k: int) -> None:
        self.clear_undo()        # that snapshot belongs to the old scene
        self.scene = k if 0 <= k < len(PRESETS) else 0
        self._keeping_layout(lambda: self.chain.apply_preset(self.scene))

    # ---- reset / undo ----

    @property
    def undo_armed(self) -> bool:
        if self._undo_snap is not None and self.clock() - self._undo_at >= UNDO_S:
            self.clear_undo()    # window lapsed
        return self._undo_snap is not None

    def clear_undo(self) -> None:
        self._undo_snap = None

    def reset_band(self, i: int | None = None) -> None:
        self.chain.apply_preset_band(self.scene, self.selb if i is None else i)

    def reset_all_clicked(self) -> None:
        """The one button: resets, or undoes if the window is still open."""
        if self.undo_armed:
            self._undo_reset_all()
        else:
            self._reset_all()

    def _reset_all(self) -> None:
        # the snapshot carries the layout too: a scene may change the bands
        self._undo_snap = (self.chain.layout(), [replace(p) for p in self.chain.params])
        self._undo_at = self.clock()
        self._keeping_layout(lambda: self.chain.apply_preset(self.scene))

    def _undo_reset_all(self) -> None:
        snap = self._undo_snap
        self.clear_undo()
        if snap is None:
            return
        layout, params = snap
        self._keeping_layout(
            lambda: self.chain.apply_layout(layout, params=[replace(p) for p in params])
        )

    # ---- band strip ----

    def set_shaper(self, band: int, fn: int) -> None:
        self.chain.params[band].fn = fn
        self.chain.st[band] = {}     # scratch state belongs to the old transfer
