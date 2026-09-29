"""Preset strip and project row — the library's face on the panel.

Every section of the panel that sits on a registry group the library
knows (library.groups()) carries a strip under its title:

  ◀  name ●  ▶      save   as…   reset

prev / next step through ``library.list(group)``; the name opens the
list (factory presets dim, user ones deletable); the dot is
``is_dirty(group)``; save overwrites the current preset — disabled for
a factory one, which can only be saved *as* something; as… turns the
strip into a name field until Enter (or Esc); reset lands the group on
its default preset — the "meaningful default" — or its fresh values when
it has none. The project row is the same idea over the open project
(name · dirty · save / as… / load ▾ / new, and the startup preset ▾),
over the F1–F8 **preset bank**: eight slots, each named by the preset
file it points at (click or F-key loads, ⇧click or ⇧F-key saves the live
state as it, the loaded one lit). Under the bank sits the one **preset
strip** — this same strip over the ``presets`` group, a document kind
preset.py keeps — and then the module overview (the performance groups
and the band strip's scene). The ROUTING page's strip is this same strip
over the ``bindings`` group — a document kind the library keeps for the
router (library.py, ``Library.routing``).

These are functions over the Panel rather than widget classes: the
state they need (the name field, the cached listings) lives on the
panel, and ui.py's imports rebind to fresh code on a hot reload. A
listing stats every file in the group's folders, so it is refreshed on
a poll cadence (LIST_POLL), never per frame; dirty state is a snapshot
compare and is cheap enough to ask each frame for the page on screen.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui
from .library import PRESETS, LibraryError
from .params import PERFORMANCE_GROUPS

LIST_POLL = 1.0      # seconds between re-listings of a group's presets
NAME_MAX = 14        # chars of a preset name the strip shows before eliding
PROJECT = "project"  # the listing / name-field key for the project row
LOAD_W = 88          # the project row's load ▾ combo
STARTUP_W = 120      # the project row's startup ▾ combo
SLOT_W = 40          # one F-key slot in the preset bank
# the module overview: every performance group but the macros (a macro's
# meaning is its subscribers, which live in the preset), and the band
# strip's scene, the one session module a project names
OVERVIEW_GROUPS = (*[g for g in PERFORMANCE_GROUPS if g != "macro"], "band")


# ---- state on the panel, created on first use ----

def _state(panel) -> dict:
    st = getattr(panel, "_lib_state", None)
    if st is None:
        st = panel._lib_state = {"lists": {}, "naming": None, "buf": "", "dirty": {}}
    return st


def names(panel, key: str) -> list[str]:
    """``library.list(group)`` (or the project list), refreshed on the poll cadence."""
    st, lib = _state(panel), panel.library
    now = imgui.get_time()
    hit = st["lists"].get(key)
    if hit is None or now - hit[0] >= LIST_POLL:
        try:
            listing = lib.project.list() if key == PROJECT else lib.list(key)
        except (LibraryError, OSError) as e:
            lib.error = f"library: {e}"
            listing = hit[1] if hit else []
        st["lists"][key] = hit = (now, listing)
    return hit[1]


def invalidate(panel, key: str) -> None:
    """Our own write: the next frame re-lists rather than waiting out the poll."""
    _state(panel)["lists"].pop(key, None)


def dirty(panel, group: str, *, polled: bool = False) -> bool:
    """``is_dirty(group)`` — live, or on the poll cadence for the rail dots."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return False
    if not polled:
        return lib.is_dirty(group)
    st, now = _state(panel), imgui.get_time()
    hit = st["dirty"].get(group)
    if hit is None or now - hit[0] >= LIST_POLL:
        st["dirty"][group] = hit = (now, lib.is_dirty(group))
    return hit[1]


def _elide(name: str) -> str:
    return name if len(name) <= NAME_MAX else name[: NAME_MAX - 1] + "…"


def name_w() -> float:
    """The strip's name button: NAME_MAX average characters and its padding."""
    return imgui.calc_text_size("n" * NAME_MAX).x + 2 * imgui.get_style().frame_padding.x


def _guard(panel, fn, *args):
    """Run a library call; a bad file or a full disk shows, never raises."""
    try:
        return fn(*args)
    except (LibraryError, OSError) as e:
        panel.library.error = f"library: {e}"
        return None


# ---- the name field: the strip while a save-as is being typed ----

def _name_field(panel, key: str, commit) -> bool:
    """Draw the inline name field for `key`; returns True while it is open."""
    st = _state(panel)
    if st["naming"] != key:
        return False
    imgui.set_next_item_width(-(ui.chip_w("ok", "×") + imgui.get_style().item_spacing.x))
    if st.pop("focus", False):          # the field takes the keyboard once, on open
        imgui.set_keyboard_focus_here()
    entered, st["buf"] = imgui.input_text_with_hint(
        f"##name.{key}", "preset name", st["buf"],
        imgui.InputTextFlags_.enter_returns_true | imgui.InputTextFlags_.auto_select_all,
    )
    imgui.same_line()
    ok = ui.chip(f"ok##{key}") or entered
    imgui.same_line()
    if ui.chip(f"×##{key}") or imgui.is_key_pressed(imgui.Key.escape):
        st["naming"] = None
    if ok:
        name = st["buf"].strip()
        if name:
            commit(name)
            st["naming"] = None
    return True


def _begin_naming(panel, key: str, seed: str) -> None:
    st = _state(panel)
    st["naming"], st["buf"], st["focus"] = key, seed, True


# ---- the strip ----

def strip(panel, group: str) -> None:
    """◀ name ● ▶ · save · as… · reset — for one registry group."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    imgui.push_id(f"strip.{group}")
    if _name_field(panel, group, lambda n: _save_as(panel, group, n)):
        imgui.pop_id()
        return
    cur = lib.current(group)
    listing = names(panel, group)
    factory = cur is not None and lib.is_factory(group, cur)
    is_dirty = dirty(panel, group)

    # ◀ name ▶ — the arrows step by name order; the name opens the list
    imgui.begin_disabled(not listing)
    if imgui.arrow_button("prev", imgui.Dir.left):
        _guard(panel, lib.prev, group)
    imgui.same_line(0, 2)
    label = _elide(cur) if cur else "—"
    imgui.push_style_color(imgui.Col_.button, imgui.ImVec4(0, 0, 0, 0))
    imgui.push_style_color(imgui.Col_.text, ui.DIM if factory or cur is None else
                           imgui.ImVec4(0.92, 0.92, 0.92, 1))
    if imgui.button(f"{label}##name", imgui.ImVec2(name_w(), 0)):
        imgui.open_popup("list")
    imgui.pop_style_color(2)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{cur}  ·  {'factory' if factory else 'user'} preset — "
                          "click for the list" if cur else "no preset loaded")
    if is_dirty:
        imgui.same_line(0, 0)
        imgui.text_colored(ui.RED, "●")
        if imgui.is_item_hovered():
            imgui.set_tooltip("edited since the preset loaded")
    imgui.same_line(0, 2)
    if imgui.arrow_button("next", imgui.Dir.right):
        _guard(panel, lib.next, group)
    imgui.end_disabled()
    _list_popup(panel, group, listing, cur)

    # save · as… · reset, flush right
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("save", "as…", "reset"))
    imgui.begin_disabled(cur is None or factory)
    if ui.chip("save"):
        _guard(panel, lib.overwrite, group)
        invalidate(panel, group)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        imgui.set_tooltip("Write the group's settings over the current preset"
                          + (" — a factory preset: save as… instead" if factory else ""))
    imgui.same_line()
    if ui.chip("as…"):
        _begin_naming(panel, group, cur or "")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Save the group's settings as a new user preset")
    imgui.same_line()
    if ui.chip("reset"):
        _guard(panel, lib.reset, group)
    if imgui.is_item_hovered():
        d = lib.default_name(group)
        imgui.set_tooltip(f"Back to the default preset — {d}" if d
                          else "Back to the values the module started with")
    imgui.pop_id()


def _save_as(panel, group: str, name: str) -> None:
    _guard(panel, panel.library.save_as, group, name)
    invalidate(panel, group)


def _list_popup(panel, group: str, listing: list[str], cur: str | None) -> None:
    lib = panel.library
    if not imgui.begin_popup("list"):
        return
    ui._micro(group)
    if not listing:
        imgui.text_disabled("no presets — save as… makes one")
    for name in listing:
        factory = lib.is_factory(group, name)
        imgui.push_style_color(imgui.Col_.text, ui.DIM if factory else
                               imgui.ImVec4(0.92, 0.92, 0.92, 1))
        picked, _ = imgui.selectable(f"{name}##pick", name == cur,
                                     imgui.SelectableFlags_.allow_overlap if not factory else 0)
        imgui.pop_style_color()
        if picked:
            _guard(panel, lib.load, group, name)
        if not factory:  # a user file: deletable from here
            imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("×"))
            imgui.push_style_color(imgui.Col_.text, ui.DIM)
            if ui.chip(f"×##del.{name}"):
                _guard(panel, lib.delete, group, name)
                invalidate(panel, group)
            imgui.pop_style_color()
            if imgui.is_item_hovered():
                imgui.set_tooltip("Delete this user preset (a factory one of the same "
                                  "name comes back)")
    imgui.end_popup()


# ---- the project row ----

def project_row(panel) -> None:
    """name ● · save · as… · load ▾ · new — the open project."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    proj = lib.project
    imgui.push_id("project")
    if _name_field(panel, PROJECT, lambda n: _project_save_as(panel, n)):
        imgui.pop_id()
        return
    imgui.text(proj.name)
    if imgui.is_item_hovered():
        imgui.set_tooltip(str(proj.path) if proj.path else
                          "not saved yet — save writes it into the library")
    if proj.is_dirty():
        imgui.same_line(0, 2)
        imgui.text_colored(ui.RED, "●")
        if imgui.is_item_hovered():
            imgui.set_tooltip("the live state differs from the project file")
    sp = imgui.get_style().item_spacing.x
    imgui.same_line(imgui.get_content_region_avail().x
                    - ui.chip_w("save", "as…", "new") - LOAD_W - STARTUP_W - 2 * sp)
    _startup_combo(panel, proj)
    imgui.same_line()
    if ui.chip("save"):
        _guard(panel, proj.save)
        invalidate(panel, PROJECT)
    if imgui.is_item_hovered():
        imgui.set_tooltip("Save the session — tempo, hands, the analyzer, output — "
                          "the preset bank and the startup preset into the project file")
    imgui.same_line()
    if ui.chip("as…"):
        _begin_naming(panel, PROJECT, proj.name)
    imgui.same_line()
    imgui.set_next_item_width(LOAD_W)
    if imgui.begin_combo("##load", "load"):
        listing = names(panel, PROJECT)
        if not listing:
            imgui.text_disabled("no saved projects")
        for name in listing:
            picked, _ = imgui.selectable(name, name == proj.name)
            if picked:
                _guard(panel, proj.load, name)
        imgui.end_combo()
    if imgui.is_item_hovered():
        imgui.set_tooltip("Open a project from the library")
    imgui.same_line()
    if ui.chip("new"):
        _guard(panel, proj.new)
    if imgui.is_item_hovered():
        imgui.set_tooltip("A fresh project: default state, the factory preset bank")
    imgui.pop_id()


def _startup_combo(panel, proj) -> None:
    """startup ▾ — the preset a launch and a project load bring up (D11)."""
    imgui.set_next_item_width(STARTUP_W)
    shown = _elide(proj.startup) if proj.startup else "startup"
    if imgui.begin_combo("##startup", shown):
        picked, _ = imgui.selectable("— none", proj.startup is None)
        if picked:
            proj.startup = None
        for name in names(panel, PRESETS):
            picked, _ = imgui.selectable(f"{name}##startup", name == proj.startup)
            if picked:
                proj.startup = name
        imgui.end_combo()
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"startup: {proj.startup or 'none'} — the preset a launch and a "
                          "project load bring up; save writes it into the project")


def _project_save_as(panel, name: str) -> None:
    _guard(panel, panel.library.project.save, name)
    invalidate(panel, PROJECT)


# ---- the F1–F8 preset bank: eight pointers to preset files ----

def preset_bank(panel) -> None:
    pr = panel.bank                   # library.Project: bank, active, load/save_slot
    if pr is None:
        return
    r, io = panel.reg, imgui.get_io()
    ui._micro("presets  ·  F1–F8")
    if imgui.is_item_hovered():
        imgui.set_tooltip(
            "The project's eight presets, each one a file in the library: the "
            "whole performance — the look, its routes, LFOs and macros, never "
            "the tempo, the hands or the analyzer. Click or F1–F8 loads; "
            "⇧click or ⇧F1–F8 saves the live state as the slot's preset."
        )
    for k, name in enumerate(pr.bank):
        if k:
            imgui.same_line()
        lit = k == pr.active and name is not None
        pid = f"preset.{'save' if io.key_shift else 'load'}.{k}"
        if ui.lit_chip(f"{k + 1}##preset{k}", lit, ui.FAINT if name is None else ui.TEXT,
                       imgui.ImVec2(SLOT_W, 0)):
            r[pid].fire()
            invalidate(panel, PRESETS)
        if imgui.is_item_hovered():
            imgui.set_tooltip(name if name is not None else
                              f"empty — ⇧F{k + 1} saves the live state here")
        panel._ctx(r[f"preset.load.{k}"])
        panel._learn_frame(r[f"preset.load.{k}"])
    if pr.bank_error:
        imgui.text_colored(ui.WARN, pr.bank_error)


def preset_strip(panel) -> None:
    """The one preset strip: the loaded preset, its dirty dot, save / as…
    — the library's strip over the ``presets`` document kind."""
    lib = panel.library
    if lib is None or lib.reg is None or PRESETS not in lib.kinds:
        return
    ui._micro("preset")
    strip(panel, PRESETS)


# ---- the overview: every group, its preset, its dirty dot ----

def groups(panel) -> list[str]:
    """The groups the overview lists: the performance groups less the
    macros, and the band strip (OVERVIEW_GROUPS), each in the library
    *and* with a persisted param in this registry — a folder alone is not
    a module the panel can save."""
    lib = panel.library
    known = {p.group for p in lib.reg if p.persist and p.group}
    return [g for g in lib.groups() if g in known and g in OVERVIEW_GROUPS]


def overview(panel) -> None:
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    ui._micro("modules")
    for group in groups(panel):
        cur = lib.current(group)
        imgui.text_disabled(f"{group:<8s}")
        imgui.same_line(ui.LABEL_W)
        imgui.text_colored(ui.DIM if cur is None else imgui.ImVec4(0.92, 0.92, 0.92, 1),
                           cur or "—")
        if dirty(panel, group, polled=True):
            imgui.same_line(0, 2)
            imgui.text_colored(ui.RED, "●")
    imgui.push_style_color(imgui.Col_.text, ui.WARN)
    if lib.warning:
        imgui.text_wrapped(lib.warning)
    if lib.error:
        imgui.text_wrapped(lib.error)
    imgui.pop_style_color()
    if lib.status and not lib.error:
        imgui.text_disabled(lib.status)
