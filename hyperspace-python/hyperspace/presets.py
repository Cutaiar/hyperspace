"""Global interface themes — emulator-style save states for the whole surface.

A theme snapshots everything the control surface can set in one go — the
registry's whole-surface ``snapshot()``: every persisted parameter except
the routing layer's macros (params.ROUTING_GROUPS), which the binding
table carries. Loading one cuts the whole look over in a
single frame, so two contrasting slots can be flipped between on the beat.

F1–F8 load slots 1–8; ⇧F1–F8 save into them. The eight slots are the
project's *bank* (library.py): they persist in the open project's file
and the factory default project ships them seeded with the eight house
moods (hyperspace/library/projects/default.hyp.json), which come back
whenever a slot is empty.

A slot restores the modules it names, whole: every id in a group the slot
mentions is set, from the slot or else from the group's defaults, so a
theme is the same state whatever it lands on — while a group it never
mentions (the seeds carry a scene, not band values; no master fader) is
left alone. Rotation phases are never in a slot: a theme changes the
look, not where the spin is.
"""

from __future__ import annotations

from typing import Any

SLOTS = 8


class Presets:
    """The theme bank — a view onto the open project's eight slots."""

    def __init__(self, library):
        self.lib = library
        self.active = -1  # last slot loaded, -1 until one is
        self.error = ""

    @property
    def slots(self) -> list[dict | None]:
        return self.lib.project.bank

    # ---- capture / apply ----

    def capture(self, name: str) -> dict[str, Any]:
        return {"name": name, "values": self.lib.reg.snapshot()}

    def save(self, k: int) -> None:
        if not 0 <= k < SLOTS or self.lib.reg is None:
            return
        old = self.slots[k]
        name = old["name"] if old else f"THEME {k + 1}"
        self.slots[k] = self.capture(name)
        self.active = k
        self._write()

    def load(self, k: int) -> None:
        if not 0 <= k < SLOTS or self.slots[k] is None or self.lib.reg is None:
            return
        values = self.slots[k].get("values") or {}
        lib, reg = self.lib, self.lib.reg
        groups = {reg[pid].group for pid in values if pid in reg}
        merged: dict[str, Any] = {}
        for g in groups:
            merged.update(lib.defaults(g))
        merged.update(values)
        missing = lib.restore(merged)
        lib.report(missing, self.slots[k]["name"])
        self.active = k

    def cycle(self, step: int = 1) -> None:
        """Flip to the next saved slot — the gamepad's theme button."""
        filled = [k for k, s in enumerate(self.slots) if s is not None]
        if not filled:
            return
        if self.active in filled:
            k = filled[(filled.index(self.active) + step) % len(filled)]
        else:
            k = filled[0]
        self.load(k)

    # ---- persistence: the bank rides in the project file ----

    def _write(self) -> None:
        try:
            self.lib.project.write()
            self.error = ""
        except Exception as e:  # noqa: BLE001 — a full disk must not stop the show
            self.error = f"presets: {e}"
