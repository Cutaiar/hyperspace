"""Preset strip and the PRESETS page — the library's face on the panel.

Every section of the panel that sits on a registry group the library
knows (library.groups()) carries a strip under its title:

  ◀  name ●  ▶      save   as…   reset

prev / next step through ``library.list(group)``; the name opens the
list (factory presets dim, user ones deletable); the dot is
``is_dirty(group)``, a 12 px red disc (``ui.dirty_dot``, plan 19 WP5),
and while it shows the save chip is lit solid red; save writes over the
current preset and is disabled only when none is loaded — on a
**factory** preset it writes your own copy of it (``Library.overwrite``
shadows the factory file, never touches it), and on the preset strip it
says so: "save copy"; as… turns the strip into a name field until Enter
(or Esc); reset (module strips only: on the presets it did nothing) lands
the group on its default preset — the "meaningful default" — or its
fresh values when it has none. The preset strip reads

  ◀  name ●  ▶            save copy   as…

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
              "free this pad (keeps the preset)" — the show is written at once, no file is
              deleted
  9–24        sixteen smaller buttons four a row (plan 19 WP1, layout B):
              the bank's far slots, the desk's clip rows 4 and 5, each its
              number and its preset's name; click loads, ⇧click saves, the
              same right-click menu. All twenty-four are on the page at
              once: no paging, no fold, and the page does not scroll with
              "more" open (``tests/test_ui_presets.py``)
  PRESET      the one preset strip — this strip over the ``presets``
              group, a document kind preset.py keeps: the loaded preset,
              its dirty dot, save / as…. Its name opens the preset list
              (plan 19 WP4): × on every preset (yours to the trash, a
              factory one hidden), rename on yours, and at its foot "show
              hidden (n)" and "trash (n) ▸" — the trash's own popup, with
              restore and "empty trash…" asked twice in place — each line
              only while it has something; no line on the page itself. A
              bank slot whose preset has no file is drawn in the warning
              ink, its hover saying where to look
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

from . import preset, ui
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
SLOT_DOT_R = 4.0     # the white disc on the loaded slot while its preset is edited (WP5)
# plan 19 WP4: the preset list's foot and the trash's view
LIST_ROWS = 12       # rows of the preset list, and of the trash, before each scrolls
EMPTY_S = 4.0        # how long "empty trash…" stays armed for its second click
HIDDEN_KEY = "\0hidden"   # the listings cache: a group's list with the hidden ones
BANK_KEY = "\0bank"       # …whether each name the bank holds has a file
TRASH_KEY = "\0trash"     # …the trash
FACTORY_KEY = "\0factory"  # …a group's factory names, and every name it indexes
# the module overview: every performance group but the macros (a macro's
# meaning is its subscribers, which live in the preset) and the media
# channels and backdrop (plan 32: a channel's values mean nothing without
# its bin, the preset's media section; the MEDIA page holds them) and (plan
# 33 S) the switches' picks and (plan 34 Z) the resizes' values (nothing
# without the preset's graph), and the
# band strip's scene, the one session module a project names
OVERVIEW_GROUPS = (*[g for g in PERFORMANCE_GROUPS
                     if g not in ("macro", "mod", "media", "backdrop", "switch", "resize")],
                  "band")


# ---- state on the panel, created on first use ----

def _state(panel) -> dict:
    st = getattr(panel, "_lib_state", None)
    if st is None:
        st = panel._lib_state = {"lists": {}, "naming": None, "buf": "", "dirty": {}}
    # what the PRESETS page drew last frame: each widget's screen rect by
    # key, and the preset buttons' labels — for the layout tests
    st.setdefault("rects", {})
    st.setdefault("bank_labels", [])
    st.setdefault("save", {})          # group → (the save chip's words, lit), last drawn
    return st


def _rect(panel, key: str) -> None:
    """Record the last item's screen rect under `key` (_state's `rects`)."""
    a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    _state(panel)["rects"][key] = (a.x, a.y, b.x, b.y)


def names(panel, key: str, *, hidden: bool = False) -> list[str]:
    """``library.list(group)`` (or the project list), refreshed on the poll
    cadence; with `hidden`, the factory presets × hid too (plan 19 WP4)."""
    st, lib = _state(panel), panel.library
    now = imgui.get_time()
    slot = f"{key}{HIDDEN_KEY}" if hidden else key
    hit = st["lists"].get(slot)
    if hit is None or now - hit[0] >= LIST_POLL:
        try:
            listing = (lib.project.list() if key == PROJECT
                       else lib.list(key, hidden=True) if hidden else lib.list(key))
        except (LibraryError, OSError) as e:
            lib.error = f"library: {e}"
            listing = hit[1] if hit else []
        st["lists"][slot] = hit = (now, listing)
    return hit[1]


def invalidate(panel, key: str) -> None:
    """Our own write: the next frame re-lists rather than waiting out the
    poll — the listing, the one with the hidden presets, whether the
    bank's names have files, and the trash."""
    lists = _state(panel)["lists"]
    for slot in (key, f"{key}{HIDDEN_KEY}", f"{key}{FACTORY_KEY}", BANK_KEY, TRASH_KEY):
        lists.pop(slot, None)


def is_factory(panel, group: str, name: str) -> bool:
    """``Library.is_factory`` on the poll cadence. Asked per row of the open
    list, every frame, the library's answer re-indexed the whole group each
    time — both roots globbed, every file stat'ed — which on a cloud
    library of 79 presets was ~50 ms a frame (25 fps with the list open).
    A name the index does not hold (reached by its slug alone) is asked
    of the library."""
    st, lib = _state(panel), panel.library
    now = imgui.get_time()
    slot = f"{group}{FACTORY_KEY}"
    hit = st["lists"].get(slot)
    if hit is None or now - hit[0] >= LIST_POLL:
        try:
            known = lib.factory_names(group)
        except (LibraryError, OSError) as e:
            lib.error = f"library: {e}"
            known = hit[1] if hit else (frozenset(), frozenset())
        st["lists"][slot] = hit = (now, known)
    factory, indexed = hit[1]
    return name in factory if name in indexed else lib.is_factory(group, name)


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


def missing(panel, name: str) -> bool:
    """Does the bank's `name` have no preset file (in the trash, or never
    was)? Answered for every name in the bank on the poll cadence, never
    per frame (`Library.path_of` reads the folders)."""
    st, lib, pr = _state(panel), panel.library, panel.bank
    now = imgui.get_time()
    hit = st["lists"].get(BANK_KEY)
    if hit is None or now - hit[0] >= LIST_POLL or name not in hit[1]:
        known = {n: lib.path_of(PRESETS, n) is not None for n in set(pr.bank) | {name} if n}
        st["lists"][BANK_KEY] = hit = (now, known)
    return not hit[1].get(name, True)


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

def save_label(lib, group: str) -> str:
    """The save chip's words (plan 19 WP5): "save copy" while the loaded
    preset is a factory one — the save writes your own copy, which takes
    its place in the list (`Library.overwrite`) — else "save"."""
    cur = lib.current(group)
    return "save copy" if cur is not None and lib.is_factory(group, cur) else "save"


def save_tip(lib, group: str) -> str:
    """The save chip's hover, in the label's terms."""
    cur = lib.current(group)
    if cur is None:
        return "No preset loaded: as… saves the settings as a new one"
    if lib.is_factory(group, cur):
        return (f"Save your own copy of {cur}: the factory one is kept and yours takes "
                "its place in the list")
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
    """◀ name ● ▶ · save · as… · reset — for one registry group. On a
    document kind's strip (the presets) the save chip says "save copy" on
    a factory preset and there is no reset: `Library.reset` on a kind
    loads a preset called "default", and none ships (plan 19 WP5)."""
    lib = panel.library
    if lib is None or lib.reg is None:
        return
    imgui.push_id(f"strip.{group}")
    if _name_field(panel, group, lambda n: _save_as(panel, group, n)):
        imgui.pop_id()
        return
    st = _state(panel)
    cur = lib.current(group)
    listing = names(panel, group)
    factory = cur is not None and is_factory(panel, group, cur)
    is_dirty = dirty(panel, group)
    kind = group in lib.kinds

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
    _rect(panel, f"strip.{group}.name")
    if imgui.is_item_hovered():
        ui.tooltip(f"{cur}  ·  {'factory' if factory else 'user'} preset — "
                          "click for the list" if cur else "no preset loaded")
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
    _list_popup(panel, group, listing, cur)

    # save · as… (· reset on a module strip), flush right
    word = save_label(lib, group) if kind else "save"
    # plan 35 T7 (row 387): `new` starts a blank preset, on the presets' strip
    presets = getattr(lib, "presets", None) if group == PRESETS else None
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
            ui.tooltip("A new preset: factory values, shape → scene → All outputs — "
                              "a shape on every window")
        imgui.same_line()
    # R17: a preset `new` made and nothing saved names itself — a user
    # preset that happens to be called `untitled` is never written over
    # (the flag counts while `untitled` is current: an undo of New hands
    # back the preset before, which saves as it always did)
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
        ui.tooltip("Save the group's settings as a new user preset")
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


def _said(panel, fn, *args):
    """Run a library call from the preset list; a refusal goes on the
    library's warning line, which the footer shows (`Library.say`)."""
    lib = panel.library
    try:
        return fn(*args)
    except (LibraryError, OSError) as e:
        lib.say(warning=f"library: {e}")
        return None


def _rename(panel, old: str, new: str) -> None:
    _said(panel, panel.library.rename, PRESETS, old, new)
    invalidate(panel, PRESETS)
    invalidate(panel, PROJECT)


def _list_popup(panel, group: str, listing: list[str], cur: str | None) -> None:
    """The list the strip's name opens: every preset, the loaded one
    selected, factory ones dim; × on your own (to the trash) — and, on the
    presets' list (plan 19 WP4), × on a factory one (hidden), `rename` on
    yours (the strip's inline name field in the row), "show hidden (n)"
    while something is hidden and "trash (n) ▸" while the trash holds
    something. Past LIST_ROWS rows the list scrolls in its own child. What
    was drawn is kept in `_state`'s ``list`` for the tests: each row's name,
    its chips and whether it is hidden; the foot's lines; screen rects."""
    st = _state(panel)
    if not imgui.begin_popup("list"):
        if group == PRESETS:
            st["empty_armed"] = None                  # the list closed: disarmed
        return
    presets = group == PRESETS
    show_hidden = presets and st.get("show_hidden", False)
    rows = names(panel, group, hidden=True) if show_hidden else listing
    gone = set(names(panel, group, hidden=True)) - set(listing) if presets else set()
    bin_ = trashed(panel) if presets else []
    drawn: dict = {"group": group, "rows": [], "foot": [], "rects": {}}
    st["list"] = drawn

    def rect(key: str) -> None:
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        drawn["rects"][key] = (a.x, a.y, b.x, b.y)

    ui._micro(group)
    style = imgui.get_style()
    chips = ("rename", "×") if presets else ("×",)
    wide = (max([imgui.calc_text_size(n).x for n in rows] or [0.0]) + 3 * style.item_spacing.x
            + max(ui.chip_w(*chips), ui.chip_w("unhide")))
    row_h = list_row_h()
    imgui.dummy(imgui.ImVec2(wide + style.scrollbar_size, 0))     # the list's width
    if not rows:
        imgui.text_disabled("no presets — save as… makes one")
    else:
        size = imgui.ImVec2(wide + style.scrollbar_size,
                            row_h * min(len(rows), LIST_ROWS))
        if imgui.begin_child("##rows", size):
            for name in rows:
                _list_row(panel, group, name, cur, name in gone, drawn, rect)
        imgui.end_child()
        rect("rows")
    if presets and (gone or bin_):
        imgui.separator()
        if gone:
            line = f"show hidden ({len(gone)})"
            hit, _ = imgui.selectable(f"{line}##hidden", show_hidden,
                                      imgui.SelectableFlags_.no_auto_close_popups)
            drawn["foot"].append(line)
            rect("show_hidden")
            if hit:
                st["show_hidden"] = not show_hidden
            if imgui.is_item_hovered():
                ui.tooltip("The factory presets × took off this list: shown struck "
                                  "through, each with unhide. A slot that names one still "
                                  "loads it")
        if bin_:
            line = f"trash ({len(bin_)}) ▸"
            hit, _ = imgui.selectable(f"{line}##trash", False,
                                      imgui.SelectableFlags_.no_auto_close_popups)
            drawn["foot"].append(line)
            rect("trash")
            if hit:
                st["empty_armed"] = None
                imgui.open_popup("trash")
            if imgui.is_item_hovered():
                ui.tooltip("What × and rename sent to the trash, and every older "
                                  "version a save replaced: restore puts one back")
        _trash_popup(panel, bin_)
    imgui.end_popup()


def list_row_h() -> float:
    """A row of the preset list: a chip's height (the tallest item in it)
    and the spacing under it."""
    return (imgui.get_text_line_height() + 2 * ui.CHIP_PAD.y
            + imgui.get_style().item_spacing.y)


def _list_row(panel, group: str, name: str, cur: str | None, hidden: bool, drawn: dict,
              rect) -> None:
    """One row of the preset list: the name (a pick loads it), then its chips."""
    lib, st = panel.library, _state(panel)
    presets = group == PRESETS
    key = f"rename:{name}"
    if presets and st["naming"] == key:            # the row is the name field
        drawn["rows"].append((name, ("field",), hidden))
        _name_field(panel, key, lambda n, old=name: _rename(panel, old, n))
        return
    factory = is_factory(panel, group, name)
    ink =(imgui.ImVec4(0.42, 0.42, 0.45, 1) if hidden else ui.DIM if factory
           else imgui.ImVec4(0.92, 0.92, 0.92, 1))
    imgui.push_style_color(imgui.Col_.text, ink)
    picked, _ = imgui.selectable(f"{name}##pick", name == cur,
                                 imgui.SelectableFlags_.allow_overlap)
    imgui.pop_style_color()
    rect(f"row.{name}")
    if hidden:                                     # struck through
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        y = (a.y + b.y) / 2
        imgui.get_window_draw_list().add_line(
            imgui.ImVec2(a.x, y), imgui.ImVec2(a.x + imgui.calc_text_size(name).x, y),
            ui.u32(ink), 1.5)
    if picked:
        _guard(panel, lib.load, group, name)
    if hidden:
        chips = ("unhide",)
    elif not factory:
        chips = ("rename", "×") if presets else ("×",)
    else:
        chips = ("×",) if presets else ()
    drawn["rows"].append((name, chips, hidden))
    if not chips:
        return
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w(*chips))
    imgui.push_style_color(imgui.Col_.text, ui.DIM)
    for i, chip in enumerate(chips):
        if i:
            imgui.same_line()
        hit = ui.chip(f"{chip}##{chip}.{name}")
        rect(f"{chip}.{name}")
        tip = ("Put it back in the list" if chip == "unhide" else
               "Give it another name: the file, and every show that names it" if chip == "rename"
               else "Off the list: the factory file stays, and a slot that names it still "
                    "loads it — show hidden brings it back" if factory else
               "To the trash (restore it from there); a factory preset of the same name "
               "comes back")
        if imgui.is_item_hovered():
            ui.tooltip(tip)
        if not hit:
            continue
        if chip == "unhide":
            _said(panel, lib.unhide, group, name)
        elif chip == "rename":
            _begin_naming(panel, f"rename:{name}", name)
        elif factory:
            _said(panel, lib.hide, group, name)
        else:
            _guard(panel, lib.delete, group, name)
        invalidate(panel, group)
    imgui.pop_style_color()


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
        ui.tooltip(str(proj.path) if proj.path else
                          "a factory show — save makes your copy" if factory else
                          "not saved yet — save writes it into the library")
    if proj.is_dirty():
        imgui.same_line(0, 4)
        imgui.text_colored(ui.RED, "●")
        _rect(panel, "show.dot")
        if imgui.is_item_hovered():
            ui.tooltip("the show differs from its file: the session (tempo, hands, "
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
        ui.tooltip("Open a show: party and house are factory (dim); yours "
                          "are in the library")
    imgui.same_line()
    if ui.chip("save"):
        _guard(panel, proj.save)
        invalidate(panel, PROJECT)
    _rect(panel, "show.save")
    if imgui.is_item_hovered():
        ui.tooltip("Save the show — the session (tempo, hands, the analyzer, "
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
        ui.tooltip("A new show: fresh state, the party show's presets")
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
        ui.tooltip(f"starts on: {proj.startup or 'none'} — the preset a launch and "
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
        ui.tooltip(
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
    # the loaded slot carries a white disc at its right end while the
    # loaded preset has unsaved edits (plan 19 WP5)
    edited = pr.active >= 0 and dirty(panel, PRESETS)
    st["rects"].pop("preset.dot", None)
    dangling: list[int] = []
    st["dangling"] = dangling                         # the slots drawn in the warning ink
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
        if lit and edited:
            room -= 2 * SLOT_DOT_R + 4                # the disc's own room at the right end
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
        # a slot whose preset has no file (in the trash, plan 19 WP4): the
        # warning ink, and the hover says where to look; never cleared for you
        gone = name is not None and missing(panel, name)
        if gone:
            dangling.append(k)
        dl.add_text(imgui.ImVec2(a.x + pad + imgui.calc_text_size(key + gap).x, y),
                    ui.u32(white if lit else ui.FAINT if name is None
                           else ui.WARN if gone else ui.TEXT), shown)
        if lit and edited:
            c = imgui.ImVec2(b.x - pad - SLOT_DOT_R, (a.y + b.y) / 2)
            dl.add_circle_filled(c, SLOT_DOT_R, ui.u32(white))
            st["rects"]["preset.dot"] = (c.x - SLOT_DOT_R, c.y - SLOT_DOT_R,
                                         c.x + SLOT_DOT_R, c.y + SLOT_DOT_R)
        if hov:
            ui.tooltip(slot_tip(k, name, gone=gone))
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


def slot_tip(k: int, name: str | None, *, gone: bool = False) -> str:
    """A bank button's hover: what the slot holds and how to reach it — an
    F-key for the first eight, a pad of the desk's clip rows 4 and 5 after;
    for a slot whose preset has no file (`gone`), where to look."""
    key = slot_key(k)
    if gone and name is not None:
        return (f"{key}: {name} — no such preset. It may be in the trash (preset list → "
                "trash). Right-click → free this pad (keeps the preset)")
    row, col = (0, k) if k < F_KEYS else divmod(k - F_KEYS, 8)
    pad = f"the desk's row {1 if k < F_KEYS else 4 + row}, pad {col + 1}"
    if name is not None:
        return (f"{key}: {name} — {pad}. Click loads, ⇧click saves the live state as "
                "it. On the desk, hold SAVE and tap the pad: a new preset here, "
                f"{name} kept in the list. Right-click → free this pad (keeps the "
                "preset) to make room")
    return (f"{key}: empty — {pad}. Hold SAVE and tap the pad, or hold the pad (or "
            "⇧click), to save the live state here, or right-click to put a preset here")


def _slot_menu(panel, k: int) -> None:
    """A bank slot's own items in its right-click menu (plan 15 WP4):
    **put preset here…**, a submenu of every preset in a child at most
    PUT_ROWS rows tall, and **free this pad (keeps the preset)**, disabled on an empty slot.
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
                                         ("free this pad (keeps the preset)", name is not None)]}

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
    if imgui.menu_item("free this pad (keeps the preset)", "", False, name is not None)[0]:
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
