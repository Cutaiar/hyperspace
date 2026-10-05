"""Preset strip and the PRESETS page — the library's face on the panel.

Every section of the panel that sits on a registry group the library
knows (library.groups()) carries a strip under its title:

  ◀  name ●  ▶      save   as…   reset

prev / next step through ``library.list(group)``; the name opens the
list (factory presets dim, user ones deletable); the dot is
``is_dirty(group)``; save writes over the current preset and is disabled
only when none is loaded — on a **factory** preset it writes your own
copy of it (``Library.overwrite`` shadows the factory file, never
touches it); as… turns the strip into a name field until Enter (or Esc);
reset lands the group on its default preset — the "meaningful default" —
or its fresh values when it has none.

The PRESETS page speaks plan 14 §3's words — **show** (what the code
calls a ``Project``: a bank of twenty-four presets and what it starts on),
**preset**, **starts on**, **module preset**, **factory** — and reads top
to bottom (plan 14 WP4):

  SHOW        the show's name on a line of its own, never covered; then
              show ▾ (every show, factory ones dim) · save · save as · new
  starts on / home ▾
              the preset the show opens with, and the one Home (the Home
              key, the desk's OVERDUB) loads — written the moment it is
              picked (``Project.write``), a factory show's making your copy
  F1–F8       eight preset buttons two a row, each with its preset's name
              and its F-key, the live one lit: click or F-key loads,
              ⇧click or ⇧F-key saves the live state as it; a right-click
              adds "put preset here…" (any preset into the slot) and
              "clear slot" — the show is written at once, no file is
              deleted
  9–24        sixteen smaller buttons four a row (plan 19 WP1, layout B):
              the bank's far slots, the desk's clip rows 4 and 5, each its
              number and its preset's name; click loads, ⇧click saves, the
              same right-click menu. All twenty-four are on the page at
              once: no paging, no fold, and the page does not scroll with
              "more" open (``tests/test_ui_presets.py``)
  PRESET      the one preset strip — this strip over the ``presets``
              group, a document kind preset.py keeps: the loaded preset,
              its dirty dot, save / as…
  more ▸      folded: a module-preset strip per performance group and the
              band strip's scene (the modules overview)

The library's warning, error and status lines stay under all of it,
outside the fold, so a note like decision 22's rename is seen. The
ROUTING page's head is the preset strip's
save / as… over the same ``presets`` group — the loaded preset, whose
routes, desk and macros that page edits (ui_routing.head); there is no
strip of routing presets since plan 13 WP5.

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
from .library import F_KEYS, HOME_UNSET, PRESETS, LibraryError, slot_key
from .params import PERFORMANCE_GROUPS

LIST_POLL = 1.0      # seconds between re-listings of a group's presets
NAME_MAX = 14        # chars of a preset name the strip shows before eliding
PROJECT = "show"     # the listing / name-field key for the show block
SHOW_W = 96          # the show ▾ menu
BANK_COLS = 2        # preset buttons a row: F1 F2 over F3 F4 …, wide enough for a name
FAR_COLS = 4         # slots 9–24 a row: a desk row of eight pads is two page rows
FAR_GAP = 3          # px between the far slots' rows, so twenty-four fit with "more" open
PUT_ROWS = 12        # rows of "put preset here…" before its list scrolls
# the module overview: every performance group but the macros (a macro's
# meaning is its subscribers, which live in the preset), and the band
# strip's scene, the one session module a project names
OVERVIEW_GROUPS = (*[g for g in PERFORMANCE_GROUPS if g != "macro"], "band")


# ---- state on the panel, created on first use ----

def _state(panel) -> dict:
    st = getattr(panel, "_lib_state", None)
    if st is None:
        st = panel._lib_state = {"lists": {}, "naming": None, "buf": "", "dirty": {}}
    # what the PRESETS page drew last frame: each widget's screen rect by
    # key, and the preset buttons' labels — for the layout tests
    st.setdefault("rects", {})
    st.setdefault("bank_labels", [])
    return st


def _rect(panel, key: str) -> None:
    """Record the last item's screen rect under `key` (_state's `rects`)."""
    a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    _state(panel)["rects"][key] = (a.x, a.y, b.x, b.y)


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
    imgui.begin_disabled(cur is None)
    if ui.chip("save"):
        _guard(panel, lib.overwrite, group)
        invalidate(panel, group)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        imgui.set_tooltip("Write the settings over the current preset"
                          + (" — a factory one: saved as your own copy of it"
                             if factory else ""))
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


# ---- the show: its name, show ▾ · save · save as · new ----

def show_block(panel) -> None:
    """The open show: its name on a line of its own (never covered), then
    show ▾ · save · save as · new."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    proj = lib.project
    imgui.push_id("show")
    if _name_field(panel, PROJECT, lambda n: _project_save_as(panel, n)):
        imgui.pop_id()
        return
    factory = proj.path is None and getattr(proj, "factory", False)
    at = imgui.get_cursor_screen_pos()          # the line the name has to itself
    _state(panel)["rects"]["show.line"] = (at.x, at.y,
                                           at.x + imgui.get_content_region_avail().x, at.y)
    ui._readout(proj.name)
    _rect(panel, "show.name")
    if imgui.is_item_hovered():
        imgui.set_tooltip(str(proj.path) if proj.path else
                          "a factory show — save makes your copy" if factory else
                          "not saved yet — save writes it into the library")
    if proj.is_dirty():
        imgui.same_line(0, 4)
        imgui.text_colored(ui.RED, "●")
        _rect(panel, "show.dot")
        if imgui.is_item_hovered():
            imgui.set_tooltip("the show differs from its file: the session (tempo, hands, "
                              "the analyzer, output) or the bank's presets")
    if factory:
        imgui.same_line(0, 8)
        imgui.text_disabled("factory")
    # show ▾ · save · save as · new
    imgui.set_next_item_width(SHOW_W)
    if imgui.begin_combo("##shows", "show"):
        listing = names(panel, PROJECT)
        for name in listing:
            fact = not proj.path_for(name).is_file()
            imgui.push_style_color(imgui.Col_.text, ui.DIM if fact else ui.TEXT)
            picked, _ = imgui.selectable(name, name == proj.name)
            imgui.pop_style_color()
            if picked:
                _guard(panel, proj.load, name)
        imgui.end_combo()
    _rect(panel, "show.menu")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Open a show: party and house are factory (dim); yours "
                          "are in the library")
    imgui.same_line()
    if ui.chip("save"):
        _guard(panel, proj.save)
        invalidate(panel, PROJECT)
    _rect(panel, "show.save")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Save the show — the session (tempo, hands, the analyzer, "
                          "output), its presets and what it starts on"
                          + (" — a factory show: saved as your own copy" if factory else ""))
    imgui.same_line()
    if ui.chip("save as"):
        _begin_naming(panel, PROJECT, proj.name)
    _rect(panel, "show.save_as")
    imgui.same_line()
    if ui.chip("new"):
        _guard(panel, proj.new)
    _rect(panel, "show.new")
    if imgui.is_item_hovered():
        imgui.set_tooltip("A new show: fresh state, the party show's presets")
    imgui.pop_id()


def project_row(panel) -> None:
    """The show block and what it starts on — the page's top (kept under
    its old name for callers from before plan 14 WP4)."""
    show_block(panel)
    starts_on(panel)


# ---- starts on ▾ ----

def starts_on(panel) -> None:
    """starts on / home ▾ — the preset the show opens with (D11) and the
    one Home goes back to (plan 15 WP2: `Project.home`), labelled, and
    written into the show the moment it is picked."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    proj = lib.project
    imgui.push_id("starts_on")
    ui._micro("starts on / home")
    _rect(panel, "starts_on.label")
    imgui.same_line()
    imgui.set_next_item_width(-1)
    if imgui.begin_combo("##starts_on", proj.startup or "— none"):
        choice: list = []
        picked, _ = imgui.selectable("— none", proj.startup is None)
        if picked:
            choice.append(None)
        for name in names(panel, PRESETS):
            picked, _ = imgui.selectable(f"{name}##starts", name == proj.startup)
            if picked:
                choice.append(name)
        imgui.end_combo()
        if choice:
            set_starts_on(panel, choice[0])
    _rect(panel, "starts_on")
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"starts on: {proj.startup or 'none'} — the preset a launch and "
                          "opening the show bring up; saved as soon as you pick it. "
                          "Home (fn ←) or OVERDUB, B11 on the desk, loads it")
    imgui.pop_id()


def set_starts_on(panel, name: str | None) -> None:
    """Pick what the show starts on and write it now (a factory show's
    write makes your copy); the show is then the one a launch opens."""
    lib = panel.library
    proj = lib.project
    proj.startup = name
    if name and lib.warning == HOME_UNSET:        # home's "pick one": it has been picked
        lib.warning = ""
    if _guard(panel, proj.write) is not None:
        lib.remember(proj.stem)
        lib.say(f"show: {proj.name} starts on {name or 'nothing'}")
    invalidate(panel, PROJECT)


def _project_save_as(panel, name: str) -> None:
    _guard(panel, panel.library.project.save, name)
    invalidate(panel, PROJECT)


# ---- the bank's buttons: F1–F8, then slots 9–24 — pointers to preset files ----

def _fit(text: str, width: float) -> str:
    """`text`, elided with … until it fits `width` pixels."""
    if imgui.calc_text_size(text).x <= width:
        return text
    while len(text) > 1 and imgui.calc_text_size(text + "…").x > width:
        text = text[:-1]
    return text.rstrip() + "…"


def preset_bank(panel) -> None:
    """The bank's buttons (plan 19 WP1, layout B): the F-keys' eight two a
    row (F1 F2 over F3 F4 …), each its preset's name and its F-key, then
    the far slots four a row, each its number and name — the live one lit.
    Click or F-key loads; ⇧click or ⇧F-key saves the live state as the
    slot's preset. A far slot has no trigger of its own (plan 19 fork 1):
    its click calls the bank, and its menu hangs off `preset.select`."""
    pr = panel.bank                   # library.Project: bank, active, load/save_slot
    if pr is None:
        return
    r, io, st = panel.reg, imgui.get_io(), _state(panel)
    ui._micro("presets  ·  F1–F8  ·  ⇧ saves  ·  9–24 on the desk")
    if imgui.is_item_hovered():
        imgui.set_tooltip(
            "The show's twenty-four presets, each one a file in the library: the "
            "whole performance — the look, its routes, LFOs and macros, never "
            "the tempo, the hands or the analyzer. Click or F1–F8 loads; "
            "⇧click or ⇧F1–F8 saves the live state as the slot's preset. "
            "Slots 9–24 are the desk's clip rows 4 and 5."
        )
    style = imgui.get_style()
    sp, avail = style.item_spacing.x, imgui.get_content_region_avail().x
    w_key = (avail - (BANK_COLS - 1) * sp) / BANK_COLS
    w_far = (avail - (FAR_COLS - 1) * sp) / FAR_COLS
    pad = ui.CHIP_PAD.x
    labels: list[str] = []
    white = imgui.ImVec4(1, 1, 1, 1)
    for k, name in enumerate(pr.bank):
        far = k >= F_KEYS
        if (k - F_KEYS) % FAR_COLS if far else k % BANK_COLS:
            imgui.same_line()
        elif k > F_KEYS:
            # the far rows sit FAR_GAP apart: the row is moved up, with no
            # style pushed, so a slot's menu and hover keep the panel's spacing
            imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() - (style.item_spacing.y - FAR_GAP))
        lit = k == pr.active and name is not None
        key = str(k + 1) if far else slot_key(k)
        gap = " " if far else "  "
        w = w_far if far else w_key
        room = w - 2 * pad - imgui.calc_text_size(key + gap).x
        shown = _fit(name, room) if name is not None else "—"
        labels.append(f"{key}{gap}{shown}")
        if ui.lit_chip(f"##preset{k}", lit, None, imgui.ImVec2(w, 0)):
            if far:
                _guard(panel, pr.save_slot if io.key_shift else pr.load_slot, k)
            else:
                r[f"preset.{'save' if io.key_shift else 'load'}.{k}"].fire()
            invalidate(panel, PRESETS)
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        st["rects"][f"preset.{k}"] = (a.x, a.y, b.x, b.y)
        hov = imgui.is_item_hovered()
        # the key hint quiet, the name bright — drawn over the pill
        dl = imgui.get_window_draw_list()
        y = a.y + (b.y - a.y - imgui.get_text_line_height()) / 2
        dl.add_text(imgui.ImVec2(a.x + pad, y), ui.u32(white if lit else ui.FAINT), key)
        dl.add_text(imgui.ImVec2(a.x + pad + imgui.calc_text_size(key + gap).x, y),
                    ui.u32(white if lit else ui.FAINT if name is None else ui.TEXT), shown)
        if hov:
            imgui.set_tooltip(slot_tip(k, name))
        if far:
            # the slot menu under the select param's own items, a popup per
            # slot (as the rail's pills do for `ui.page`)
            panel._ctx(r["preset.select"], f".{k}", extra=lambda k=k: _slot_menu(panel, k))
        else:
            panel._ctx(r[f"preset.load.{k}"], extra=lambda k=k: _slot_menu(panel, k))
            panel._learn_frame(r[f"preset.load.{k}"])
    st["bank_labels"] = labels
    if pr.bank_error:
        imgui.text_colored(ui.WARN, pr.bank_error)


def slot_tip(k: int, name: str | None) -> str:
    """A bank button's hover: what the slot holds and how to reach it — an
    F-key for the first eight, a pad of the desk's clip rows 4 and 5 after."""
    key = slot_key(k)
    if k < F_KEYS:
        return (f"{key}: {name} — click loads, ⇧click saves the live state as it"
                if name is not None else f"{key}: empty — ⇧{key} saves the live state here")
    row, col = divmod(k - F_KEYS, 8)
    if name is not None:
        return (f"{key}: {name} — the desk's row {4 + row}, pad {col + 1}. Click loads, "
                "⇧click saves the live state as it")
    return (f"{key}: empty — right-click to put a preset here; a hold on the clip-stop "
            "row fills the next empty slot")


def _slot_menu(panel, k: int) -> None:
    """A bank slot's own items in its right-click menu (plan 15 WP4):
    **put preset here…**, a submenu of every preset in a child at most
    PUT_ROWS rows tall, and **clear slot**, disabled on an empty slot.
    Each writes the show at once (`Project.put_slot` / `clear_slot`) and
    deletes no file. What was drawn is recorded in `_state`'s `slot_menu`
    for the tests: the slot, each item's label and whether it is enabled,
    the names listed, and screen rects (the two items, the list's child,
    each name's row)."""
    pr, st = panel.bank, _state(panel)
    name = pr.bank[k]
    imgui.separator()
    rects: dict[str, tuple] = {}
    drawn = st["slot_menu"] = {"slot": k, "names": [], "rects": rects,
                               "items": [("put preset here…", True),
                                         ("clear slot", name is not None)]}

    def rect(key: str) -> None:
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        rects[key] = (a.x, a.y, b.x, b.y)

    at = imgui.get_cursor_screen_pos()
    rects["put"] = (at.x, at.y, at.x + imgui.get_content_region_avail().x,
                    at.y + imgui.get_text_line_height())
    if imgui.begin_menu("put preset here…"):
        listing = names(panel, PRESETS)
        drawn["names"] = list(listing)
        style = imgui.get_style()
        wide = max([imgui.calc_text_size(n).x for n in listing] or [0.0])
        size = imgui.ImVec2(wide + style.scrollbar_size + 2 * style.item_spacing.x,
                            imgui.get_text_line_height_with_spacing()
                            * max(1, min(len(listing), PUT_ROWS)))
        if imgui.begin_child("##put", size):
            if not listing:
                imgui.text_disabled("no presets")
            for n in listing:
                picked, _ = imgui.selectable(f"{n}##put", n == name)
                rect(f"name.{n}")
                if picked:
                    _guard(panel, pr.put_slot, k, n)
                    invalidate(panel, PROJECT)
                    imgui.close_current_popup()
        imgui.end_child()
        rect("list")
        imgui.end_menu()
    if imgui.menu_item("clear slot", "", False, name is not None)[0]:
        _guard(panel, pr.clear_slot, k)
        invalidate(panel, PROJECT)
    rect("clear")


def preset_strip(panel) -> None:
    """The one preset strip: the loaded preset, its dirty dot, save / as…
    — the library's strip over the ``presets`` document kind."""
    lib = panel.library
    if lib is None or lib.reg is None or PRESETS not in lib.kinds:
        return
    ui._micro("preset")
    strip(panel, PRESETS)


# ---- more: every module preset, its strip ----

def groups(panel) -> list[str]:
    """The groups the overview lists: the performance groups less the
    macros, and the band strip (OVERVIEW_GROUPS), each in the library
    *and* with a persisted param in this registry — a folder alone is not
    a module the panel can save."""
    lib = panel.library
    known = {p.group for p in lib.reg if p.persist and p.group}
    return [g for g in lib.groups() if g in known and g in OVERVIEW_GROUPS]


def more(panel) -> None:
    """The fold: a module-preset strip per group (its name, its dot, save
    / as… / reset) — the modules overview. Folded unless opened."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    if not imgui.collapsing_header("more  ·  module presets##presets.more"):
        return
    for group in groups(panel):
        imgui.text_disabled(f"{group:<8s}")
        imgui.same_line(ui.LABEL_W)
        strip(panel, group)


def overview(panel) -> None:
    """The fold, then the library's warning, error and status lines — never
    folded, so a note is always seen."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    more(panel)
    notes(panel)


def notes(panel) -> None:
    lib = panel.library
    imgui.push_style_color(imgui.Col_.text, ui.WARN)
    if lib.warning:
        imgui.text_wrapped(lib.warning)
    if lib.error:
        imgui.text_wrapped(lib.error)
    imgui.pop_style_color()
    if lib.status and not lib.error:
        imgui.text_disabled(lib.status)
