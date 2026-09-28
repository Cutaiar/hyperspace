"""Headless panel state — the non-visual logic behind the control surface.

Ported semantics (ENGINEERING.md, audio chain section): scenes are the
unit of intent, so Reset
resolves to the currently selected scene, never to hard-coded defaults;
Reset-all is guarded by an 8 s undo (the button relabels itself) whose
snapshot is discarded on a scene change because it belongs to the old
scene. Knob edits and transfer changes never move the scene selection.

A scene *is* a band preset (plan 11, audit A1): the eleven files in
library/band/*.json, named here in combo order (SCENES) because the APC40's
clip grid and every saved project address them by index. The combo, the
grid and Reset re-tune whatever bands are loaded from the scene's values
— an object write on the analyzer's Params, folded into the base next
frame (ARCHITECTURE §3.2) — and tell the library which scene is current;
a load from the preset strip (Library.load) goes the other way, layout
included, and tells the combo. With no library attached the factory file
is read directly (library.factory_doc), so the headless tests need none.

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

from .analyzer import Analyzer, scene_rows
from .library import LibraryError, factory_doc

UNDO_S = 8.0
BAND_GROUP = "band"
# the scenes, in combo order — the index is what scene.select, the APC40's
# clip grid and a project's values hold, so this list is append-only
SCENES = ("Balanced", "Kick & Sizzle", "Glacial Drift", "Strobe Cage", "Bass Engine",
          "Air & Lace", "Inverse World", "Percussive", "Tremolo Web", "Harmonic Bloom",
          "Slow Bass / Fast Air")


class Control:
    def __init__(self, chain: Analyzer, clock=time.monotonic, library=None):
        self.chain = chain
        self.clock = clock
        self.library = library   # reads the scenes (user shadows honoured); None → factory files
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

    @property
    def scene_names(self) -> list[str]:
        return list(SCENES)

    def scene_doc(self, k: int | None = None) -> dict:
        """The selected scene's band preset — the user's file if one shadows
        the factory's, else the factory's (a missing or broken file falls
        back to the factory copy and is reported on the library)."""
        name = SCENES[self.scene if k is None else k]
        if self.library is not None:
            try:
                return self.library.read(BAND_GROUP, name)
            except LibraryError as e:
                self.library.error = f"library: {e}"
        return factory_doc(BAND_GROUP, name)

    def select_scene(self, k: int) -> None:
        self.clear_undo()        # that snapshot belongs to the old scene
        self.scene = k if 0 <= k < len(SCENES) else 0
        self._apply_scene()

    def scene_loaded(self, name: str) -> None:
        """The strip loaded a band preset: if it is a scene, the combo follows
        (Library.on_load); a user preset that is not one leaves it."""
        if name in SCENES:
            self.clear_undo()
            self.scene = SCENES.index(name)

    def _apply_scene(self) -> dict:
        """The scene's values onto the bands loaded; the library is told."""
        doc = self.scene_doc()
        self.chain.apply_scene(doc.get("values") or {})
        if self.library is not None:
            self.library.adopt(BAND_GROUP, doc)
        return doc

    # ---- reset / undo ----

    @property
    def undo_armed(self) -> bool:
        if self._undo_snap is not None and self.clock() - self._undo_at >= UNDO_S:
            self.clear_undo()    # window lapsed
        return self._undo_snap is not None

    def clear_undo(self) -> None:
        self._undo_snap = None

    def reset_band(self, i: int | None = None) -> None:
        i = self.selb if i is None else i
        rows = scene_rows(self.scene_doc().get("values") or {})
        self.chain.apply_scene_band(i, rows.get(i))

    def reset_all_clicked(self) -> None:
        """The one button: resets, or undoes if the window is still open."""
        if self.undo_armed:
            self._undo_reset_all()
        else:
            self._reset_all()

    def _reset_all(self) -> None:
        # the snapshot carries the layout too, so an undo is whole whatever
        # a strip load did in between
        snap = (self.chain.layout(), [replace(p) for p in self.chain.params])
        self._apply_scene()
        self._undo_snap, self._undo_at = snap, self.clock()

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
