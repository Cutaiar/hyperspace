"""Headless panel state — the non-visual logic behind the control surface.

Ported semantics (ENGINEERING §4): scenes are the unit of intent, so Reset
resolves to the currently selected scene, never to hard-coded defaults;
Reset-all is guarded by an 8 s undo (the button relabels itself) whose
snapshot is discarded on a scene change because it belongs to the old
scene. Knob edits and transfer changes never move the scene selection.

Kept free of imgui so tests can drive it directly; ui.py only draws it.
"""

from __future__ import annotations

import time
from dataclasses import replace

from .bands import PRESETS, Chain

UNDO_S = 8.0


class Control:
    def __init__(self, chain: Chain, clock=time.monotonic):
        self.chain = chain
        self.clock = clock
        self.selb = 0            # band whose strip is open
        self.scene = 0           # the live scene — source of truth for resets
        self._undo_snap = None
        self._undo_at = 0.0

    # ---- scenes ----

    def select_scene(self, k: int) -> None:
        self.clear_undo()        # that snapshot belongs to the old scene
        self.scene = k if 0 <= k < len(PRESETS) else 0
        self.chain.apply_preset(self.scene)

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
        self._undo_snap = [replace(p) for p in self.chain.params]
        self._undo_at = self.clock()
        self.chain.apply_preset(self.scene)

    def _undo_reset_all(self) -> None:
        snap = self._undo_snap
        self.clear_undo()
        if snap is None:
            return
        for i, saved in enumerate(snap):
            self.chain.params[i] = replace(saved)
            self.chain.st[i] = {}

    # ---- band strip ----

    def set_shaper(self, band: int, fn: int) -> None:
        self.chain.params[band].fn = fn
        self.chain.st[band] = {}     # scratch state belongs to the old transfer
