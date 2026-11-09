"""The PRESETS page (2026-10-28: one tier — nothing is factory, nothing is
hidden) — headless imgui over the controls rig (tests/test_ui_shell.py),
on a home seeded with the corpus, which opens the party show.

Top to bottom (ui_loadable.page): the preset strip — ◀ name ● ▶ · new ·
save · as…, the name a readout — then every loadable patch as a list that fills
the page (a click loads, `rename` and × on each row), the trash's foot
while the trash holds something, the patches fold, one line for the show
(its name ●, open ▾, save, as…, new) and the library's notes. No bank
pills, no "starts on", no loadable patch combo, no module-preset fold.
"""

import json
import re
from pathlib import Path

import pytest
from imgui_bundle import imgui
from test_ui_routing import _drawn
from test_ui_shell import (  # noqa: F401 — the fixture
    CONTROL_SIZE,
    _click,
    frame,
    page_frame,
    rig,
)

from hyperspace import ui, ui_kit, ui_loadable, ui_pane
from hyperspace.library import HOME_UNSET, LOADABLE, PATCHES, RETIRED_MODULES, Library
from hyperspace.ui import PAGE_KEYS

ACID_WASH = Path(__file__).resolve().parent / "fixtures" / "patches" / "acid-wash.json"
# what the page must never say (the owner, 2026-10-28): whole words, lower case
BANNED = r"\b(starts on|f[1-8]|hidden|factory|slots?|project|startup|module patches?)\b"


def _overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _rects(panel):
    return dict(ui_loadable._state(panel)["rects"])


def _page(panel, n: int = 2):
    """The PRESETS page drawn `n` frames; the page's state."""
    page_frame(panel, "loadable")
    for _ in range(n - 1):
        page_frame(panel)
    return ui_loadable._state(panel)


def _labels(monkeypatch) -> dict[str, list]:
    """Every widget label the page hands imgui — buttons (the chips), the
    selectables (the rows, with whether each was selected), the headers,
    the name field's hint — appended to as frames draw."""
    got: dict[str, list] = {"button": [], "selectable": [], "header": [], "hint": []}
    button, selectable = imgui.button, imgui.selectable
    header, field = imgui.collapsing_header, imgui.input_text_with_hint
    monkeypatch.setattr(imgui, "button", lambda label, *a, **k: (
        got["button"].append(label), button(label, *a, **k))[1])
    monkeypatch.setattr(imgui, "selectable", lambda label, *a, **k: (
        got["selectable"].append((label, bool(a[0]) if a else False)),
        selectable(label, *a, **k))[1])
    monkeypatch.setattr(imgui, "collapsing_header", lambda label, *a, **k: (
        got["header"].append(label), header(label, *a, **k))[1])
    monkeypatch.setattr(imgui, "input_text_with_hint", lambda label, hint, *a, **k: (
        got["hint"].append(hint), field(label, hint, *a, **k))[1])
    return got


def _open_patches(monkeypatch):
    real = imgui.collapsing_header
    monkeypatch.setattr(imgui, "collapsing_header", lambda label, *a, **k: (
        label == "patches##presets.patches" or real(label, *a, **k)))


# ------------------------------------------------------------ the page, top to bottom

def test_the_page_is_strip_list_patches_show_top_to_bottom(rig):  # noqa: F811
    """The strip's rects, the list's box under it, the show line under
    that — and nothing of the old page: no bank pill, no "starts on", no
    loadable patch combo, no "more"."""
    panel = rig.panel
    st = _page(panel)
    rects, page = st["rects"], st["page"]
    assert {"strip.loadable.name", "strip.loadable.next", "strip.loadable.new",
            "strip.loadable.save", "strip.loadable.as"} <= set(rects)
    assert {"show.line", "show.name", "show.menu", "show.save", "show.save_as",
            "show.new"} <= set(rects)
    assert not [k for k in rects if k.startswith(("preset.", "starts_on", "strip.loadable.reset"))]
    assert "bank_labels" not in st and "slot_menu" not in st and "dangling" not in st
    new, save, as_ = (rects[f"strip.loadable.{k}"] for k in ("new", "save", "as"))
    assert new[2] <= save[0] < save[2] <= as_[0]                 # new · save · as…, in a row
    rows = page["rects"]["rows"]
    assert rects["strip.loadable.name"][3] <= rows[1]            # the strip over the list
    assert rows[3] <= rects["show.line"][1]                      # the show line under it
    assert rects["show.line"][3] <= rects["show.name"][1]        # then the show's own row
    assert page["group"] == "loadable"


def test_the_strips_name_is_a_readout_and_opens_no_list(rig, monkeypatch):  # noqa: F811
    """The name on the loadable patches' strip reads what is loaded ("—" for
    nothing) and a click on it opens nothing: the list is the page."""
    panel, lib = rig.panel, rig.lib
    got = _labels(monkeypatch)
    _page(panel)
    st = ui_loadable._state(panel)

    def said() -> str:          # what the name's button reads: the stock button's or the kit's
        if ui_kit.ready():
            return st["names"]["loadable"]
        return next(b for b in got["button"] if b.endswith("##name")).split("##")[0]
    assert said() == "—"
    lib.load("loadable", "TRIP")
    got["button"].clear()
    page_frame(panel)
    assert said() == "TRIP"
    _click(panel, st["rects"]["strip.loadable.name"])
    page_frame(panel)
    assert "list" not in st                                       # no popup list opened
    assert lib.current("loadable") == "TRIP"


def test_the_list_is_every_loadable_by_name_with_rename_and_cross(rig):  # noqa: F811
    """Every loadable patch of the library, in `Library.list`'s order (case folded),
    each row `rename` and × — one tier, no row dim, no row hidden; each
    row's chips clear its name inside the list's box."""
    panel, lib = rig.panel, rig.lib
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    st = _page(panel)
    page = st["page"]
    listing = lib.list("loadable")
    assert len(listing) == 25 and listing == sorted(listing, key=str.lower)
    assert {"TUMBLE", "BIG BLUE WAVE", "legacy6", "seq-demo", "DIAL"} <= set(listing)
    assert page["rows"] == [(name, ("rename", "×")) for name in listing]
    assert page["foot"] == []                                     # an empty trash: no foot
    box = page["rects"]["rows"]
    half = imgui.get_style().item_spacing.x / 2      # a selectable spans half a spacing out
    for name in listing:
        row, ren, x = (page["rects"][f"{k}.{name}"] for k in ("row", "rename", "×"))
        assert row[0] + imgui.calc_text_size(name).x < ren[0] < ren[2] <= x[0], name
        assert box[0] - half <= row[0] and x[2] <= row[2] + 1, name
        assert row[2] <= box[2] + half, name


def test_a_click_on_a_row_loads_it_and_the_loaded_row_is_selected(rig, monkeypatch):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    got = _labels(monkeypatch)
    st = _page(panel)
    assert lib.current("loadable") is None
    assert not [label for label, on in got["selectable"] if on]
    _click(panel, st["page"]["rects"]["row.FIELD"])
    assert lib.current("loadable") == "FIELD" and not lib.is_dirty("loadable")
    assert rig.view.shape == lib.read("loadable", "FIELD")["values"]["view.shape"]
    got["selectable"].clear()
    page_frame(panel)
    assert [label for label, on in got["selectable"] if on] == ["FIELD##pick"]
    _click(panel, st["page"]["rects"]["row.ACID"])
    assert lib.current("loadable") == "ACID"


def test_cross_sends_the_file_to_the_trash_and_the_row_goes(rig, tmp_path):  # noqa: F811
    """× on any row: the file goes to the trash, the row leaves the list,
    the foot says the trash holds something. A loadable patch a pad names is still
    its file's: the footer says which pad, nothing is cleared for you."""
    panel, lib = rig.panel, rig.lib
    st = _page(panel)
    page = st["page"]
    _click(panel, page["rects"]["×.DIAL"])
    assert not (tmp_path / "loadable" / "dial.json").exists()
    assert [t.name for t in lib.trash()] == ["DIAL"] and "DIAL" not in lib.list("loadable")
    assert lib.status == "DIAL is in the trash — the PATCHES section's trash can restore it"
    page_frame(panel)
    page = st["page"]
    assert "DIAL" not in [n for n, _ in page["rows"]] and len(page["rows"]) == 24
    assert page["foot"] == ["trash (1) ▸"] and "trash" in page["rects"]
    _click(panel, page["rects"]["×.ACID"])                       # F6's loadable patch
    assert lib.warning.startswith("ACID is in the trash — F6 still names it")
    assert lib.install.bank[5] == "ACID" and "ACID" not in lib.list("loadable")
    page_frame(panel)
    assert st["page"]["foot"] == ["trash (2) ▸"]


def test_a_folder_loadable_sits_under_its_header_and_renames_in_its_folder(rig):  # noqa: F811
    """Plan 48 row 588, under stage 2's tree (row 636): a loadable patch in
    ``loadable/party/`` is listed as ``party/DIAL`` and drawn under the
    ``party`` header by its leaf, its chips clear of it; `rename` seeds
    the field with the leaf alone, and the file stays in its folder.
    (The window tall enough that the folder, after every top-level
    loadable patch, is in view.)"""
    panel, lib = rig.panel, rig.lib
    imgui.get_io().display_size = imgui.ImVec2(CONTROL_SIZE[0], 2400)
    src = lib.path_of("loadable", "DIAL")
    folder = lib.home / "loadable" / "party"
    folder.mkdir()
    src.rename(folder / "dial.json")
    st = _page(panel)
    page = st["page"]
    assert ("party/DIAL", ("rename", "×")) in page["rows"]
    assert page["rows"][-1][0] == "party/DIAL"                  # after the top level
    assert ("party", True) in page["folders"]
    assert ("party", "DIAL") in page["text"] and ("", "TUMBLE") in page["text"]
    row, ren = page["rects"]["row.party/DIAL"], page["rects"]["rename.party/DIAL"]
    head = page["rects"]["folder.party"]
    assert head[3] <= row[1] and head[0] < row[0]               # under it, indented
    assert row[0] + imgui.calc_text_size("DIAL").x < ren[0]
    _click(panel, ren)
    page_frame(panel)
    assert st["naming"] == "rename:party/DIAL" and st["buf"] == "DIAL"
    lib.rename("loadable", "party/DIAL", st["buf"] + " TWO")
    st["naming"] = None
    assert (folder / "dial-two.json").is_file() and "party/DIAL TWO" in lib.list("loadable")


def test_rename_turns_the_row_into_the_field_and_enter_renames(rig, tmp_path):  # noqa: F811
    """`rename` on a row: the row becomes the name field, seeded with the
    name; Enter renames the file (the name inside it too) and the list
    re-lists under the new name. A taken name is refused on the footer."""
    panel, lib = rig.panel, rig.lib
    lib.load("loadable", "DIAL")
    st = _page(panel)
    _click(panel, st["page"]["rects"]["rename.DIAL"])
    page_frame(panel)
    row = next(r for r in st["page"]["rows"] if r[0] == "DIAL")
    assert row == ("DIAL", ("field",)) and st["naming"] == "rename:DIAL" and st["buf"] == "DIAL"
    io = imgui.get_io()
    io.add_input_characters_utf8("DIAL TWO")                      # typed over the seeded name
    page_frame(panel)
    io.add_key_event(imgui.Key.enter, True)
    page_frame(panel)
    io.add_key_event(imgui.Key.enter, False)
    page_frame(panel)
    page_frame(panel)
    assert st["naming"] is None
    assert lib.current("loadable") == "DIAL TWO"
    assert (tmp_path / "loadable" / "dial-two.json").is_file()
    assert not (tmp_path / "loadable" / "dial.json").exists()
    assert json.loads((tmp_path / "loadable" / "dial-two.json").read_text())["name"] == "DIAL TWO"
    assert lib.status.startswith("renamed DIAL → DIAL TWO")
    names = [n for n, _ in st["page"]["rows"]]
    assert "DIAL TWO" in names and "DIAL" not in names and names == lib.list("loadable")
    # a refused rename shows on the warning line (the footer), nothing moves
    ui_loadable._rename(panel, "DIAL TWO", "TRIP")
    assert lib.warning.startswith("library: TRIP: that name is taken")
    assert lib.list("loadable").count("TRIP") == 1 and "DIAL TWO" in lib.list("loadable")


def test_the_trash_foot_shows_only_while_the_trash_holds_something_and_restores(
        rig, tmp_path):  # noqa: F811
    """"trash (n) ▸" at the list's foot only while the trash holds a file;
    its popup lists them with `restore`, which puts the file back in the
    list — and the foot goes again."""
    panel, lib = rig.panel, rig.lib
    st = _page(panel)
    assert st["page"]["foot"] == [] and "trash" not in st["page"]["rects"]
    assert lib.delete("loadable", "DIAL")
    ui_loadable.invalidate(panel, "loadable")
    page_frame(panel)
    page_frame(panel)
    assert st["page"]["foot"] == ["trash (1) ▸"]
    _click(panel, st["page"]["rects"]["trash"])
    page_frame(panel)
    view = st["trash_view"]
    assert [(g, n) for g, n, _when in view["rows"]] == [("loadable", "DIAL")]
    assert view["empty"] == "empty trash…"
    _click(panel, view["rects"]["restore.0"])
    assert lib.status == "restored DIAL" and "DIAL" in lib.list("loadable")
    assert (tmp_path / "loadable" / "dial.json").is_file() and lib.trash() == []
    page_frame(panel)
    page_frame(panel)
    assert st["page"]["foot"] == [] and "trash" not in st["page"]["rects"]
    assert "DIAL" in [n for n, _ in st["page"]["rows"]]


def test_the_list_fills_the_page_and_never_pushes_the_show_line_off(rig, monkeypatch):  # noqa: F811
    """The list is a child that takes the page's room — never shorter than
    MIN_ROWS rows, scrolling inside itself past that — so the show line
    sits under it on a short window and a tall one."""
    panel, lib = rig.panel, rig.lib
    lib.load("loadable", "TRIP")
    lib.warning = ""        # (the rig has no envelopes: the `/7`'s env ids are unknown here)
    assert len(lib.list("loadable")) == 25
    for size in ((820, 820), CONTROL_SIZE):
        imgui.get_io().display_size = imgui.ImVec2(*size)
        st = _page(panel, 3)
        rows, line = st["page"]["rects"]["rows"], st["rects"]["show.line"]
        assert rows[3] - rows[1] >= ui_loadable.MIN_ROWS * ui_loadable.list_row_h() - 1
        assert rows[3] <= line[1], size                           # the show line under the list
        assert rows[1] < rows[3] <= size[1] and line[3] <= size[1], size


def test_the_shows_row_is_never_covered(rig):  # noqa: F811
    """The layout bug the owner hit once (the startup combo over the show's
    name): the name, open ▾, save, as… and new share a row and none covers
    another; the row sits under its own line."""
    panel = rig.panel
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    rects = _page(panel, 3)["rects"]
    name, line = rects["show.name"], rects["show.line"]
    assert line[3] <= name[1] and line[0] <= name[0]
    keys = ["show.name", "show.menu", "show.save", "show.save_as", "show.new"]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            assert not _overlap(rects[a], rects[b]), (a, b)
        assert rects[a][1] < name[3] and name[1] < rects[a][3], a   # one row
    assert rects["show.new"][2] <= ui_loadable._state(panel)["page"]["rects"]["rows"][2] + 1


# ------------------------------------------------------------ the strip

def _dirty(r):
    """An edit the loaded patch does not hold: the loadable patches group (and the
    view's) is dirty."""
    reg = r.reg
    reg["view.bright"].set(reg["view.bright"].value * 0.5 + 0.1)
    assert r.lib.is_dirty("loadable")


def test_the_dots_are_clean_after_a_load(rig):  # noqa: F811
    """Plan 14 §1: right after a loadable patch loaded, no rail dot is lit and the
    show is not unsaved — every dot compares against the loaded patch or
    show. An edit brings the loadable patch's back; a meta controller move the show's."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    for name in ("TRIP", "WAKE", "BIG BLUE WAVE"):
        lib.load("loadable", name)
        groups = [g for _k, _t, grp, _b in ui_pane.SECTIONS for g in grp]
        lit = [g for g in groups if ui_loadable.dirty(panel, g)]
        assert lit == [], f"{name}: dirty dots on {lit}"
        assert not lib.install.is_dirty(), "the show is not unsaved"
    page_frame(panel, "loadable")
    reg["view.bright"].set_value(reg["view.bright"].value + 1.0)   # an edit: the dot comes back
    assert ui_loadable.dirty(panel, "view") and ui_loadable.dirty(panel, "loadable")
    assert not lib.install.is_dirty()                     # a performance move: the loadable patch's
    reg["master.gain"].set(reg["master.gain"].value + 1.0)  # a meta controller move: the show's
    assert ui_loadable.dirty(panel, "master") and lib.install.is_dirty()


def test_the_dot_is_a_twelve_pixel_disc_and_save_is_lit_while_dirty(rig):  # noqa: F811
    """Plan 19 WP5: the dot is a filled red disc 12 px across (`ui.DOT_R`),
    centred on the name's line between the name and ▶; while it shows the
    save chip is the lit one (solid red) and reads "save" — one tier, the
    only word it has. The row does not grow. Saved: the dot goes and the
    chip is quiet again."""
    panel, lib = rig.panel, rig.lib
    lib.load("loadable", "BIG BLUE WAVE")
    st = _page(panel)
    clean = dict(st["rects"])
    assert "strip.loadable.dot" not in clean
    assert st["save"]["strip.loadable"] == ("save", False)
    assert ui_loadable.save_label(lib, "loadable") == "save"
    assert ui_loadable.save_tip(lib, "loadable") == (
        "Write the settings over BIG BLUE WAVE (the old file goes to the trash)")
    _dirty(rig)
    page_frame(panel)
    page_frame(panel)
    rects = st["rects"]
    x0, y0, x1, y1 = rects["strip.loadable.dot"]
    assert x1 - x0 == y1 - y0 == 2 * ui.DOT_R == 12
    name = rects["strip.loadable.name"]
    assert abs((y0 + y1) / 2 - (name[1] + name[3]) / 2) < 0.5     # on the name's middle
    assert name[2] <= x0 and x1 <= rects["strip.loadable.next"][0]  # between the name and ▶
    assert st["save"]["strip.loadable"] == ("save", True)          # lit while dirty
    for key in ("strip.loadable.name", "strip.loadable.new", "strip.loadable.save",
                "strip.loadable.as", "show.name"):
        assert rects[key][1] == clean[key][1] and rects[key][3] == clean[key][3], key
    _click(panel, rects["strip.loadable.save"])
    assert not lib.is_dirty("loadable") and lib.status == "patch: saved BIG BLUE WAVE"
    assert [t.name for t in lib.trash()] == ["BIG BLUE WAVE"]      # the old text, kept
    page_frame(panel)
    assert "strip.loadable.dot" not in st["rects"]
    assert st["save"]["strip.loadable"] == ("save", False)
    # nothing loaded: "save", disabled, and the hover says what as… does
    lib.reland("loadable", (None, None, None))
    assert ui_loadable.save_label(lib, "loadable") == "save"
    assert ui_loadable.save_tip(lib, "loadable").startswith("No patch loaded")


def test_save_writes_over_the_loaded_loadables_own_file(rig, tmp_path):  # noqa: F811
    """Save on a loaded patch writes its own file over — the one the list
    found it by — and keeps the old text in the trash; the list still holds
    the name once. TRIP's file is `party-trip.json` (the corpus kept the
    stems the build shipped, as the owner's migrated library may): a save
    must not leave a second TRIP beside it."""
    panel, lib = rig.panel, rig.lib
    lib.load("loadable", "TRIP")
    path = lib.path_of("loadable", "TRIP")
    assert path == tmp_path / "loadable" / "party-trip.json"
    was = path.read_bytes()
    _dirty(rig)
    st = _page(panel)
    _click(panel, st["rects"]["strip.loadable.save"])
    assert not lib.is_dirty("loadable") and lib.current("loadable") == "TRIP"
    assert lib.path_of("loadable", "TRIP") == path and path.read_bytes() != was
    assert [t.name for t in lib.trash()] == ["TRIP"]
    assert lib.list("loadable").count("TRIP") == 1 and len(lib.list("loadable")) == 25
    assert sorted(p.name for p in (tmp_path / "loadable").glob("*trip*")) == ["party-trip.json"]


def test_the_loadable_strip_has_no_reset_and_does_not_overlap(rig, monkeypatch):  # noqa: F811
    """The preset strip drops `reset` (on a document kind `Library.reset`
    loads a loadable patch called "default", and none is there): at the control
    size, the longest name loaded and dirty, the strip's items — ◀ name ●
    ▶ · new · save · as… — clear one another and the page's edge."""
    panel, lib = rig.panel, rig.lib
    assert lib.default_name("loadable") is None                 # what reset would load: none
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    longest = max(lib.list("loadable"), key=lambda n: (len(n), n))
    lib.load("loadable", longest)
    lib.warning = ""        # (the rig has no envelopes: the `/7`'s env ids are unknown here)
    _dirty(rig)
    st = _page(panel, 3)
    rects = st["rects"]
    assert "strip.loadable.reset" not in rects
    assert st["save"]["strip.loadable"] == ("save", True)
    page_right = st["page"]["rects"]["rows"][2]
    items = {k: r for k, r in rects.items() if k.startswith("strip.loadable.")}
    assert set(items) == {f"strip.loadable.{k}" for k in ("name", "dot", "next", "new", "save", "as")}
    keys = sorted(items)
    for i, a in enumerate(keys):
        assert items[a][2] <= page_right + 1, a
        for b in keys[i + 1:]:
            assert not _overlap(items[a], items[b]), (a, b)
    assert not any(k.startswith("strip.") and not k.startswith("strip.loadable.") for k in rects)


@pytest.mark.parametrize("width", [258.0, 340.0, 600.0])
def test_a_module_strip_does_not_overlap(rig, monkeypatch, width):  # noqa: F811
    """Audit U10: plan 49's `strip_name_w` squeezes the name, and at 258 px the chips
    now wrap, but `same_line(avail - w)` counts from the window's edge, so at 340 px the
    save chip still covered ▶ by 6 px. Every module strip with its reset, and the
    loadable patches' strip, dirty, clear themselves and the strip's right edge: where
    it wraps, where it squeezes, and where it has room."""
    panel, lib = rig.panel, rig.lib
    monkeypatch.setattr(ui_loadable, "dirty", lambda *a, **k: True)
    groups = [g for g in lib.groups() if g not in lib.kinds and g not in RETIRED_MODULES]
    assert "view" in groups and "pattern" in groups
    modules = groups
    groups = [*modules, LOADABLE]
    imgui.new_frame()
    imgui.set_next_window_pos(imgui.ImVec2(0, 0))
    imgui.set_next_window_size(imgui.ImVec2(width + 2 * imgui.get_style().window_padding.x, 800))
    imgui.begin("strips", None, imgui.WindowFlags_.no_scrollbar)
    avail = imgui.get_content_region_avail().x
    right = imgui.get_cursor_screen_pos().x + avail
    for group in groups:
        ui_loadable.strip(panel, group)
    imgui.end()
    imgui.end_frame()
    assert avail == pytest.approx(width)
    rects = _rects(panel)
    for group in groups:
        items = {k: v for k, v in rects.items() if k.startswith(f"strip.{group}.")}
        chips = ("name", "next", "save", "as", "reset") if group in modules else ("name", "next", "new", "save", "as")
        assert {f"strip.{group}.{k}" for k in chips} <= set(items), group
        keys = sorted(items)
        for i, a in enumerate(keys):
            assert items[a][2] <= right + 1, a
            for b in keys[i + 1:]:
                assert not _overlap(items[a], items[b]), (a, b, items[a], items[b])


def test_the_strip_has_a_new_chip(rig, monkeypatch):  # noqa: F811
    """Plan 35 T7 (row 387): `new` sits before `save` on the loadable patches' strip
    and starts the blank loadable patch; `save` on the untitled loadable patch begins
    naming, since it has no file to write over."""
    from hyperspace import loadable

    panel, lib = rig.panel, rig.lib
    called = []
    monkeypatch.setattr(lib.loaded_patch, "new", lambda at: called.append(1) or [loadable.NEW_SAID])
    rects = _page(panel)["rects"]
    assert "strip.loadable.new" in rects and "strip.loadable.save" in rects
    assert rects["strip.loadable.new"][2] <= rects["strip.loadable.save"][0]
    assert [k for k in rects if k.endswith(".new") and k.startswith("strip.")] == [
        "strip.loadable.new"]
    _click(panel, rects["strip.loadable.new"])
    assert called == [1]
    monkeypatch.undo()
    lib.loaded_patch.new()
    assert lib.current("loadable") == loadable.UNTITLED_PATCH
    page_frame(panel)
    _click(panel, _rects(panel)["strip.loadable.save"])
    assert ui_loadable._state(panel)["naming"] == "loadable"


def test_new_then_save_never_writes_over_a_loadable_named_untitled(rig):  # noqa: F811
    """R17 (final review): a loadable patch named `untitled` exists; New, then
    save, opens naming (the new loadable patch is unsaved, whatever its name) and
    the file is the bytes it was; `as…` on it prefills nothing. A save
    clears the flag: save on the saved loadable patch writes over it."""
    from hyperspace import loadable

    panel, lib = rig.panel, rig.lib
    path = lib.loaded_patch.save_as(loadable.UNTITLED_PATCH)
    was = path.read_bytes()
    assert not lib.loaded_patch.unsaved
    lib.loaded_patch.new()
    assert lib.loaded_patch.unsaved and lib.path_of("loadable", loadable.UNTITLED_PATCH) == path
    _page(panel)
    _click(panel, _rects(panel)["strip.loadable.save"])
    st = ui_loadable._state(panel)
    assert st["naming"] == "loadable" and st["buf"] == ""
    assert path.read_bytes() == was
    st["naming"] = None
    page_frame(panel)
    _click(panel, _rects(panel)["strip.loadable.as"])
    assert st["naming"] == "loadable" and st["buf"] == ""
    st["naming"] = None
    lib.loaded_patch.save_as("blank")
    assert not lib.loaded_patch.unsaved
    lib.loaded_patch.new()
    lib.loaded_patch.load("blank")
    assert not lib.loaded_patch.unsaved


def test_the_routing_head_draws_save_and_as_over_the_loadables(rig):  # noqa: F811
    """ROUTING's head is the preset strip's save / as… over the same
    `presets` group (ui_routing.head): the same words, lit while dirty,
    `Library.overwrite` on a click; its as… is the strip's name field
    under the head's own key."""
    from hyperspace import ui_routing

    panel, lib = rig.panel, rig.lib
    lib.load("loadable", "BIG BLUE WAVE")
    page_frame(panel, "routing")
    page_frame(panel)
    st = ui_loadable._state(panel)
    assert st["save"]["head"] == ("save", False) and "head.save" in st["rects"]
    assert "head.dot" not in st["rects"]
    _dirty(rig)
    page_frame(panel)
    page_frame(panel)
    assert st["save"]["head"] == ("save", True) and "head.dot" in st["rects"]
    _click(panel, st["rects"]["head.save"])
    assert not lib.is_dirty("loadable") and lib.status == "patch: saved BIG BLUE WAVE"
    page_frame(panel)
    assert st["save"]["head"] == ("save", False) and "head.dot" not in st["rects"]
    ui_loadable._begin_naming(panel, ui_routing.NAMING, "Mine")
    page_frame(panel)
    ui_routing._save_as(panel, "Mine")
    st["naming"] = None
    page_frame(panel)
    assert lib.current("loadable") == "Mine" and (lib.home / "loadable" / "mine.json").is_file()


# ------------------------------------------------------------ the trash (plan 19 WP4)

def _trash_view(panel):
    st = _page(panel)
    _click(panel, st["page"]["rects"]["trash"])
    page_frame(panel)
    return st, st["trash_view"]


def test_old_trash_rows_say_so_and_nothing_to_empty_draws_no_chip(rig, monkeypatch):  # noqa: F811
    """Plan 48 review: a row from the library's old trash carries
    "patch · library" in itself; when only such rows are listed there is
    nothing "empty" would remove, so no chip to arm."""
    from hyperspace.library import Trashed
    panel, lib = rig.panel, rig.lib
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    old = Trashed(lib.home / "trash" / "loadable" / "gone.20261001-120000.json", "loadable",
                  "GONE", "Oct 1 12:00", "", True)
    monkeypatch.setattr(lib, "trash", lambda: [old])
    ui_loadable.invalidate(panel, "loadable")
    _st, view = _trash_view(panel)
    assert view["rows"] == [("loadable", "GONE", "Oct 1 12:00")]
    assert view["tags"] == ["patch · library"] and view["old"] == 1
    assert view["empty"] is None and "empty" not in view["rects"]


def test_empty_asks_once_and_disarms(rig, tmp_path):  # noqa: F811
    """"empty trash…" asks once, in place, no modal: one click arms it —
    "delete N files for good? — click again" — and empties nothing; a
    second click within four seconds empties. The time running out, any
    other click, or the popup closing disarms it. Real clicks on the trash
    popup, opened from the list's foot."""
    panel, lib = rig.panel, rig.lib
    io = imgui.get_io()
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)

    def fill():
        lib.load("loadable", "TRIP")
        lib.save_as("loadable", "A MINE")
        lib.delete("loadable", "A MINE")
        ui_loadable.invalidate(panel, "loadable")

    fill()
    st, view = _trash_view(panel)
    assert view["rows"] and view["empty"] == "empty trash…"
    files = [t.path for t in lib.trash()]
    _click(panel, view["rects"]["empty"])
    view = st["trash_view"]
    assert view["empty"] == "delete 1 file for good? — click again"
    assert all(p.exists() for p in files)                     # one click empties nothing
    # the time runs out
    io.delta_time = ui_loadable.EMPTY_S + 0.5
    page_frame(panel)
    io.delta_time = 1 / 60
    page_frame(panel)
    assert st["trash_view"]["empty"] == "empty trash…"
    _click(panel, st["trash_view"]["rects"]["empty"])         # armed again, not emptied
    assert all(p.exists() for p in files)
    # any other click disarms (the popup's own header, nothing there)
    rows = st["trash_view"]["rects"]["rows"]
    _click(panel, (rows[0], rows[1] - 18, rows[0] + 40, rows[1] - 6))
    assert st["trash_view"]["empty"] == "empty trash…" and all(p.exists() for p in files)
    # closing the popup disarms
    _click(panel, st["trash_view"]["rects"]["empty"])
    assert st["trash_view"]["empty"].startswith("delete 1 file")
    io.add_key_event(imgui.Key.escape, True)
    page_frame(panel)
    io.add_key_event(imgui.Key.escape, False)
    page_frame(panel)
    _click(panel, (5, 5, 6, 6))                               # outside the popup
    page_frame(panel)
    assert st.get("empty_armed") is None
    st, view = _trash_view(panel)
    assert view["empty"] == "empty trash…"
    # two clicks within the time: emptied
    _click(panel, view["rects"]["empty"])
    _click(panel, st["trash_view"]["rects"]["empty"])
    assert not any(p.exists() for p in files) and lib.trash() == []
    assert lib.status == "trash: 1 file deleted for good"
    page_frame(panel)
    page_frame(panel)
    assert st["page"]["foot"] == []


def test_the_page_does_not_reread_the_library_every_frame(rig, monkeypatch):  # noqa: F811
    """The list costs what is on the poll cadence, not a pass over the
    library per row per frame (the owner's 79-preset cloud library once
    drew at 25 fps with the list open): ten frames of the page re-index
    the library at most a few times, however many rows it draws."""
    panel = rig.panel
    st = _page(panel)
    assert len(st["page"]["rows"]) > ui_loadable.LIST_ROWS
    calls = []
    real = Library._index

    def counted(self, group):
        calls.append(group)
        return real(self, group)

    monkeypatch.setattr(Library, "_index", counted)
    for _ in range(10):
        page_frame(panel)
    assert len(st["page"]["rows"]) > ui_loadable.LIST_ROWS
    assert len(calls) <= 3, f"{len(calls)} library index passes in 10 frames"


# ------------------------------------------------------------ the patches fold (plan 40 T3)

def test_the_patches_fold_lists_patches_with_rename_and_cross_and_no_pick(
        rig, monkeypatch):  # noqa: F811
    """The **patches** fold: every patch, each a row of the preset list's
    own — rename and × (to the trash) on each, one tier. A pick loads
    nothing: a patch is spawned on GRAPH."""
    panel, lib = rig.panel, rig.lib
    (lib.home / PATCHES).mkdir(parents=True, exist_ok=True)
    (lib.home / PATCHES / "acid-wash.json").write_text(ACID_WASH.read_text())
    mine = json.loads(ACID_WASH.read_text())
    mine["name"] = "my wash"
    (lib.home / PATCHES / "my-wash.json").write_text(json.dumps(mine))
    _open_patches(monkeypatch)
    real_chip, real_selectable = ui.chip, imgui.selectable
    loads = []
    monkeypatch.setattr(lib, "load", lambda *a, **k: loads.append(a))
    monkeypatch.setattr(imgui, "selectable", lambda label, *a, **k: (
        (True, True) if label == "my wash##pick" else real_selectable(label, *a, **k)))
    page_frame(panel, "loadable")
    drawn = ui_loadable._state(panel)["patches"]
    assert drawn["group"] == PATCHES and drawn["foot"] == []
    assert drawn["rows"] == [("acid wash", ("rename", "×")), ("my wash", ("rename", "×"))]
    assert loads == []                                     # a pick loads nothing
    assert {"row.acid wash", "rename.acid wash", "×.acid wash"} <= set(drawn["rects"])
    # × on a patch: to the trash (restorable)
    trashed = len(lib.trash())
    monkeypatch.setattr(ui, "chip", lambda label, *a, **k: (
        label == "×##×.acid wash" or real_chip(label, *a, **k)))
    page_frame(panel)
    assert lib.list(PATCHES) == ["my wash"]
    assert not (lib.home / PATCHES / "acid-wash.json").exists()
    assert len(lib.trash()) == trashed + 1 and lib.trash()[0].group == PATCHES
    # rename: the row becomes the name field under the patch's own key
    monkeypatch.setattr(ui, "chip", lambda label, *a, **k: (
        label == "rename##rename.my wash" or real_chip(label, *a, **k)))
    page_frame(panel)
    st = ui_loadable._state(panel)
    assert st["naming"] == f"rename:{PATCHES}:my wash" and st["buf"] == "my wash"
    monkeypatch.setattr(ui, "chip", real_chip)
    page_frame(panel)
    assert st["patches"]["rows"] == [("my wash", ("field",))]
    ui_loadable._rename(panel, "my wash", "their wash", PATCHES)
    st["naming"] = None
    page_frame(panel)
    assert st["patches"]["rows"] == [("their wash", ("rename", "×"))]
    assert lib.list(PATCHES) == ["their wash"]
    assert (lib.home / PATCHES / "their-wash.json").is_file()


# ------------------------------------------------------------ the show line

def test_the_show_line_names_the_show_and_its_dot(rig, monkeypatch):  # noqa: F811
    """One line says what a show is; then its name in the readout face and
    a red ● only while it differs from its file."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    texts, _ = _drawn(monkeypatch)
    st = _page(panel)
    assert ui_loadable.SHOW_LINE.upper() in texts and "party" in texts
    assert "●" not in texts and "show.dot" not in st["rects"]
    assert not lib.install.is_dirty()
    reg["master.gain"].set(reg["master.gain"].value + 1.0)      # a meta controller move
    texts.clear()
    page_frame(panel)
    assert lib.install.is_dirty() and "●" in texts and "show.dot" in st["rects"]
    name, dot = st["rects"]["show.name"], st["rects"]["show.dot"]
    assert name[2] <= dot[0] and not _overlap(name, dot)


def test_open_lists_the_librarys_shows_and_picks_one(rig, monkeypatch):  # noqa: F811
    """The open ▾ combo lists `Install.list()` — the library's shows — and
    a pick opens that show with its startup loadable patch."""
    panel, lib = rig.panel, rig.lib
    assert lib.install.list() == ["house", "party"]
    st = _page(panel)
    assert lib.install.name == "party" and lib.current("loadable") is None
    seen: list[str] = []
    real = imgui.selectable
    monkeypatch.setattr(imgui, "selectable", lambda label, *a, **k: (
        seen.append(label), real(label, *a, **k))[1])
    _click(panel, st["rects"]["show.menu"])                      # the combo opens
    seen.clear()
    page_frame(panel)
    assert [s for s in seen if "##" not in s] == ["house", "party"]
    monkeypatch.setattr(imgui, "selectable", lambda label, *a, **k: (
        (True, True) if label == "house" else real(label, *a, **k)))
    page_frame(panel)
    assert lib.install.name == "house" and lib.install.stem == "house"
    assert lib.current("loadable") == "BIG BLUE WAVE"             # the house show's startup
    assert lib.install.bank[0] == "BIG BLUE WAVE" and not lib.install.is_dirty()


def test_save_as_and_new_work_the_show(rig, tmp_path):  # noqa: F811
    """save writes the show's file; as… is the name field under the show's
    key, and its commit writes under the new name; new starts an unsaved
    `untitled` show with every pad empty and nothing to start on."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    proj = lib.install
    show = tmp_path / "installs" / "party.json"
    st = _page(panel)
    reg["master.gain"].set(reg["master.gain"].value + 1.0)
    assert proj.is_dirty()
    _click(panel, st["rects"]["show.save"])
    assert not proj.is_dirty() and lib.status == "install: saved party"
    assert json.loads(show.read_text())["tuning"]["master.gain"] == reg["master.gain"].value
    _click(panel, st["rects"]["show.save_as"])
    assert st["naming"] == ui_loadable.PROJECT and st["buf"] == "party"
    page_frame(panel)                                              # the field stands in for the row
    ui_loadable._project_save_as(panel, "FRIDAY")
    st["naming"] = None
    page_frame(panel)
    assert proj.name == "FRIDAY" and proj.path == tmp_path / "installs" / "friday.json"
    assert proj.path.is_file() and not proj.is_dirty()
    assert ui_loadable.names(panel, ui_loadable.PROJECT) == ["friday", "house", "party"]
    assert (tmp_path / "last_install").read_text() == "friday\n"
    _click(panel, st["rects"]["show.new"])
    assert proj.name == "untitled" and proj.path is None and proj.is_dirty()
    assert proj.bank == [None] * 24 and proj.startup is None
    page_frame(panel)
    page_frame(panel)
    assert "show.dot" in st["rects"]                             # unsaved: the dot


# ------------------------------------------------------------ the page's words

def test_nothing_on_the_page_says_starts_on_f_keys_hidden_or_factory(rig, monkeypatch):  # noqa: F811
    """The owner's ask, 2026-10-28: no "starts on", no F-key, no hidden, no
    factory, no slot — in any text the page draws, any hover, any widget
    label, any rect key — with a loadable patch loaded, the trash holding a file,
    a patch in its fold and the show line drawn. The page says show and
    loadable patch, never project or startup."""
    panel, lib = rig.panel, rig.lib
    lib.load("loadable", "TRIP")
    lib.delete("loadable", "DIAL")
    ui_loadable.invalidate(panel, "loadable")
    (lib.home / PATCHES).mkdir(parents=True, exist_ok=True)
    (lib.home / PATCHES / "acid-wash.json").write_text(ACID_WASH.read_text())
    _open_patches(monkeypatch)
    texts, previews = _drawn(monkeypatch)
    got = _labels(monkeypatch)
    tips: list[str] = []
    monkeypatch.setattr(ui, "tooltip", tips.append)
    monkeypatch.setattr(imgui, "is_item_hovered", lambda *a: True)
    st = _page(panel, 3)
    assert st["page"]["foot"] == ["trash (1) ▸"] and st["patches"]["rows"]
    words = [*texts, *previews, *tips, *got["hint"], *got["header"],
             *(label.split("##")[0] for label in got["button"]),
             *(label.split("##")[0] for label, _ in got["selectable"]),
             *st["rects"], *st["page"]["rects"], *st["patches"]["rects"]]
    assert len(words) > 40 and "TRIP" in words and "party" in words
    said = "\n".join(words).lower()
    assert re.search(BANNED, said) is None, re.search(BANNED, said)
    assert "show" in said and "preset" in said and "trash" in said and "patches" in said


# ------------------------------------------------------------ the footer's library lines

def test_the_footer_says_a_library_line_again(rig, monkeypatch):  # noqa: F811
    """Plan 15 WP4: the footer's slot shows a library line when its words
    change — and, for a line set through `Library.say`, when it is said
    again in the same words: a save-as that meets a full bank twice, a
    pad cleared, refilled and cleared again."""
    panel, lib = rig.panel, rig.lib
    proj = lib.install
    clock = [1000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    page_frame(panel, "view")                                      # the first look only remembers
    assert panel._message() == ("", False)
    proj.clear_slot(5)
    said = lib.status
    assert said == "F6: cleared — ACID is still in the patch list"
    assert panel._message() == (said, False)
    clock[0] += ui.MESSAGE_S + 1
    assert panel._message() == ("", False)                    # …and it goes
    proj.bank[5] = "ACID"                                     # (not through the desk: no line)
    proj.clear_slot(5)
    assert lib.status == said and panel._message() == (said, False)   # the same words, shown again
    # a warning said again shows again, and an old warning is not dragged
    # back by a later status
    clock[0] += ui.MESSAGE_S + 1
    lib.say(warning="saved TRIP 9 — the bank is full: it is in the patch list")
    assert panel._message() == (lib.warning, True)
    clock[0] += ui.MESSAGE_S + 1
    lib.say(warning=lib.warning)
    assert panel._message() == (lib.warning, True)
    clock[0] += ui.MESSAGE_S + 1
    lib.say("show: something else")
    assert panel._message() == ("show: something else", False)
    # a plain assignment of the same words stays quiet, as before
    clock[0] += ui.MESSAGE_S + 1
    lib.status = "show: something else"
    assert panel._message() == ("", False)
    # a panel kept across a hot reload remembers the lines as plain strings:
    # they are not news (review of PR #87)
    panel._msg["seen"] = {"status": lib.status, "warning": lib.warning,
                          "undo": panel._msg["seen"]["undo"]}
    assert lib.warning and panel._message() == ("", False)
    lib.say("show: after the reload")
    assert panel._message() == ("show: after the reload", False)


def test_a_line_said_twice_shows_twice(rig, monkeypatch):  # noqa: F811
    """Plan 16 WP7: every line that reports something that just happened
    goes through `Library.say`, so the same press giving the same words
    shows them again — an empty F-key, home on a show that names no
    startup loadable patch, a pad naming no file, a show saved twice."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    proj = lib.install
    clock = [1000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    page_frame(panel, "view")                                      # the first look only remembers
    assert panel._message() == ("", False)
    proj.bank[2] = None
    empty = "F3: an empty slot — hold its pad (or ⇧F3) to save the live state into it"
    proj.startup = None
    for trigger, line in (("preset.load.2", empty), ("preset.home", HOME_UNSET)):
        for _ in range(2):                                    # the second press too
            clock[0] += ui.MESSAGE_S + 1
            assert panel._message() == ("", False)
            reg[trigger].fire()
            assert lib.warning == line and panel._message() == (line, True), trigger
    proj.bank[3] = "GONE"                                     # a pad naming no file
    for _ in range(2):
        clock[0] += ui.MESSAGE_S + 1
        assert panel._message() == ("", False)
        reg["preset.load.3"].fire()
        assert panel._message() == ("F4: no patch 'GONE'", True)
    for _ in range(2):                                        # a status as well
        clock[0] += ui.MESSAGE_S + 1
        assert panel._message() == ("", False)
        proj.save("MINE")
        assert panel._message() == ("install: saved MINE", False)


def test_a_line_assigned_every_frame_does_not_pin_the_footer(rig, monkeypatch):  # noqa: F811
    """…and nothing holds the slot open: a line assigned in the same words
    every frame is not said again (only `say` counts), and a panel left
    alone, drawing every page in turn, says nothing at all."""
    panel, lib = rig.panel, rig.lib
    clock = [1000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    frame(panel, "view")
    lib.say(warning=HOME_UNSET)
    said = dict(lib.said)
    shown = []
    for k in range(60):                                       # six seconds at 10 fps
        clock[0] += 0.1
        lib.warning = HOME_UNSET                              # the same words, every frame
        lib.status = "show: party"
        frame(panel, PAGE_KEYS[k % len(PAGE_KEYS)])                # every page's own code runs
        shown.append(panel._message()[0])
    assert shown[0] == HOME_UNSET and shown[-1] == "" and lib.said == said
    assert "" in shown and all(s == "" for s in shown[shown.index(""):])
    assert abs(shown.index("") * 0.1 - ui.MESSAGE_S) < 0.25   # gone on time
    # a knob on `scene.select` sends the same scene many times in one turn:
    # said once, when it changes, and never again while it is the same
    # (review of PR #92)
    scene = rig.reg["scene.select"]
    panel.control.library = lib                               # as app.py wires it
    clock[0] += ui.MESSAGE_S + 1
    scene.set(1)
    line = lib.status
    assert line.startswith("analyzer: ") and panel._message() == (line, False)
    said = dict(lib.said)
    lib.say(warning=HOME_UNSET)                               # news, a frame later
    seen = []
    for _ in range(50):
        scene.set(1)
        assert lib.status == line
        seen.append(panel._message()[0])
        clock[0] += 0.1
    # the warning kept the slot for its four seconds, then nothing
    assert seen[0] == HOME_UNSET and set(seen) == {HOME_UNSET, ""} and seen[-1] == ""
    assert lib.said["status"] == said["status"]
    scene.set(2)
    assert lib.status != line and panel._message() == (lib.status, False)


# ---- the list on the kit: a search, and a row's actions shown on its hover ----

def test_the_search_lists_the_patches_that_have_the_letters_flat(rig):  # noqa: F811
    """A few letters, from a name or its folder: the list is the patches that
    have them, flat, each with its folder; none, and the list says so."""
    panel, lib = rig.panel, rig.lib
    folder = lib.home / "loadable" / "party"
    folder.mkdir()
    lib.path_of("loadable", "DIAL").rename(folder / "dial.json")
    st = _page(panel)
    every = [n for n, _ in st["page"]["rows"]]
    assert "party/DIAL" in every and len(every) == 25
    st["find"] = "wav"
    page_frame(panel)
    found = [n for n, _ in st["page"]["rows"]]
    assert found == [n for n in lib.list("loadable") if "wav" in n.casefold()] and found
    st["find"] = "PARTY"                            # its folder's letters, either case
    page_frame(panel)
    assert [n for n, _ in st["page"]["rows"]] == ["party/DIAL"]
    assert ("party", "DIAL") in st["page"]["text"]                 # flat: its folder said
    assert st["page"]["folders"] == []                             # no headers while searching
    st["find"] = "zzz"
    page_frame(panel)
    assert st["page"]["rows"] == []
    st["find"] = ""
    page_frame(panel)
    assert [n for n, _ in st["page"]["rows"]] == every


@pytest.mark.skipif(not ui_kit.enabled(), reason="the kit is switched off (HYPERSPACE_KIT=0)")
def test_a_rows_actions_show_on_its_hover_and_take_a_click_unseen(rig):  # noqa: F811
    """On the kit a row's `rename` and × are icons shown while the row is
    hovered — twenty-five rows are not fifty chips — eased in, and gone
    again when the pointer leaves; and a click on where one is takes it
    whether it shows yet or not (the driver's click, a quick pointer)."""
    panel, lib = rig.panel, rig.lib
    st = _page(panel)
    assert ui_kit.ready()
    anim = panel.__dict__[ui_kit.STATE]["ui"].anim      # the panel's kit state (ui_kit.begin)

    def reveal(name: str) -> float:
        return anim._t[f"row:{name}:reveal"].value

    assert reveal("DIAL") == 0.0 and reveal("ACID") == 0.0        # at rest: hidden
    x0, y0, x1, y1 = st["page"]["rects"]["row.DIAL"]
    io = imgui.get_io()
    io.add_mouse_pos_event(x0 + 20, (y0 + y1) / 2)
    for _ in range(20):                                            # past the 150 ms ease
        page_frame(panel)
    assert reveal("DIAL") == pytest.approx(1.0) and reveal("ACID") == 0.0
    io.add_mouse_pos_event(-1.0, -1.0)
    for _ in range(20):
        page_frame(panel)
    assert reveal("DIAL") == pytest.approx(0.0)
    _click(panel, st["page"]["rects"]["×.DIAL"])                   # unseen, still there
    assert "DIAL" not in lib.list("loadable")
