"""Preset strips and the PRESETS page — the library's face on the panel.

Every section of the panel that sits on a registry group the library
knows (library.groups()) carries a strip under its title:

  ◀  name ●  ▶      save   as…   reset

prev / next step through ``library.list(group)``; on a module group the
name opens the group's list (× on each, to the trash); the dot is
``is_dirty(group)``, a 12 px red disc (``ui.dirty_dot``, plan 19 WP5),
and while it shows the save chip is lit solid red; save writes over the
current loadable patch (its old text kept in the trash) and is disabled only when
none is loaded; as… turns the strip into a name field until Enter (or
Esc); reset (module strips only) lands the group on its default loadable patch
or its fresh values.

The PRESETS page (2026-10-28: one tier — nothing is factory, nothing is
hidden, every loadable patch is yours to load, rename and delete) reads top to
bottom (``page``):

  PRESET      the preset strip over the ``presets`` document kind
              (loadable.py): ◀ loaded patch ● ▶ · new · save · as… — the
              name is a readout, the list is the page
  the list    every loadable patch by name, the loaded one selected, filling the
              page: a click loads, `rename` turns the row into a name
              field, × sends the file to the trash. Plan 48 stage 2: a
              tree — the top-level loadable patches, then a folding header per
              folder (the fold this Mac's, in ui.json), nested folders
              nested; a row's right-click is "move to ▸", a row drags
              onto a header; a header's right-click makes a folder
              inside, renames it, removes it (empty only); "new folder"
              at the foot makes one at the top
  trash (n) ▸ at the list's foot, only while the trash holds something:
              its own popup — restore per file, "empty trash…" asked twice
              in place
  patches ▸   folded: every patch (plan 40 T3), rename and × — a patch is
              spawned on GRAPH, never loaded here
  SHOW        one line that says what a show is — the desk's pads, the
              meta controller and the meta controller's wires — then its name ●, open ▾ (your
              shows), save, as…, new. The pads are set on the desk (hold
              a pad, or SAVE + a pad); nothing on the page edits them

The library's warning, error and status lines stay under all of it, so a
note like a rename's is seen. The ROUTING page's head is the loadable patch
strip's save / as… over the same ``presets`` group (ui_routing.head).

These are functions over the Panel rather than widget classes: the
state they need (the name field, the cached listings) lives on the
panel, and ui.py's imports rebind to fresh code on a hot reload. A
listing stats every file in the group's folder, so it is refreshed on
a poll cadence (LIST_POLL), never per frame; dirty state is a snapshot
compare and is cheap enough to ask each frame for the page on screen.
"""

from __future__ import annotations

import time

from imgui_bundle import imgui

from . import loadable, ui, undo
from .groupwords import group_word
from .library import (
    LOADABLE,
    PATCHES,
    RETIRED_MODULES,
    LibraryError,
)

LIST_POLL = 1.0      # seconds between re-listings of a group's loadable patches
NAME_MAX = 14        # chars of a loadable patch name the strip shows before eliding
PROJECT = "show"     # the listing / name-field key for the show line
SHOW_W = 96          # the open ▾ menu
# plan 19 WP4: a module strip's list and the trash's view
LIST_ROWS = 12       # rows of a module strip's list, and of the trash, before each scrolls
EMPTY_S = 4.0        # how long "empty trash…" stays armed for its second click
MIN_ROWS = 3         # the page's list is never shorter than this many rows
TRASH_KEY = "\0trash"     # the listings cache: the trash
# plan 48 stage 2: the tree
FOLDERS_KEY = "\0folders" # the listings cache: the loadable patches' folders
LOADABLE_DRAG = "PRESET"    # a row's drag payload (the name kept in `_state`'s preset_drag)
OLD_UI_KEY = "presets"    # (read once: this Mac's folds from before the one migration)
UI_KEY = "loadable"       # <machine>/ui.json: {"loadable": {"folded": [folder, …]}}
FOLDER_TIP = ("A folder of presets: click to fold or unfold (kept on this Mac). "
              "Drag a preset onto it to move it in. Right-click: a new folder inside, "
              "rename, remove (an empty folder only)")
# what a show is, in one line under the SHOW label and in its hover
SHOW_LINE = "show: pads, meta controller"
SHOW_TIP = ("A show is the room the presets play in: which preset each of the desk's "
            "twenty-four pads loads, off air (set on the desk — hold a pad, or SAVE + a pad), the "
            "meta controller (tempo, hands, the analyzer, the outputs) and the analyzer's scene. "
            "A preset is the look, with the bus cables it cuts on GRAPH; the show is everything "
            "around it. Open another, save this one, or start a new one here.")


def trash_tag(item) -> str:
    """A trash row's dim first column: its group, and for a file in the
    library's old trash (plan 48 row 586) ``· library`` — so a row says in
    itself that "empty" leaves it and a restore is a copy."""
    word = group_word(item.group)
    return f"{word} · library" if item.old else word


# ---- state on the panel, created on first use ----

def _state(panel) -> dict:
    st = getattr(panel, "_lib_state", None)
    if st is None:
        st = panel._lib_state = {"lists": {}, "naming": None, "buf": "", "dirty": {}}
    # what the PRESETS page drew last frame: each widget's screen rect by
    # key, and the list's rows — for the layout tests
    st.setdefault("rects", {})
    st.setdefault("save", {})          # group → (the save chip's words, lit), last drawn
    return st


def _rect(panel, key: str) -> None:
    """Record the last item's screen rect under `key` (_state's `rects`)."""
    a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    _state(panel)["rects"][key] = (a.x, a.y, b.x, b.y)


def names(panel, key: str) -> list[str]:
    """``library.list(group)`` (or the show list), refreshed on the poll
    cadence."""
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
    """Our own write: the next frame re-lists rather than waiting out the
    poll — the listing and the trash."""
    lists = _state(panel)["lists"]
    for slot in (key, TRASH_KEY, FOLDERS_KEY):
        lists.pop(slot, None)


def trashed(panel) -> list:
    """``library.trash()``, refreshed on the poll cadence (it lists a folder)."""
    st, lib = _state(panel), panel.library
    now = imgui.get_time()
    hit = st["lists"].get(TRASH_KEY)
    if hit is None or now - hit[0] >= LIST_POLL:
        try:
            listing = lib.trash()
        except OSError as e:
            lib.error = f"library: {e}"
            listing = hit[1] if hit else []
        st["lists"][TRASH_KEY] = hit = (now, listing)
    return hit[1]


def dirty(panel, group: str, *, polled: bool = False) -> bool:
    """``is_dirty(group)`` — live, or on the poll cadence for the section headers' dots."""
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


NAME_MIN = 48.0     # px: the narrowest the strip's name button is squeezed to


def strip_name_w(avail: float, chips: tuple[str, ...], dirty_: bool,
                 extra: float = 0.0) -> float:
    """The name button's width on a strip `avail` px wide (plan 49): `name_w`
    where it fits — every page — else what is left beside the arrows, the
    dot, `extra` (the presets strip's "N devices missing" chip after ▶,
    `ui_graph.wants_chip_w`) and the right-hand chips (GRAPH's side pane, a
    few hundred px), never under `NAME_MIN`."""
    return max(NAME_MIN, min(name_w(), avail - _strip_beside(chips, dirty_, extra)))


def _strip_beside(chips: tuple[str, ...], dirty_: bool, extra: float = 0.0) -> float:
    """What a strip's row holds besides its name button."""
    return (2 * imgui.get_frame_height() + 4 + ui.chip_w(*chips) + imgui.get_style().item_spacing.x
            + (2 * ui.DOT_R + 2 if dirty_ else 0.0) + extra)


def _guard(panel, fn, *args):
    """Run a library call; a bad file or a full disk shows, never raises."""
    try:
        return fn(*args)
    except (LibraryError, OSError) as e:
        panel.library.error = f"library: {e}"
        return None


def _said(panel, fn, *args):
    """Run a library call from the list; a refusal goes on the library's
    warning line, which the footer shows (`Library.say`)."""
    lib = panel.library
    try:
        return fn(*args)
    except (LibraryError, OSError) as e:
        lib.say(warning=f"library: {e}")
        return None


# ---- the name field: the strip while a save-as is being typed ----

def _name_field(panel, key: str, commit, hint: str = "preset name") -> bool:
    """Draw the inline name field for `key`; returns True while it is open."""
    st = _state(panel)
    if st["naming"] != key:
        return False
    imgui.set_next_item_width(-(ui.chip_w("ok", "×") + imgui.get_style().item_spacing.x))
    if st.pop("focus", False):          # the field takes the keyboard once, on open
        imgui.set_keyboard_focus_here()
    entered, st["buf"] = imgui.input_text_with_hint(
        f"##name.{key}", hint, st["buf"],
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
            undo.by_hand(True)          # the field's own report: row 757
            commit(name)
            st["naming"] = None
    return True


def _begin_naming(panel, key: str, seed: str) -> None:
    st = _state(panel)
    st["naming"], st["buf"], st["focus"] = key, seed, True


# ---- the strip ----

def save_label(lib, group: str) -> str:
    """The save chip's words — "save" (one tier: every save writes the
    loaded patch's own file; kept as a function for ROUTING's head)."""
    return "save"


def save_tip(lib, group: str) -> str:
    """The save chip's hover, in the label's terms."""
    cur = lib.current(group)
    if cur is None:
        return "No preset loaded: as… saves the settings as a new one"
    return f"Write the settings over {cur} (the old file goes to the trash)"


def save_chip(panel, group: str, label: str, lit: bool, *, key: str | None = None) -> bool:
    """The save chip: solid red while there is something to save (the
    panel's lit key, readable from the floor), the quiet chip when clean.
    Disabled while nothing is loaded. Returns whether it was clicked; its
    rect (``<key>.save``) and its words and whether it was lit
    (``save[<key>]``) are kept in `_state` for the tests — `key` is
    ``strip.<group>`` for a strip, ``head`` for ROUTING's head."""
    lib = panel.library
    cur = lib.current(group)
    key = key or f"strip.{group}"
    imgui.begin_disabled(cur is None)
    hit = ui.lit_chip(f"{label}##save", True) if lit and cur is not None \
        else ui.chip(f"{label}##save")
    imgui.end_disabled()
    _rect(panel, f"{key}.save")
    _state(panel)["save"][key] = (label, bool(lit and cur is not None))
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        ui.tooltip(save_tip(lib, group))
    return hit


def _on_deck(meta) -> str:
    """ "· deck 2 · off air", for a hover; "" with no meta controller."""
    return f"  ·  {meta.words(meta.panel)}" if meta is not None else ""


def strip(panel, group: str) -> None:
    """◀ name ● ▶ · save · as… · reset — for one registry group. On the
    loadable patches' strip (a document kind) there is no reset (`Library.reset`
    on a kind loads a loadable patch called "default", and none ships) and `new`
    starts a blank loadable patch (plan 35 T7); its name is a readout — the
    PRESETS page's list is under it. A module strip's name opens the
    group's list."""
    lib = panel.library
    if lib is None or lib.reg is None or group in RETIRED_MODULES:
        return                  # (plan 40 T5: a retired module group has no strip)
    # the deck this name is on, for the hover (`page` says it over the strip)
    meta = getattr(panel, "meta", None) if group == LOADABLE else None
    imgui.push_id(f"strip.{group}")
    if _name_field(panel, group, lambda n: _save_as(panel, group, n)):
        imgui.pop_id()
        return
    st = _state(panel)
    cur = lib.current(group)
    listing = names(panel, group)
    is_dirty = dirty(panel, group)
    kind = group in lib.kinds
    loaded_patch = getattr(lib, "loaded_patch", None) if group == LOADABLE else None
    word = "save"
    chips = (word, "as…") if kind else (word, "as…", "reset")
    if loaded_patch is not None:
        chips = ("new", *chips)
    wants, avail = 0.0, imgui.get_content_region_avail().x
    if group == LOADABLE:
        from . import ui_graph  # (late, as below)
        wants = ui_graph.wants_chip_w(panel)
    # "N devices missing" beside ▶ where it fits by a squeezed name, else
    # on a row of its own under the strip (a narrow pane, plan 49)
    wants_beside = wants == 0.0 or strip_name_w(avail, chips, is_dirty) - wants >= NAME_MIN
    extra = wants if wants_beside else 0.0
    width = strip_name_w(avail, chips, is_dirty, extra)
    # plan 49 stage 3: narrower still (a pane with its scrollbars), the chips
    # go on a row of their own under ◀ name ▶ and the name has that row's room
    roomy = avail - _strip_beside(chips, is_dirty, extra) >= NAME_MIN
    if not roomy:
        width = strip_name_w(avail, (), is_dirty)

    # ◀ name ▶ — the arrows step by name order; a module strip's name opens its list
    imgui.begin_disabled(not listing)
    if imgui.arrow_button("prev", imgui.Dir.left):
        _guard(panel, lib.prev, group)
    imgui.same_line(0, 2)
    label = _elide(cur) if cur else "—"
    if width < name_w():                # a narrow strip: the name cut to its button
        label = ui.fit_text(label, width - 2 * imgui.get_style().frame_padding.x)
    imgui.push_style_color(imgui.Col_.button, imgui.ImVec4(0, 0, 0, 0))
    imgui.push_style_color(imgui.Col_.text, ui.DIM if cur is None else
                           imgui.ImVec4(0.92, 0.92, 0.92, 1))
    if imgui.button(f"{label}##name", imgui.ImVec2(width, 0)) and group != LOADABLE:
        imgui.open_popup("list")
    imgui.pop_style_color(2)
    _rect(panel, f"strip.{group}.name")
    if imgui.is_item_hovered():
        if cur is None:
            ui.tooltip(f"no preset loaded{_on_deck(meta)}")
        elif group == LOADABLE:
            ui.tooltip(f"{cur}{_on_deck(meta)}  ·  the loaded preset — the list below "
                       "loads onto this deck")
        else:
            ui.tooltip(f"{cur}  ·  click for the list")
    st["rects"].pop(f"strip.{group}.dot", None)
    if is_dirty:
        imgui.same_line(0, 2)
        st["rects"][f"strip.{group}.dot"] = ui.dirty_dot("edited since the preset loaded — "
                                                   "save writes it")
    imgui.same_line(0, 2)
    if imgui.arrow_button("next", imgui.Dir.right):
        _guard(panel, lib.next, group)
    _rect(panel, f"strip.{group}.next")
    imgui.end_disabled()
    if group == LOADABLE:
        from . import ui_graph  # (late, as `new` below)
        if wants_beside:                # plan 40 T4: the devices the loadable patch waits for
            ui_graph._wants_chip(panel)
    else:
        _list_popup(panel, group, listing, cur)

    # (new ·) save · as… (· reset on a module strip), flush right
    if roomy:
        ui.flush_right(ui.chip_w(*chips))
    if loaded_patch is not None:
        if ui.chip("new##new"):
            from . import ui_graph  # (late: ui_graph imports ui_routing, which imports this)
            # plan 36 T5: its chain laid out where the GRAPH page is looking
            _guard(panel, loaded_patch.new, ui_graph.in_view(panel))
            invalidate(panel, group)
        _rect(panel, f"strip.{group}.new")
        if imgui.is_item_hovered():
            ui.tooltip("A new preset: default values, shape → scene → All outputs — "
                       "a shape on every window")
        imgui.same_line()
    # R17: a loadable patch `new` made and nothing saved names itself — a loadable patch
    # that happens to be called `untitled` is never written over (the flag
    # counts while `untitled` is current: an undo of New hands back the
    # loadable patch before, which saves as it always did)
    unsaved = loaded_patch is not None and cur == loadable.UNTITLED_PATCH and (
        bool(getattr(loaded_patch, "unsaved", False)) or lib.path_of(group, cur) is None)
    if save_chip(panel, group, word, is_dirty):
        if unsaved:
            _begin_naming(panel, group, "")      # unnamed: save acts as as…
        else:
            _guard(panel, lib.overwrite, group)
            invalidate(panel, group)
    imgui.same_line()
    if ui.chip("as…"):
        _begin_naming(panel, group, "" if unsaved else (cur or ""))
    _rect(panel, f"strip.{group}.as")
    if imgui.is_item_hovered():
        ui.tooltip("Save the settings as a new preset")
    if not kind:
        imgui.same_line()
        if ui.chip("reset"):
            _guard(panel, lib.reset, group)
        _rect(panel, f"strip.{group}.reset")
        if imgui.is_item_hovered():
            d = lib.default_name(group)
            ui.tooltip(f"Back to the default preset — {d}" if d
                       else "Back to the values the module started with")
    if not wants_beside:
        from . import ui_graph
        ui_graph._wants_chip(panel, beside=False)
    imgui.pop_id()


def _save_as(panel, group: str, name: str) -> None:
    _guard(panel, panel.library.save_as, group, name)
    invalidate(panel, group)


def _rename(panel, old: str, new: str, group: str = LOADABLE) -> None:
    _said(panel, panel.library.rename, group, old, new)
    invalidate(panel, group)
    invalidate(panel, PROJECT)


def list_row_h() -> float:
    """A row of a preset list: a chip's height (the tallest item in it)
    and the spacing under it."""
    return (imgui.get_text_line_height() + 2 * ui.CHIP_PAD.y
            + imgui.get_style().item_spacing.y)


def _list_row(panel, group: str, name: str, cur: str | None, drawn: dict, rect,
              tree: bool = False) -> None:
    """One row of a preset list: the name (a pick loads it), then its
    chips — `rename` and × on a loadable patch or a patch (plan 40 T3: a patch's
    row has no pick — a patch is spawned on GRAPH, never loaded), × alone
    on a module preset. What was drawn joins `drawn["rows"]` as
    ``(name, chips)``."""
    lib, st = panel.library, _state(panel)
    patch = group == PATCHES
    renamable = group == LOADABLE or patch
    key = f"rename:{group}:{name}" if patch else f"rename:{name}"
    if renamable and st["naming"] == key:          # the row is the name field
        drawn["rows"].append((name, ("field",)))
        _name_field(panel, key, lambda n, old=name: _rename(panel, old, n, group))
        return
    # plan 48 row 588: a loadable patch from a folder reads "party / TRIP", the
    # folder dim — the row's text drawn over a label-less selectable; a
    # top-level name is the selectable's own label, as before
    # (plan 48 stage 2: under its folder's header — `tree` — a row is the
    # leaf alone, the header says the folder)
    folder, leaf = lib.folder_of(group, name)      # the library's one rule
    x = imgui.get_cursor_pos_x()
    imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(0.92, 0.92, 0.92, 1))
    label = (f"{leaf}##{name}##pick" if folder and tree else
             f"##{name}##pick" if folder else f"{name}##pick")
    picked, _ = imgui.selectable(label, name == cur, imgui.SelectableFlags_.allow_overlap)
    rect(f"row.{name}")
    dragged = False
    if group == LOADABLE:
        # plan 48 stage 2: a row drags onto a folder's header, and its
        # right-click offers "move to ▸"
        if imgui.begin_drag_drop_source():
            st["preset_drag"], dragged = name, True
            imgui.set_drag_drop_payload_py_id(LOADABLE_DRAG, 0)
            imgui.text(name)
            imgui.end_drag_drop_source()
        if imgui.begin_popup_context_item(f"menu.{name}"):
            _row_menu(panel, name, folder)
            imgui.end_popup()
    if folder and not tree:
        imgui.same_line(x, 0)
        imgui.text_colored(ui.DIM, f"{folder.replace('/', ' / ')} / ")
        imgui.same_line(0, 0)
        imgui.text(leaf)
    imgui.pop_style_color()
    drawn.setdefault("text", []).append((folder, leaf))
    if picked and not patch and not dragged:
        _guard(panel, lib.load, group, name)
    chips = ("rename", "×") if renamable else ("×",)
    drawn["rows"].append((name, chips))
    ui.flush_right(ui.chip_w(*chips))
    imgui.push_style_color(imgui.Col_.text, ui.DIM)
    for i, chip in enumerate(chips):
        if i:
            imgui.same_line()
        hit = ui.chip(f"{chip}##{chip}.{name}")
        rect(f"{chip}.{name}")
        if imgui.is_item_hovered():
            ui.tooltip("Give it another name: the file, and every show that names it"
                       if chip == "rename" else
                       "To the trash — restore it from there (the list's foot)")
        if not hit:
            continue
        if chip == "rename":
            _begin_naming(panel, key, leaf)      # a rename keeps the folder
        else:
            _guard(panel, lib.delete, group, name)
        invalidate(panel, group)
    imgui.pop_style_color()


def _list_popup(panel, group: str, listing: list[str], cur: str | None) -> None:
    """A module strip's list, the popup its name opens: every loadable patch of the
    group, the loaded one selected, × on each (to the trash). Past
    LIST_ROWS rows it scrolls in its own child. What was drawn is kept in
    `_state`'s ``list`` for the tests."""
    st = _state(panel)
    if not imgui.begin_popup("list"):
        return
    drawn: dict = {"group": group, "rows": [], "foot": [], "rects": {}}
    st["list"] = drawn

    def rect(key: str) -> None:
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        drawn["rects"][key] = (a.x, a.y, b.x, b.y)

    ui._micro(group)
    style = imgui.get_style()
    wide = (max([imgui.calc_text_size(n).x for n in listing] or [0.0])
            + 3 * style.item_spacing.x + ui.chip_w("×"))
    imgui.dummy(imgui.ImVec2(wide + style.scrollbar_size, 0))     # the list's width
    if not listing:
        imgui.text_disabled("no presets — save as… makes one")
    else:
        size = imgui.ImVec2(wide + style.scrollbar_size,
                            list_row_h() * min(len(listing), LIST_ROWS))
        if imgui.begin_child("##rows", size):
            for name in listing:
                _list_row(panel, group, name, cur, drawn, rect)
        imgui.end_child()
        rect("rows")
    imgui.end_popup()


# ---- the PRESETS page ----

def page(panel) -> None:
    """The page, top to bottom (the module docstring): the preset strip,
    the list filling the page, the trash foot, the patches fold, the show
    line, the notes."""
    lib = panel.library
    if lib is None or lib.reg is None or LOADABLE not in lib.kinds:
        return
    ui._micro("preset")
    meta = getattr(panel, "meta", None)
    if meta is not None:    # plan 44 D5e, DQ7: its own room, so no name is cut for it
        imgui.same_line()
        ui._micro(meta.words(meta.panel), ui.RED if meta.panel is not meta.on_air else ui.DIM)
    strip(panel, LOADABLE)
    loadable_list(panel)
    imgui.separator()
    patches_fold(panel)
    imgui.separator()
    show_line(panel)
    notes(panel)


def _reserve() -> float:
    """The height the page keeps under the list: the trash foot, two
    separators, the patches header, the show line's three rows and two
    lines of notes."""
    style = imgui.get_style()
    return (list_row_h()
            + 2 * (style.item_spacing.y + 1)
            + imgui.get_frame_height_with_spacing()
            + 3 * imgui.get_frame_height_with_spacing()
            + 2 * imgui.get_text_line_height_with_spacing())


def loadable_list(panel) -> None:
    """Every loadable patch, as a list that fills the page (never shorter than
    MIN_ROWS rows, scrolling past the room it has): the loaded one
    selected, a click loads, `rename` and × on each row (`_list_row`).
    Plan 48 stage 2: a tree — the top-level loadable patches first, then a folding
    header per folder, alphabetically, a folder's loadable patches (in the list's
    order) then its own folders under it (`_folder`); a fold is this
    Mac's (`folded`). Then the foot line: the trash's while it holds
    something, and **new folder** (at the top) flush right. What was drawn
    is kept in `_state`'s ``page`` for the tests: each row's name and
    chips, each header (``folders``: (folder, open)), the foot's lines,
    screen rects."""
    lib, st = panel.library, _state(panel)
    cur = lib.current(LOADABLE)
    rows = names(panel, LOADABLE)
    bin_ = trashed(panel)
    drawn: dict = {"group": LOADABLE, "rows": [], "foot": [], "rects": {}, "folders": []}
    st["page"] = drawn

    def rect(key: str) -> None:
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        drawn["rects"][key] = (a.x, a.y, b.x, b.y)

    flush_folds(panel)                  # a fold clicked WRITE_AFTER_S ago, kept
    tree = _tree(lib, rows, folder_list(panel))
    room = imgui.get_content_region_avail().y - _reserve()
    height = max(room, list_row_h() * MIN_ROWS)
    if imgui.begin_child("##presets.rows", imgui.ImVec2(0, height)):
        if not tree["count"].get(""):  # no loadable patch anywhere, folders or none
            imgui.text_disabled("no presets — new, then save as… makes one")
        _folder_body(panel, "", tree, cur, drawn, rect)
    imgui.end_child()
    rect("rows")
    if _name_field(panel, "newfolder:", lambda n: _make_folder(panel, "", n), "folder name"):
        return
    chip = "new folder"
    if bin_:
        line = f"trash ({len(bin_)}) ▸"
        width = imgui.get_content_region_avail().x - ui.chip_w(chip) - imgui.get_style().item_spacing.x
        hit, _ = imgui.selectable(f"{line}##trash", False, 0, imgui.ImVec2(max(width, 1.0), 0))
        drawn["foot"].append(line)
        rect("trash")
        if hit:
            st["empty_armed"] = None
            imgui.open_popup("trash")
        if imgui.is_item_hovered():
            ui.tooltip("What × and rename sent to the trash, and every older version a "
                       "save replaced: restore puts one back")
        _trash_popup(panel, bin_)
        imgui.same_line()
    imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + imgui.get_content_region_avail().x
                           - ui.chip_w(chip))
    imgui.push_style_color(imgui.Col_.text, ui.DIM)
    if ui.chip(f"{chip}##newfolder"):
        _begin_naming(panel, "newfolder:", "")
    imgui.pop_style_color()
    rect("new_folder")
    if imgui.is_item_hovered():
        ui.tooltip("A new folder at the top of the presets (a folder's right-click makes "
                   "one inside it). Drag a preset onto a folder, or right-click it: "
                   "move to ▸")


# ---- the tree (plan 48 stage 2) ----

def folder_list(panel) -> list[str]:
    """``library.folders()``, refreshed on the poll cadence."""
    st, lib = _state(panel), panel.library
    now = imgui.get_time()
    hit = st["lists"].get(FOLDERS_KEY)
    if hit is None or now - hit[0] >= LIST_POLL:
        try:
            listing = lib.folders()
        except (LibraryError, OSError) as e:
            lib.error = f"library: {e}"
            listing = hit[1] if hit else []
        st["lists"][FOLDERS_KEY] = hit = (now, listing)
    return hit[1]


def _tree(lib, rows: list[str], folders: list[str]) -> dict:
    """The list as a tree: ``rows`` — folder → its loadable patches, in the list's
    order (``""`` the top); ``kids`` — folder → its folders, sorted case
    folded; ``count`` — folder → loadable patches in it, every folder down. Every
    folder on disk is in it, empty ones too, and every folder a name
    sits in (with its parents)."""
    by: dict[str, list[str]] = {}
    every: set[str] = set(folders)
    for name in rows:
        folder = lib.folder_of(LOADABLE, name)[0]
        by.setdefault(folder, []).append(name)
        every.add(folder)
    for f in list(every):
        while f:
            every.add(f)
            f = f.rpartition("/")[0]
    every.discard("")
    kids: dict[str, list[str]] = {}
    for f in every:
        kids.setdefault(f.rpartition("/")[0], []).append(f)
    for v in kids.values():
        v.sort(key=str.lower)
    count: dict[str, int] = {}

    def total(f: str) -> int:
        count[f] = len(by.get(f, [])) + sum(total(k) for k in kids.get(f, []))
        return count[f]
    total("")
    return {"rows": by, "kids": kids, "count": count}


def _folder_body(panel, folder: str, tree: dict, cur, drawn: dict, rect) -> None:
    """A folder's inside (the top's too): a new folder's name field while
    one is being made here, its loadable patches, then its folders."""
    if folder:
        _name_field(panel, f"newfolder:{folder}",
                    lambda n: _make_folder(panel, folder, n), "folder name")
    for name in tree["rows"].get(folder, []):
        _list_row(panel, LOADABLE, name, cur, drawn, rect, tree=True)
    for kid in tree["kids"].get(folder, []):
        _folder(panel, kid, tree, cur, drawn, rect)


def _folder(panel, folder: str, tree: dict, cur, drawn: dict, rect) -> None:
    """One folder's header, folding (this Mac's, `folded`): its name, how
    many loadable patches it holds, and — folded — the loaded patch's name when it
    is inside; a drop target for a dragged row; its right-click menu
    (`_folder_menu`). Open, its body under it, indented."""
    st = _state(panel)
    leaf = folder.rpartition("/")[2]
    if _name_field(panel, f"folder:{folder}",
                   lambda n: _rename_folder(panel, folder, n), "folder name"):
        drawn["folders"].append((folder, None))
        return
    shut = folder in folded(panel)
    n = tree["count"].get(folder, 0)
    label = f"{leaf}  ·  {n}"
    where = panel.library.folder_of(LOADABLE, cur)[0] if cur else None
    if shut and where is not None and (where == folder or where.startswith(folder + "/")):
        label += f"  ·  {cur.rpartition('/')[2]}"
    imgui.set_next_item_open(not shut, imgui.Cond_.always)
    opened = imgui.tree_node_ex(f"{label}###folder.{folder}",
                                imgui.TreeNodeFlags_.framed
                                | imgui.TreeNodeFlags_.span_avail_width)
    rect(f"folder.{folder}")
    if imgui.is_item_toggled_open():
        set_folded(panel, folder, not opened)
    drawn["folders"].append((folder, opened))
    if imgui.is_item_hovered():
        ui.tooltip(FOLDER_TIP)
    if imgui.begin_drag_drop_target():
        if imgui.accept_drag_drop_payload_py_id(LOADABLE_DRAG) is not None:
            name = st.pop("preset_drag", None)
            if name:
                _move(panel, name, folder)
        imgui.end_drag_drop_target()
    if imgui.begin_popup_context_item(f"folder.menu.{folder}"):
        _folder_menu(panel, folder)
        imgui.end_popup()
    if opened:
        _folder_body(panel, folder, tree, cur, drawn, rect)
        imgui.tree_pop()


def _menu_rect(panel, key: str) -> None:
    a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    _state(panel).setdefault("menu", {})[key] = (a.x, a.y, b.x, b.y)


def _row_menu(panel, name: str, folder: str) -> None:
    """A row's right-click: **move to ▸** — the top level and every
    folder, less the one it is in. What was drawn is kept in `_state`'s
    ``menu`` (item → rect) for the tests."""
    st = _state(panel)
    st["menu"] = {}
    st["menu_for"] = name
    ui._micro(name)
    opened = imgui.begin_menu("move to")
    _menu_rect(panel, "move to")
    if not opened:
        return
    for f in ["", *folder_list(panel)]:
        if f == folder:
            continue
        label = "top level" if not f else f.replace("/", " / ")
        if imgui.menu_item_simple(f"{label}##to.{f}"):
            _move(panel, name, f)
        _menu_rect(panel, f"to.{f}")
    imgui.end_menu()


def _folder_menu(panel, folder: str) -> None:
    """A folder's right-click: a new folder inside, rename, remove (an
    empty folder only — the item is off otherwise, its hover naming what
    is in the way: `Library.held`, the same test the remove makes, hidden
    files and all; review of #349). Drawn only while the menu is open,
    so the folder is listed only then."""
    st = _state(panel)
    st["menu"] = {}
    st["menu_for"] = folder
    held = _guard(panel, panel.library.held, folder) or []
    empty = not held
    st["menu_held"] = held
    if imgui.menu_item_simple("new folder inside…"):
        set_folded(panel, folder, False)
        _begin_naming(panel, f"newfolder:{folder}", "")
    _menu_rect(panel, "new")
    if imgui.menu_item_simple("rename folder…"):
        _begin_naming(panel, f"folder:{folder}", folder.rpartition("/")[2])
    _menu_rect(panel, "rename")
    if imgui.menu_item_simple("remove folder", "", False, empty):
        _said(panel, panel.library.remove_folder, folder)
        set_folded(panel, folder, False)
        _changed(panel)
    _menu_rect(panel, "remove")
    if not empty and imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        ui.tooltip("Only an empty folder is removed — it holds "
                   + ", ".join(held) + ": move or trash them first")


def _changed(panel) -> None:
    invalidate(panel, LOADABLE)
    invalidate(panel, PROJECT)


def _move(panel, name: str, folder: str) -> None:
    _said(panel, panel.library.move, name, folder)
    _changed(panel)


def _make_folder(panel, parent: str, name: str) -> None:
    _said(panel, panel.library.make_folder, parent, name)
    _changed(panel)


def _rename_folder(panel, folder: str, name: str) -> None:
    new = _said(panel, panel.library.rename_folder, folder, name)
    if new and new != folder:
        shut = folded(panel)
        moved = {f for f in shut if f == folder or f.startswith(folder + "/")}
        for f in moved:
            shut.discard(f)
            shut.add(new + f[len(folder):])
        if moved:
            _folds_dirty(panel, clicks={**{f: False for f in moved},
                                        **{new + f[len(folder):]: True for f in moved}})
    _changed(panel)


# ---- the folds: this Mac's, in ui.json beside the pane's (ui_pane) ----

def _machine(panel):
    lib = panel.library
    try:
        return lib._machine()
    except (AttributeError, OSError):
        return None


def folded(panel) -> set[str]:
    """The folders folded on this Mac — ``presets.folded`` in
    ``<machine>/ui.json`` (`ui_pane.read_doc`). Read once the machine is
    known, and again if it changes (review of #349, as `ui_pane.opened`:
    a draw before the library attached must not stand for the file), any
    fold clicked before that laid over what the file says
    (``fold_clicks``), so the next write keeps both. A folder not named
    there is open."""
    st = _state(panel)
    machine = _machine(panel)
    if "folded" not in st or (machine is not None and st.get("folded_from") != machine):
        held = None
        if machine is not None:
            from . import ui_pane  # (late: ui_pane imports this module)
            doc = ui_pane.read_doc(machine)
            sec = doc.get(UI_KEY, doc.get(OLD_UI_KEY))
            held = sec.get("folded") if isinstance(sec, dict) else None
        got = {f for f in held if isinstance(f, str)} if isinstance(held, list) else set()
        for f, shut in (st.get("fold_clicks") or {}).items():
            (got.add if shut else got.discard)(f)
        st["folded"], st["folded_from"] = got, machine
    return st["folded"]


def set_folded(panel, folder: str, shut: bool, now: float | None = None) -> None:
    """Fold or unfold `folder`; kept in this Mac's ui.json `WRITE_AFTER_S`
    after the last change (`flush_folds`), as the pane's folds are."""
    s = folded(panel)
    if (folder in s) == shut:
        return
    (s.add if shut else s.discard)(folder)
    _folds_dirty(panel, now, {folder: shut})


def _folds_dirty(panel, now: float | None = None, clicks: dict | None = None) -> None:
    st = _state(panel)
    st.setdefault("fold_clicks", {}).update(clicks or {})
    st["folds_dirty_at"] = time.monotonic() if now is None else now


def flush_folds(panel, now: float | None = None, force: bool = False) -> bool:
    """Write ``presets.folded`` (`ui_pane.write_key`, the rest of ui.json
    as it was) once `ui_pane.WRITE_AFTER_S` has passed since the last fold
    (`force`: now). Called each frame the list draws; True when it wrote."""
    from . import ui_pane
    st = _state(panel)
    at = st.get("folds_dirty_at")
    machine = _machine(panel)
    if at is None or machine is None:
        return False
    now = time.monotonic() if now is None else now
    if not force and now - at < ui_pane.WRITE_AFTER_S:
        return False
    ui_pane.write_key(machine, UI_KEY, {"folded": sorted(folded(panel), key=str.lower)},
                      "presets")
    st.pop("folds_dirty_at", None)
    st.pop("fold_clicks", None)
    return True


def _trash_popup(panel, bin_: list) -> None:
    """The trash (plan 19 WP4), a popup off the list's "trash (n) ▸": every
    file it holds, newest first — every group and the shows a rename kept,
    for "empty" deletes what is listed and nothing else — each with
    `restore`, in a child that scrolls past LIST_ROWS rows; then "empty
    trash…", which asks once in place: it becomes "delete N files for
    good? — click again" in the warning ink for EMPTY_S; a second click in
    that time empties, anything else (the time running out, the popup
    closing, any other click) disarms it. No modal: the show runs on."""
    lib, st = panel.library, _state(panel)
    if not imgui.begin_popup("trash"):
        st["empty_armed"] = None                       # closed: disarmed
        return
    drawn: dict = {"rows": [], "rects": {}, "empty": None}
    st["trash_view"] = drawn

    def rect(key: str) -> None:
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        drawn["rects"][key] = (a.x, a.y, b.x, b.y)

    n = len(bin_)
    ui._micro(f"trash  ·  {n} file{'' if n == 1 else 's'}")
    style = imgui.get_style()
    gw = max([imgui.calc_text_size(trash_tag(t)).x for t in bin_] or [0.0])
    nw = max([imgui.calc_text_size(t.name).x for t in bin_] or [0.0])
    ww = imgui.calc_text_size("Oct 30 00:00").x
    sp = 2 * style.item_spacing.x
    wide = gw + nw + ww + 3 * sp + ui.chip_w("restore") + style.scrollbar_size
    row_h = imgui.get_frame_height_with_spacing()
    if bin_ and imgui.begin_child("##trash.rows",
                                  imgui.ImVec2(wide, row_h * min(n, LIST_ROWS))):
        for i, item in enumerate(bin_):
            x = imgui.get_cursor_pos_x()
            imgui.align_text_to_frame_padding()
            imgui.text_disabled(trash_tag(item))       # an old row says so in itself
            imgui.same_line(x + gw + sp)
            imgui.text(item.name)
            imgui.same_line(x + gw + nw + 2 * sp)
            imgui.text_disabled(item.when)
            imgui.same_line(x + gw + nw + ww + 3 * sp)
            hit = ui.chip(f"restore##restore.{i}")
            rect(f"restore.{i}")
            drawn["rows"].append((item.group, item.name, item.when))
            drawn.setdefault("tags", []).append(trash_tag(item))
            if imgui.is_item_hovered():
                ui.tooltip(f"{item.path.name} — back into {item.group}/, never over a "
                           "file: a name that is taken gets the next free one"
                           + ("\nFrom the library's old trash: a copy comes back and the "
                              "file stays there (empty trash leaves it)"
                              if item.old else ""))
            if hit:
                _said(panel, lib.restore_trash, item)
                invalidate(panel, item.group)
                invalidate(panel, PROJECT)
                invalidate(panel, LOADABLE)
        imgui.end_child()
        rect("rows")
    # plan 48 row 586: the trash is this Mac's; what the library's own
    # trash kept from before is listed and restorable, never emptied here
    old = sum(1 for t in bin_ if t.old)
    drawn["old"] = old
    if old:
        ui._micro(f"{old} from the library's old trash — restore copies, empty leaves them")
        if imgui.is_item_hovered():
            ui.tooltip("Deletes and overwritten files now go to this Mac's trash "
                       f"({lib._trash_dir()}), never the shared library. The "
                       f"library's old trash ({lib.home / 'trash'}) is shown so its files "
                       "can be restored: a restore copies the file back and leaves it "
                       "there (the app never writes to the shared folder's trash); "
                       "clear it in Finder.")
    n -= old
    imgui.separator()
    if n == 0:
        # only the library's old trash is listed: nothing here to empty, so
        # no chip to arm ("delete 0 files for good?", review of #334)
        st["empty_armed"] = None
        drawn["empty"] = None
        imgui.end_popup()
        return
    now = imgui.get_time()
    armed = st.get("empty_armed")
    if armed is not None and now - armed > EMPTY_S:
        armed = st["empty_armed"] = None
    label = (f"delete {n} file{'' if n == 1 else 's'} for good? — click again"
             if armed is not None else "empty trash…")
    elsewhere = imgui.is_mouse_clicked(0) or imgui.is_mouse_clicked(1)
    if armed is not None:
        imgui.push_style_color(imgui.Col_.text, ui.WARN)
    hit = ui.chip(f"{label}##empty")
    if armed is not None:
        imgui.pop_style_color()
    rect("empty")
    drawn["empty"] = label
    hov = imgui.is_item_hovered()
    if hov:
        ui.tooltip("Delete every file listed here for good — the one delete in "
                   "the app that keeps no copy. Asks once: click again within "
                   f"{EMPTY_S:.0f} s")
    if hit:
        if armed is not None:
            st["empty_armed"] = None
            _said(panel, lib.empty_trash)
            invalidate(panel, LOADABLE)
            imgui.close_current_popup()
        else:
            st["empty_armed"] = now
    elif armed is not None and elsewhere and not hov:
        st["empty_armed"] = None                       # any other click: disarmed
    imgui.end_popup()


# ---- the patches fold (plan 40 T3) ----

def patches_fold(panel) -> None:
    """The **patches** fold — every patch (`Library.list(PATCHES)`), each a
    row of the list's own (`_list_row`): rename, and × to the trash. No
    spawn from here: that is GRAPH's (its head's **patches** chip, the
    canvas's **spawn ▸**). Folded unless opened; what was drawn is kept in
    `_state`'s ``patches``."""
    lib = panel.library
    if lib is None:
        return
    if not imgui.collapsing_header("patches##presets.patches"):
        return
    st = _state(panel)
    rows = names(panel, PATCHES)
    drawn: dict = {"group": PATCHES, "rows": [], "foot": [], "rects": {}}
    st["patches"] = drawn

    def rect(key: str) -> None:
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        drawn["rects"][key] = (a.x, a.y, b.x, b.y)

    if not rows:
        imgui.text_disabled("no patches — on GRAPH, a group's menu: save as patch…")
    for name in rows:
        _list_row(panel, PATCHES, name, None, drawn, rect)


# ---- the show: one line ----

def show_line(panel) -> None:
    """What a show is, in one line (SHOW_LINE, SHOW_TIP on hover); then
    its name ● · open ▾ · save · as… · new. The pads are the desk's to
    set; the startup loadable patch stays whatever the file says."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    proj = lib.project
    imgui.push_id("show")
    # the line's right edge: a chip that would pass it starts a new row
    # (GRAPH's side pane, plan 49; every page has the room for one row)
    right = imgui.get_cursor_screen_pos().x + imgui.get_content_region_avail().x
    ui._micro(ui.fit_micro(SHOW_LINE, right - imgui.get_cursor_screen_pos().x))
    _rect(panel, "show.line")
    if imgui.is_item_hovered():
        ui.tooltip(SHOW_TIP)
    if _name_field(panel, PROJECT, lambda n: _project_save_as(panel, n)):
        imgui.pop_id()
        return
    ui._readout(proj.name)
    _rect(panel, "show.name")
    if imgui.is_item_hovered():
        ui.tooltip(str(proj.path) if proj.path else
                   "not saved yet — save writes it into the library")
    if proj.is_dirty():
        imgui.same_line(0, 4)
        imgui.text_colored(ui.RED, "●")
        _rect(panel, "show.dot")
        if imgui.is_item_hovered():
            ui.tooltip("the show differs from its file: the meta controller (tempo, hands, "
                       "the analyzer, output) or its pads")
    _beside(right, SHOW_W)
    imgui.set_next_item_width(SHOW_W)
    if imgui.begin_combo("##shows", "open"):
        listing = names(panel, PROJECT)
        if not listing:
            imgui.text_disabled("no saved shows")
        for name in listing:
            picked, _ = imgui.selectable(name, name == proj.stem)
            if picked:
                _guard(panel, proj.load, name)
                invalidate(panel, LOADABLE)
        imgui.end_combo()
    _rect(panel, "show.menu")
    if imgui.is_item_hovered():
        ui.tooltip("Open another show from the library")
    _beside(right, ui.chip_w("save"))
    if ui.chip("save"):
        _guard(panel, proj.save)
        invalidate(panel, PROJECT)
    _rect(panel, "show.save")
    if imgui.is_item_hovered():
        ui.tooltip("Save the show — the meta controller (tempo, hands, the analyzer, output) "
                   "and its pads")
    _beside(right, ui.chip_w("as…"))
    if ui.chip("as…"):
        _begin_naming(panel, PROJECT, proj.name)
    _rect(panel, "show.save_as")
    if imgui.is_item_hovered():
        ui.tooltip("Save the show under another name")
    _beside(right, ui.chip_w("new"))
    if ui.chip("new"):
        _guard(panel, proj.new)
        invalidate(panel, LOADABLE)
    _rect(panel, "show.new")
    if imgui.is_item_hovered():
        ui.tooltip("A new show: fresh state, every pad empty")
    imgui.pop_id()


def _beside(right: float, w: float) -> None:
    """The next item, `w` wide, on the line of the one before when it ends
    by `right`; else (a narrow pane) on a row of its own."""
    if imgui.get_item_rect_max().x + imgui.get_style().item_spacing.x + w <= right:
        imgui.same_line()


def _project_save_as(panel, name: str) -> None:
    _guard(panel, panel.library.project.save, name)
    invalidate(panel, PROJECT)


# ---- the library's lines ----

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
