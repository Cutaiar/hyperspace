"""Headless panel state — the non-visual logic behind the control surface.

Ported semantics (ENGINEERING.md, audio chain section): scenes are the
unit of intent, so Reset
resolves to the currently selected scene, never to hard-coded defaults;
Reset-all is guarded by an 8 s undo (the button relabels itself) whose
snapshot is discarded on a scene change because it belongs to the old
scene. Knob edits and transfer changes never move the scene selection.

A scene is a band preset's document (plan 11, audit A1): the eleven files
in hyperspace/scenes/band/*.json — code data, shipped with the build and
never a library preset (2026-10-28: the library has one tier, the
user's) — named here in combo order (SCENES) because the APC40's clip
grid and every saved project address them by index. The combo, the grid
and Reset re-tune whatever bands are loaded from the scene's values —
through the registry when one is attached (a base write, as a strip load
is, so a knob a performer holds keeps its offset and the strip reads
clean at once), else straight onto the analyzer's Params — and tell the
library which scene is current; a load from the band strip (Library.load,
the user's own band presets) goes the other way, layout included, and
tells the combo when its name is a scene's. The scene files are read
without a library (library.scene_doc), so the headless tests need none.

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
from pathlib import Path

from .analyzer import Analyzer, scene_strip
from .library import scene_doc, slug

UNDO_S = 8.0
BAND_GROUP = "band"
# the scene files: code data beside this module, never a library preset
SCENES_DIR = Path(__file__).with_name("scenes") / BAND_GROUP
# the scenes, in combo order — the index is what scene.select, the APC40's
# clip grid and a project's values hold, so this list is append-only
SCENES = ("Balanced", "Kick & Sizzle", "Glacial Drift", "Strobe Cage", "Bass Engine",
          "Air & Lace", "Inverse World", "Percussive", "Tremolo Web", "Harmonic Bloom",
          "Slow Bass / Fast Air")


class Control:
    def __init__(self, chain: Analyzer, clock=time.monotonic, library=None):
        self.chain = chain
        self.clock = clock
        self.library = library   # told which scene is current; None in the headless tests
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

    def scene_doc(self) -> dict:
        """The selected scene's document: its file under `SCENES_DIR`, by the
        scene's slug (library.scene_doc; a LibraryError for a file that is
        missing or broken — the build's own data, so never in practice)."""
        return scene_doc(SCENES_DIR / f"{slug(SCENES[self.scene])}.json")

    def scene_values(self) -> dict:
        """The scene's values, filled in the way a strip load fills a
        partial file (Library.resolved) when a library is attached, so the
        two roads never land different strips."""
        doc = self.scene_doc()
        values = doc.get("values") or {}
        lib = self.library
        if lib is not None and lib.reg is not None:
            values = lib.resolved(BAND_GROUP, values)
        return values

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

    def _land(self, strip: dict) -> None:
        """A scene's strip values onto the bands: through the registry when
        the library has one (a base write — a performed knob keeps its
        offset and is_dirty reads clean straight away), else onto the
        analyzer's Params (the headless tests, no library)."""
        lib = self.library
        if lib is not None and lib.reg is not None:
            lib.restore(strip)
        else:
            self.chain.apply_scene(strip)

    def _apply_scene(self) -> None:
        """The scene's values onto the bands loaded; the library is told,
        and re-applies it this way if the scene's file changes on disk."""
        self._land(scene_strip(self.scene_values(), self.chain.n))
        if self.library is not None:
            self.library.adopt(BAND_GROUP, SCENES[self.scene], self._apply_scene)

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
        self._land(scene_strip(self.scene_values(), self.chain.n, bands=(i,)))

    def reset_all_clicked(self) -> None:
        """The one button: resets, or undoes if the window is still open."""
        if self.undo_armed:
            self._undo_reset_all()
        else:
            self._reset_all()

    def _reset_all(self) -> None:
        # the snapshot carries the layout and the strip's current preset
        # too, so an undo is whole
        lib = self.library
        snap = (self.chain.layout(), [replace(p) for p in self.chain.params],
                None if lib is None else lib.landed(BAND_GROUP))
        self._apply_scene()
        self._undo_snap, self._undo_at = snap, self.clock()

    def _undo_reset_all(self) -> None:
        snap = self._undo_snap
        self.clear_undo()
        if snap is None:
            return
        layout, params, landed = snap
        self._keeping_layout(
            lambda: self.chain.apply_layout(layout, params=[replace(p) for p in params])
        )
        if landed is not None and self.library is not None:
            self.library.reland(BAND_GROUP, landed)

    # ---- band strip ----

    def set_shaper(self, band: int, fn: int) -> None:
        self.chain.params[band].fn = fn
        self.chain.st[band] = {}     # scratch state belongs to the old transfer
