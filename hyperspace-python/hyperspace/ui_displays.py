"""The output section's rows (wave 5 SC2): one per connected display, each choosing what
targets it, with its fullscreen and flips. Not a dropdown of screens: the owner, 2026-11-06.

What the rows are, and the file they go to, is `displays.py`. A change of target acts on ⌘R
until SC3b, and the section says so; fullscreen and flips act at once on a window that's open
there. Nothing here touches the disk or a window system's list but `Running.screens`, drawn only
while the section is.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import displays, placement, ui
from .displays import CONTROL, NOTHING, Running

TIP_TARGET = ("What this display shows: the control window, an output, or nothing. A display has "
              "one target; an output may go to several displays; the control window goes to one. "
              "Both Macs share this, each display remembering its job by name. A change of "
              "target acts on ⌘R.")
TIP_FULLSCREEN = ("Borderless, covering this display. No video-mode switch. It covers the control "
                  "window too, if that's on this display.")
TIP_FLIP = ("Mirrors the whole picture on this display, for a glass that reflects it. Each display "
            "of an output has its own.")
ON_RESTART = "⌘R to apply: "
NO_RENDER = "No display shows an output: the picture is only on GRAPH."


def choices(slots: list) -> list[tuple[str, str]]:
    """(target, words) of what a row may choose: nothing, the control window, every output."""
    return [(NOTHING, "nothing"), (CONTROL, "control window"),
            *((f"output.{sl.n}", sl.label) for sl in slots)]


def words(target: str, slots: list) -> str:
    return next((w for t, w in choices(slots) if t == target), target)


def _tick(panel, run: Running, tag: str, key: str, on: bool, target: str) -> None:
    """A tick on the row, and on the window that's open there for this target, at once. The
    window's first display goes through the params the desk's rows name."""
    run.store.set(tag, **{key: on})
    open_on = run.window_on(tag)
    if open_on is None or run.opened.get(tag) != target:
        return
    sl, also = open_on
    if also is not None:
        if key == "fullscreen":
            also.output.fullscreen = on
        else:
            setattr(also, key, on)
    elif key == "fullscreen":
        if sl.n == 1 and "output.fullscreen" in panel.reg:
            panel.reg["output.fullscreen"].set(on)
        elif sl.output is not None:
            sl.output.fullscreen = on
    elif f"output.{sl.n}.{key}" in panel.reg:
        panel.reg[f"output.{sl.n}.{key}"].set(on)
    else:
        setattr(sl.switches, key, on)


def _shown(run: Running, tag: str, key: str, row: dict, target: str) -> bool:
    """What a tick says: the open window's, as the desk may have moved it; else the row's."""
    open_on = run.window_on(tag)
    if open_on is None or run.opened.get(tag) != target or key == "fullscreen":
        return row[key]
    sl, also = open_on
    return bool(getattr(also if also is not None else sl.switches, key))


def _warn(line: str) -> None:
    """Words that must be read whole, at any width of the pane."""
    imgui.push_text_wrap_pos(0.0)
    imgui.text_colored(ui.WARN, line)
    imgui.pop_text_wrap_pos()


def _row(panel, run: Running, k: int, tag: str, connected: list[str]) -> None:
    """One display: its name, what targets it, and for an output its ticks. `k` is its place
    across the desk: a name may hold anything an id can't."""
    row = displays.read_row(displays.find(run.store.current, tag))
    picks = choices(run.slots)
    at = next((i for i, (t, _) in enumerate(picks) if t == row["target"]), 0)
    imgui.align_text_to_frame_padding()
    width = imgui.get_content_region_avail().x
    imgui.text(ui.fit_text(tag, width))
    if imgui.is_item_hovered():
        ui.tooltip(tag)
    imgui.set_next_item_width(-1)
    changed, chosen = imgui.combo(f"##display.{k}.target", at, [w for _, w in picks])
    if imgui.is_item_hovered():
        ui.tooltip(TIP_TARGET)
    if changed:
        run.store.set_target(tag, picks[chosen][0], connected)
    if displays.output_of(row["target"]) is None:
        return
    open_on = run.window_on(tag)
    for i, (key, text, tip) in enumerate((("fullscreen", "fullscreen", TIP_FULLSCREEN),
                                          ("flip_x", "flip X", TIP_FLIP), ("flip_y", "flip Y", TIP_FLIP))):
        if i:
            ui.beside(ui.check_w(text))
        hit, on = imgui.checkbox(f"{text}##display.{k}.{key}", _shown(run, tag, key, row, row["target"]))
        if imgui.is_item_hovered():
            ui.tooltip(tip)
        if hit:
            _tick(panel, run, tag, key, on, row["target"])
    wrong = open_on[1].error if open_on is not None and open_on[1] is not None else ""
    if wrong:
        imgui.text_colored(ui.WARN, ui.fit_text(wrong, imgui.get_content_region_avail().x))


def section(panel, run: Running) -> None:
    """Every connected display, across the desk, and what's waiting."""
    scr = run.screens()
    if not scr:
        imgui.text_disabled("no display says it's connected")
        return
    tags = placement.labels(scr)
    connected = [tags[i] for i in placement.arranged(scr)]
    for k, tag in enumerate(connected):
        _row(panel, run, k, tag, connected)
    if run.store.said:
        _warn(run.store.said)
    want = displays.wanted(run.store.current, scr)
    if not want.renders:
        _warn(NO_RENDER)
    for note in want.notes:
        _warn(note)
    waiting = displays.pending(run.store.current, scr, run.opened)
    if waiting:
        _warn(ON_RESTART + ", ".join(f"{tag} shows {words(t, run.slots)}" for tag, t in waiting))
    imgui.dummy(imgui.ImVec2(0, 2))
