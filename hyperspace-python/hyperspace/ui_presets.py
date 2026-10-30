"""Preset strips and the PRESETS page — the library's face on the panel.

Every section of the panel that sits on a registry group the library
knows (library.groups()) carries a strip under its title:

  ◀  name ●  ▶      save   as…   reset

prev / next step through ``library.list(group)``; on a module group the
name opens the group's list (× on each, to the trash); the dot is
``is_dirty(group)``, a 12 px red disc (``ui.dirty_dot``, plan 19 WP5),
and while it shows the save chip is lit solid red; save writes over the
current preset (its old text kept in the trash) and is disabled only when
none is loaded; as… turns the strip into a name field until Enter (or
Esc); reset (module strips only) lands the group on its default preset
or its fresh values.

The PRESETS page (2026-10-28: one tier — nothing is factory, nothing is
hidden, every preset is yours to load, rename and delete) reads top to
bottom (``page``):

  PRESET      the preset strip over the ``presets`` document kind
              (preset.py): ◀ loaded preset ● ▶ · new · save · as… — the
              name is a readout, the list is the page
  the list    every preset by name, the loaded one selected, filling the
              page: a click loads, `rename` turns the row into a name
              field, × sends the file to the trash. Nothing folds, nothing
              drops down, nothing is dim
  trash (n) ▸ at the list's foot, only while the trash holds something:
              its own popup — restore per file, "empty trash…" asked twice
              in place
  patches ▸   folded: every patch (plan 40 T3), rename and × — a patch is
              spawned on GRAPH, never loaded here
  SHOW        one line that says what a show is — the desk's pads, the
              session and the rig's wires — then its name ●, open ▾ (your
              shows), save, as…, new. The pads are set on the desk (hold
              a pad, or SAVE + a pad); nothing on the page edits them

The library's warning, error and status lines stay under all of it, so a
note like a rename's is seen. The ROUTING page's head is the preset
strip's save / as… over the same ``presets`` group (ui_routing.head).

These are functions over the Panel rather than widget classes: the
state they need (the name field, the cached listings) lives on the
panel, and ui.py's imports rebind to fresh code on a hot reload. A
listing stats every file in the group's folder, so it is refreshed on
a poll cadence (LIST_POLL), never per frame; dirty state is a snapshot
compare and is cheap enough to ask each frame for the page on screen.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import preset, ui
from .library import (
    PATCHES,
    PRESETS,
    RETIRED_MODULES,
    LibraryError,
)

LIST_POLL = 1.0      # seconds between re-listings of a group's presets
NAME_MAX = 14        # chars of a preset name the strip shows before eliding
PROJECT = "show"     # the listing / name-field key for the show line
SHOW_W = 96          # the open ▾ menu
# plan 19 WP4: a module strip's list and the trash's view
LIST_ROWS = 12       # rows of a module strip's list, and of the trash, before each scrolls
EMPTY_S = 4.0        # how long "empty trash…" stays armed for its second click
MIN_ROWS = 3         # the page's list is never shorter than this many rows
TRASH_KEY = "\0trash"     # the listings cache: the trash
# what a show is, in one line under the SHOW label and in its hover
SHOW_LINE = "show  ·  the desk's pads, the session, the rig's wires"
SHOW_TIP = ("A show is the room the presets play in: which preset each of the desk's "
            "twenty-four pads loads (set on the desk — hold a pad, or SAVE + a pad), the "
            "session (tempo, hands, the analyzer, the outputs), the band scene, and the "
            "bus cables cut on GRAPH. A preset is the look; the show is everything "
            "around it. Open another, save this one, or start a new one here.")


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
    for slot in (key, TRASH_KEY):
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

def save_label(lib, group: str) -> str:
    """The save chip's words — "save" (one tier: every save writes the
    loaded preset's own file; kept as a function for ROUTING's head)."""
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


def strip(panel, group: str) -> None:
    """◀ name ● ▶ · save · as… · reset — for one registry group. On the
    presets' strip (a document kind) there is no reset (`Library.reset`
    on a kind loads a preset called "default", and none ships) and `new`
    starts a blank preset (plan 35 T7); its name is a readout — the
    PRESETS page's list is under it. A module strip's name opens the
    group's list."""
    lib = panel.library
    if lib is None or lib.reg is None or group in RETIRED_MODULES:
        return                  # (plan 40 T5: a retired module group has no strip)
    imgui.push_id(f"strip.{group}")
    if _name_field(panel, group, lambda n: _save_as(panel, group, n)):
        imgui.pop_id()
        return
    st = _state(panel)
    cur = lib.current(group)
    listing = names(panel, group)
    is_dirty = dirty(panel, group)
    kind = group in lib.kinds
    presets = getattr(lib, "presets", None) if group == PRESETS else None

    # ◀ name ▶ — the arrows step by name order; a module strip's name opens its list
    imgui.begin_disabled(not listing)
    if imgui.arrow_button("prev", imgui.Dir.left):
        _guard(panel, lib.prev, group)
    imgui.same_line(0, 2)
    label = _elide(cur) if cur else "—"
    imgui.push_style_color(imgui.Col_.button, imgui.ImVec4(0, 0, 0, 0))
    imgui.push_style_color(imgui.Col_.text, ui.DIM if cur is None else
                           imgui.ImVec4(0.92, 0.92, 0.92, 1))
    if imgui.button(f"{label}##name", imgui.ImVec2(name_w(), 0)) and group != PRESETS:
        imgui.open_popup("list")
    imgui.pop_style_color(2)
    _rect(panel, f"strip.{group}.name")
    if imgui.is_item_hovered():
        if cur is None:
            ui.tooltip("no preset loaded")
        elif group == PRESETS:
            ui.tooltip(f"{cur}  ·  the loaded preset — the list is below")
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
    if group == PRESETS:
        from . import ui_graph  # (late, as `new` below)
        ui_graph._wants_chip(panel)     # plan 40 T4: the devices the preset waits for
    else:
        _list_popup(panel, group, listing, cur)

    # (new ·) save · as… (· reset on a module strip), flush right
    word = "save"
    chips = (word, "as…") if kind else (word, "as…", "reset")
    if presets is not None:
        chips = ("new", *chips)
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w(*chips))
    if presets is not None:
        if ui.chip("new##new"):
            from . import ui_graph  # (late: ui_graph imports ui_routing, which imports this)
            # plan 36 T5: its chain laid out where the GRAPH page is looking
            _guard(panel, presets.new, ui_graph.in_view(panel))
            invalidate(panel, group)
        _rect(panel, f"strip.{group}.new")
        if imgui.is_item_hovered():
            ui.tooltip("A new preset: default values, shape → scene → All outputs — "
                       "a shape on every window")
        imgui.same_line()
    # R17: a preset `new` made and nothing saved names itself — a preset
    # that happens to be called `untitled` is never written over (the flag
    # counts while `untitled` is current: an undo of New hands back the
    # preset before, which saves as it always did)
    unsaved = presets is not None and cur == preset.UNTITLED_PRESET and (
        bool(getattr(presets, "unsaved", False)) or lib.path_of(group, cur) is None)
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
    imgui.pop_id()


def _save_as(panel, group: str, name: str) -> None:
    _guard(panel, panel.library.save_as, group, name)
    invalidate(panel, group)


def _rename(panel, old: str, new: str, group: str = PRESETS) -> None:
    _said(panel, panel.library.rename, group, old, new)
    invalidate(panel, group)
    invalidate(panel, PROJECT)


def list_row_h() -> float:
    """A row of a preset list: a chip's height (the tallest item in it)
    and the spacing under it."""
    return (imgui.get_text_line_height() + 2 * ui.CHIP_PAD.y
            + imgui.get_style().item_spacing.y)


def _list_row(panel, group: str, name: str, cur: str | None, drawn: dict, rect) -> None:
    """One row of a preset list: the name (a pick loads it), then its
    chips — `rename` and × on a preset or a patch (plan 40 T3: a patch's
    row has no pick — a patch is spawned on GRAPH, never loaded), × alone
    on a module preset. What was drawn joins `drawn["rows"]` as
    ``(name, chips)``."""
    lib, st = panel.library, _state(panel)
    patch = group == PATCHES
    renamable = group == PRESETS or patch
    key = f"rename:{group}:{name}" if patch else f"rename:{name}"
    if renamable and st["naming"] == key:          # the row is the name field
        drawn["rows"].append((name, ("field",)))
        _name_field(panel, key, lambda n, old=name: _rename(panel, old, n, group))
        return
    imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(0.92, 0.92, 0.92, 1))
    picked, _ = imgui.selectable(f"{name}##pick", name == cur,
                                 imgui.SelectableFlags_.allow_overlap)
    imgui.pop_style_color()
    rect(f"row.{name}")
    if picked and not patch:
        _guard(panel, lib.load, group, name)
    chips = ("rename", "×") if renamable else ("×",)
    drawn["rows"].append((name, chips))
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w(*chips))
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
            _begin_naming(panel, key, name)
        else:
            _guard(panel, lib.delete, group, name)
        invalidate(panel, group)
    imgui.pop_style_color()


def _list_popup(panel, group: str, listing: list[str], cur: str | None) -> None:
    """A module strip's list, the popup its name opens: every preset of the
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
    if lib is None or lib.reg is None or PRESETS not in lib.kinds:
        return
    ui._micro("preset")
    strip(panel, PRESETS)
    preset_list(panel)
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


def preset_list(panel) -> None:
    """Every preset, as a list that fills the page (never shorter than
    MIN_ROWS rows, scrolling past the room it has): the loaded one
    selected, a click loads, `rename` and × on each row (`_list_row`);
    then the trash's foot line while the trash holds something. What was
    drawn is kept in `_state`'s ``page`` for the tests: each row's name
    and chips, the foot's lines, screen rects."""
    lib, st = panel.library, _state(panel)
    cur = lib.current(PRESETS)
    rows = names(panel, PRESETS)
    bin_ = trashed(panel)
    drawn: dict = {"group": PRESETS, "rows": [], "foot": [], "rects": {}}
    st["page"] = drawn

    def rect(key: str) -> None:
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        drawn["rects"][key] = (a.x, a.y, b.x, b.y)

    room = imgui.get_content_region_avail().y - _reserve()
    height = max(room, list_row_h() * MIN_ROWS)
    if imgui.begin_child("##presets.rows", imgui.ImVec2(0, height)):
        if not rows:
            imgui.text_disabled("no presets — new, then save as… makes one")
        for name in rows:
            _list_row(panel, PRESETS, name, cur, drawn, rect)
    imgui.end_child()
    rect("rows")
    if bin_:
        line = f"trash ({len(bin_)}) ▸"
        hit, _ = imgui.selectable(f"{line}##trash", False)
        drawn["foot"].append(line)
        rect("trash")
        if hit:
            st["empty_armed"] = None
            imgui.open_popup("trash")
        if imgui.is_item_hovered():
            ui.tooltip("What × and rename sent to the trash, and every older version a "
                       "save replaced: restore puts one back")
        _trash_popup(panel, bin_)


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
    gw = max([imgui.calc_text_size(t.group).x for t in bin_] or [0.0])
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
            imgui.text_disabled(item.group)
            imgui.same_line(x + gw + sp)
            imgui.text(item.name)
            imgui.same_line(x + gw + nw + 2 * sp)
            imgui.text_disabled(item.when)
            imgui.same_line(x + gw + nw + ww + 3 * sp)
            hit = ui.chip(f"restore##restore.{i}")
            rect(f"restore.{i}")
            drawn["rows"].append((item.group, item.name, item.when))
            if imgui.is_item_hovered():
                ui.tooltip(f"{item.path.name} — back into {item.group}/, never over a "
                           "file: a name that is taken gets the next free one")
            if hit:
                _said(panel, lib.restore_trash, item)
                invalidate(panel, item.group)
                invalidate(panel, PROJECT)
                invalidate(panel, PRESETS)
        imgui.end_child()
        rect("rows")
    imgui.separator()
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
            invalidate(panel, PRESETS)
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
    set; the startup preset stays whatever the file says."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    proj = lib.project
    imgui.push_id("show")
    ui._micro(SHOW_LINE)
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
            ui.tooltip("the show differs from its file: the session (tempo, hands, "
                       "the analyzer, output), its pads or its wires")
    imgui.same_line()
    imgui.set_next_item_width(SHOW_W)
    if imgui.begin_combo("##shows", "open"):
        listing = names(panel, PROJECT)
        if not listing:
            imgui.text_disabled("no saved shows")
        for name in listing:
            picked, _ = imgui.selectable(name, name == proj.stem)
            if picked:
                _guard(panel, proj.load, name)
                invalidate(panel, PRESETS)
        imgui.end_combo()
    _rect(panel, "show.menu")
    if imgui.is_item_hovered():
        ui.tooltip("Open another show from the library")
    imgui.same_line()
    if ui.chip("save"):
        _guard(panel, proj.save)
        invalidate(panel, PROJECT)
    _rect(panel, "show.save")
    if imgui.is_item_hovered():
        ui.tooltip("Save the show — the session (tempo, hands, the analyzer, output), "
                   "its pads and its wires")
    imgui.same_line()
    if ui.chip("as…"):
        _begin_naming(panel, PROJECT, proj.name)
    _rect(panel, "show.save_as")
    if imgui.is_item_hovered():
        ui.tooltip("Save the show under another name")
    imgui.same_line()
    if ui.chip("new"):
        _guard(panel, proj.new)
        invalidate(panel, PRESETS)
    _rect(panel, "show.new")
    if imgui.is_item_hovered():
        ui.tooltip("A new show: fresh state, every pad empty")
    imgui.pop_id()


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
