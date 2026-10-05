"""Plan 14 WP4: the PRESETS page for a party — headless imgui over the
controls rig (tests/test_ui_shell.py), on a fresh home, which opens the
factory party show (decision 22).

Top to bottom: the show's name on its own line, never covered; show ▾ ·
save · save as · new; "starts on ▾", saved when set; eight preset buttons
carrying their presets' names; the preset strip; "more" folded. The dirty
dots compare against the loaded preset or show, so a factory load is clean.
"""

import json

from imgui_bundle import imgui
from test_ui_routing import _drawn
from test_ui_shell import _page_scroll, frame, rig  # noqa: F401 — the fixture

from hyperspace import ui_presets
from hyperspace.library import HOME_UNSET, Library
from hyperspace.ui import PAGES


def _overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _rects(panel):
    return dict(ui_presets._state(panel)["rects"])


def test_the_shows_name_is_never_covered(rig, tmp_path):  # noqa: F811
    """The layout bug the owner hit: the startup combo drew over the
    project's name, so only "de" of "default" showed. The name has its line
    to itself; no widget on the page overlaps it; it fits the line — a long
    name too."""
    panel, lib = rig.panel, rig.lib
    for name in (None, "FRIDAY NIGHT AT THE WAREHOUSE"):
        if name:
            ui_presets._project_save_as(panel, name)
        frame(panel, "presets")
        frame(panel)
        rects = _rects(panel)
        shown = rects["show.name"]
        assert shown[2] - shown[0] >= imgui.calc_text_size("x").x * len(lib.project.name) * 0.5
        line = rects["show.line"]
        assert line[0] <= shown[0] and shown[2] <= line[2], "the name runs off its line"
        others = {k: r for k, r in rects.items()
                  if k not in ("show.name", "show.line", "show.dot")}
        assert {"show.menu", "show.save", "show.save_as", "show.new", "starts_on",
                "starts_on.label", "preset.0", "preset.7"} <= set(others)
        hit = [k for k, r in others.items() if _overlap(shown, r)]
        assert hit == [], f"covering the show's name: {hit}"
        # and the widgets below never overlap one another
        keys = sorted(others)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                assert not _overlap(others[a], others[b]), (a, b)


def test_the_preset_buttons_carry_their_presets_names(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    lib.load("presets", "FACES")
    frame(panel, "presets")
    frame(panel)
    labels = ui_presets._state(panel)["bank_labels"]
    assert labels == ["F1  TUMBLE", "F2  FACES", "F3  FIELD", "F4  WAKE", "F5  TRIP",
                      "F6  ACID", "F7  MANDALA", "F8  NOITA"] and len(labels) == 8   # plan 14 WP5 filled F6–F8
    assert lib.project.active == 1                          # FACES, lit
    rects = _rects(panel)
    assert rects["preset.2"][1] > rects["preset.0"][1]       # F3 F4 under F1 F2
    assert rects["preset.2"][0] == rects["preset.0"][0] < rects["preset.1"][0]


def test_a_long_preset_name_is_elided_to_its_button(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    lib.project.bank[5] = "A PRESET NAME FAR TOO LONG FOR ONE BUTTON"
    frame(panel, "presets")
    frame(panel)
    label = ui_presets._state(panel)["bank_labels"][5]
    assert label.startswith("F6  A PRESET NAME") and label.endswith("…")


def test_the_dots_are_clean_after_a_factory_load(rig):  # noqa: F811
    """Plan 14 §1: right after a factory preset loaded, the rail lit dots on
    VIEW / CAMERA / LOOKBACK / FX / LFO (they compared against fresh
    defaults) and the footer said the factory show was unsaved. Now every
    dot compares against the loaded preset or show."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    for name in ("TRIP", "WAKE", "BIG BLUE WAVE"):
        lib.load("presets", name)
        groups = [g for _k, _l, grp in PAGES
                  for g in ((grp,) if isinstance(grp, str) else (grp or ()))]
        lit = [g for g in groups if ui_presets.dirty(panel, g)]
        assert lit == [], f"{name}: dirty dots on {lit}"
        assert not lib.project.is_dirty(), "the factory show is not unsaved"
    frame(panel, "presets")
    reg["view.bright"].set_value(reg["view.bright"].value + 1.0)   # an edit: the dot comes back
    assert ui_presets.dirty(panel, "view") and ui_presets.dirty(panel, "presets")
    assert not lib.project.is_dirty()                     # a performance move: the preset's
    reg["master.gain"].set(reg["master.gain"].value + 1.0)  # a session move: the show's
    assert ui_presets.dirty(panel, "master") and lib.project.is_dirty()


def test_starts_on_is_labelled_and_saved_when_set(rig, tmp_path, monkeypatch):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    texts, previews = _drawn(monkeypatch)
    frame(panel, "presets")
    frame(panel)
    assert "STARTS ON / HOME" in texts and "TUMBLE" in previews
    ui_presets.set_starts_on(panel, "WAKE")
    path = tmp_path / "projects" / "party.hyp.json"          # the factory show: your copy
    doc = json.loads(path.read_text())
    assert doc["startup"] == "WAKE" and doc["name"] == "party"
    assert not lib.project.is_dirty() and lib.project.path == path
    assert (tmp_path / "last_show").read_text() == "party\n"
    again = Library(tmp_path, period=0.0)
    assert again.project.name == "party" and again.project.startup == "WAKE"


def test_starts_on_reads_starts_on_home(rig, monkeypatch):  # noqa: F811
    """Plan 15 WP2 (decision 27): home is what the show starts on, so the
    label says both and its tooltip names the two controls that go there.
    No widget was added: the row is still one label and one combo, the
    combo has room for a preset's name, and the page does not scroll."""
    panel, lib = rig.panel, rig.lib
    texts, previews = _drawn(monkeypatch)
    tips: list[str] = []
    monkeypatch.setattr(imgui, "is_item_hovered", lambda *a: True)
    monkeypatch.setattr(imgui, "set_tooltip", tips.append)
    frame(panel, "presets")
    frame(panel)
    assert "STARTS ON / HOME" in texts and "STARTS ON" not in texts
    assert lib.project.startup == "TUMBLE" and "TUMBLE" in previews
    (tip,) = {t for t in tips if t.startswith("starts on")}
    assert tip.startswith("starts on: TUMBLE") and "Home (fn ←)" in tip
    assert "OVERDUB, B11 on the desk, loads it" in tip
    rects = _rects(panel)
    label, combo = rects["starts_on.label"], rects["starts_on"]
    assert not _overlap(label, combo) and label[1] < combo[3] and combo[1] < label[3]   # one row
    longest = max(ui_presets.names(panel, "presets"), key=len)
    assert combo[2] - combo[0] > imgui.calc_text_size(longest).x
    assert [k for k in rects if k.startswith("starts_on")] == ["starts_on.label", "starts_on"]
    # home on a show with no "starts on" asks for one to be picked here;
    # picking one takes the note away (review of PR #83), and no other note
    ui_presets.set_starts_on(panel, None)
    rig.reg["preset.home"].fire()
    assert lib.warning == HOME_UNSET
    ui_presets.set_starts_on(panel, None)
    assert lib.warning == HOME_UNSET
    ui_presets.set_starts_on(panel, "WAKE")
    assert lib.warning == "" and lib.project.startup == "WAKE"
    lib.warning = "something else"
    ui_presets.set_starts_on(panel, "TUMBLE")
    assert lib.warning == "something else"


def test_the_page_speaks_one_word_per_thing(rig, monkeypatch):  # noqa: F811
    """Plan 14 §3: show, preset, starts on, module preset, factory — the
    page never says project or startup."""
    panel = rig.panel
    texts, previews = _drawn(monkeypatch)
    frame(panel, "presets")
    frame(panel)
    words = " ".join(texts + previews).lower()
    assert "show" in words and "starts on" in words and "factory" in words
    assert "project" not in words and "startup" not in words
    # "more" is folded: no module strip drawn until it is opened
    assert not any(t.startswith("view ") for t in texts)


def test_more_opened_holds_a_strip_per_module_and_still_fits(rig, monkeypatch):  # noqa: F811
    real = imgui.collapsing_header
    monkeypatch.setattr(imgui, "collapsing_header",
                        lambda label, *a: (real(label, *a), True)[1] if "more" in label
                        else real(label, *a))
    texts, _ = _drawn(monkeypatch)
    frame(rig.panel, "presets")
    frame(rig.panel)
    groups = ui_presets.groups(rig.panel)
    assert {"view", "camera", "fx", "band"} <= set(groups)
    assert all(f"{g:<8s}" in texts for g in groups)
    assert _page_scroll(rig, monkeypatch)["presets"] == 0


# ------------------------------------------- plan 15 WP4: a slot's own menu

def _mouse(panel, x, y, button=None, down=False):
    """One frame with the mouse at (x, y), a button going down or up."""
    io = imgui.get_io()
    io.add_mouse_pos_event(x, y)
    if button is not None:
        io.add_mouse_button_event(button, down)
    frame(panel)


def _click(panel, rect, button=0):
    x, y = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    _mouse(panel, x, y)
    _mouse(panel, x, y, button, True)
    _mouse(panel, x, y, button, False)
    frame(panel)


def test_a_slots_menu_offers_put_and_clear(rig, tmp_path):  # noqa: F811
    """Plan 15 WP4: a right-click on a bank slot adds two items to its
    menu, under the param's own: "put preset here…", a list of every
    preset no taller than twelve rows, and "clear slot", disabled on an
    empty slot. Each writes the show at once and deletes no file."""
    panel, lib = rig.panel, rig.lib
    proj = lib.project
    show = tmp_path / "projects" / "party.hyp.json"
    frame(panel, "presets")
    frame(panel)
    st = ui_presets._state(panel)
    assert "slot_menu" not in st                              # no menu until it is opened
    files = sorted(p.name for p in (tmp_path / "presets").glob("*.json")) \
        if (tmp_path / "presets").is_dir() else []
    # slot 6 (F6, ACID): open its menu
    _click(panel, st["rects"]["preset.5"], button=1)
    menu = st["slot_menu"]
    assert menu["slot"] == 5
    assert menu["items"] == [("put preset here…", True), ("clear slot", True)]
    # clear slot: the bank and the show's file, and ACID is still a preset
    _click(panel, menu["rects"]["clear"])
    assert proj.bank[5] is None and json.loads(show.read_text())["bank"][5] is None
    assert "ACID" in lib.list("presets") and lib.status.startswith("F6: cleared")
    assert ui_presets._state(panel)["bank_labels"][5] == "F6  —"
    # on the empty slot "clear slot" is disabled, and clicking it does nothing
    st.pop("slot_menu")
    _click(panel, st["rects"]["preset.5"], button=1)
    menu = st["slot_menu"]
    assert menu["items"] == [("put preset here…", True), ("clear slot", False)]
    before = show.read_text()
    _click(panel, menu["rects"]["clear"])
    assert show.read_text() == before and proj.bank[5] is None
    # put preset here…: the list is every preset, in a child at most twelve rows tall
    st.pop("slot_menu", None)
    _click(panel, st["rects"]["preset.5"], button=1)
    _click(panel, st["slot_menu"]["rects"]["put"])
    menu = st["slot_menu"]
    listing = lib.list("presets")
    assert menu["names"] == listing and len(listing) > ui_presets.PUT_ROWS
    box = menu["rects"]["list"]
    row = imgui.get_text_line_height_with_spacing()
    assert box[3] - box[1] <= ui_presets.PUT_ROWS * row + 1
    assert box[2] - box[0] > max(imgui.calc_text_size(n).x for n in listing)
    pick = listing[2]
    _click(panel, menu["rects"][f"name.{pick}"])
    assert proj.bank[5] == pick and json.loads(show.read_text())["bank"][5] == pick
    assert lib.status == f"F6: {pick}"
    # the menu closed on the pick, and nothing in the preset folder moved
    st.pop("slot_menu")
    frame(panel)
    frame(panel)
    assert "slot_menu" not in st
    now = sorted(p.name for p in (tmp_path / "presets").glob("*.json")) \
        if (tmp_path / "presets").is_dir() else []
    assert now == files and not (tmp_path / "trash").exists()


def test_the_footer_says_a_library_line_again(rig, monkeypatch):  # noqa: F811
    """Plan 15 WP4: the footer's slot shows a library line when its words
    change — and, for a line set through `Library.say`, when it is said
    again in the same words: a save-as that meets a full bank twice, a
    slot cleared, refilled and cleared again."""
    from hyperspace import ui

    panel, lib = rig.panel, rig.lib
    proj = lib.project
    clock = [1000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    frame(panel, "view")                                      # the first look only remembers
    assert panel._message() == ("", False)
    proj.clear_slot(5)
    said = lib.status
    assert said == "F6: cleared — ACID is still in the preset list"
    assert panel._message() == (said, False)
    clock[0] += ui.MESSAGE_S + 1
    assert panel._message() == ("", False)                    # …and it goes
    proj.bank[5] = "ACID"                                     # (not through the menu: no line)
    proj.clear_slot(5)
    assert lib.status == said and panel._message() == (said, False)   # the same words, shown again
    # a warning said again shows again, and an old warning is not dragged
    # back by a later status
    clock[0] += ui.MESSAGE_S + 1
    lib.say(warning="saved TRIP 9 — the bank is full: it is in the preset list")
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
