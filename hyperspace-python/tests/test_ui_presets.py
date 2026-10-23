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
from test_ui_shell import CONTROL_SIZE, _page_scroll, frame, rig  # noqa: F401 — the fixture

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
    assert labels[:8] == ["F1  TUMBLE", "F2  FACES", "F3  FIELD", "F4  WAKE", "F5  TRIP",
                          "F6  ACID", "F7  MANDALA", "F8  NOITA"]   # plan 14 WP5 filled F6–F8
    # plan 19 WP1: the far slots under them, by number
    assert labels[8:] == ["9 TRACER", *[f"{k} —" for k in range(10, 25)]]
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
    # at the control size from the first frame: the panel takes its height
    # once (`Cond_.once`), and the rig's 820 px display is 80 px shorter
    # than the control window the rule is about (plan 19 WP1)
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
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
    assert menu["items"] == [("put preset here…", True), ("free this pad (keeps the preset)", True)]
    # clear slot: the bank and the show's file, and ACID is still a preset
    _click(panel, menu["rects"]["clear"])
    assert proj.bank[5] is None and json.loads(show.read_text())["bank"][5] is None
    assert "ACID" in lib.list("presets") and lib.status.startswith("F6: cleared")
    assert ui_presets._state(panel)["bank_labels"][5] == "F6  —"
    # on the empty slot "clear slot" is disabled, and clicking it does nothing
    st.pop("slot_menu")
    _click(panel, st["rects"]["preset.5"], button=1)
    menu = st["slot_menu"]
    assert menu["items"] == [("put preset here…", True), ("free this pad (keeps the preset)", False)]
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
    "starts on", a slot naming no file, a show saved twice."""
    from hyperspace import ui

    panel, lib, reg = rig.panel, rig.lib, rig.reg
    proj = lib.project
    clock = [1000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    frame(panel, "view")                                      # the first look only remembers
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
    proj.bank[3] = "GONE"                                     # a slot naming no file
    for _ in range(2):
        clock[0] += ui.MESSAGE_S + 1
        assert panel._message() == ("", False)
        reg["preset.load.3"].fire()
        assert panel._message() == ("F4: no preset 'GONE'", True)
    for _ in range(2):                                        # a status as well
        clock[0] += ui.MESSAGE_S + 1
        assert panel._message() == ("", False)
        proj.save("MINE")
        assert panel._message() == ("show: saved MINE", False)


def test_a_line_assigned_every_frame_does_not_pin_the_footer(rig, monkeypatch):  # noqa: F811
    """…and nothing holds the slot open: a line assigned in the same words
    every frame is not said again (only `say` counts), and a panel left
    alone, drawing every page in turn, says nothing at all."""
    from hyperspace import ui

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
        frame(panel, PAGES[k % len(PAGES)][0])                # every page's own code runs
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
    assert line.startswith("band: ") and panel._message() == (line, False)
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


# ------------------------------------------- plan 19 WP1: twenty-four slots (layout B)

def _open_more(monkeypatch):
    real = imgui.collapsing_header
    monkeypatch.setattr(imgui, "collapsing_header",
                        lambda label, *a: (real(label, *a), True)[1] if "more" in label
                        else real(label, *a))


def test_twenty_four_slots_fit_the_page_with_more_open(rig, monkeypatch):  # noqa: F811
    """No page scrolls at the control size — the PRESETS page with all
    twenty-four slots filled (the longest factory names first), a preset
    loaded so the status line is drawn, and "more" open. Layout B: F1–F8
    two a row, then 9–24 four a row, their rows FAR_GAP apart; no slot
    overlaps another and every one is inside the page."""
    panel, lib = rig.panel, rig.lib
    pr = lib.project
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    _open_more(monkeypatch)
    names = sorted(lib.list("presets"), key=lambda n: (-len(n), n))
    pr.bank[:] = [names[k % len(names)] for k in range(24)]
    lib.load("presets", names[0])
    assert lib.status and len(pr.bank) == 24 and all(pr.bank)
    assert _page_scroll(rig, monkeypatch)["presets"] == 0
    st = ui_presets._state(panel)
    labels, rects = st["bank_labels"], st["rects"]
    assert len(labels) == 24 and not any(label.endswith("—") for label in labels)
    slots = [rects[f"preset.{k}"] for k in range(24)]
    for i, a in enumerate(slots):
        for b in slots[i + 1:]:
            assert not _overlap(a, b)
    # F1–F8 two a row; 9–24 four a row, each row FAR_GAP under the last
    assert slots[0][1] == slots[1][1] < slots[2][1] and slots[0][0] == slots[2][0]
    for row in range(4):
        four = slots[8 + 4 * row: 12 + 4 * row]
        assert len({s[1] for s in four}) == 1 and [s[0] for s in four] == sorted(s[0] for s in four)
        assert [s[0] for s in four] == [s[0] for s in slots[8:12]]
        if row:
            above = slots[8 + 4 * (row - 1)]
            assert four[0][1] - above[3] == ui_presets.FAR_GAP
    assert slots[8][1] > slots[7][3] and slots[11][2] <= slots[1][2] + 1
    widths = {round(s[2] - s[0]) for s in slots[8:]}
    assert len(widths) == 1 and widths.pop() >= 90         # room for a number and a name
    # the sixteen filled and the rest empty: the same height, and it still fits
    pr.bank[16:] = [None] * 8
    assert _page_scroll(rig, monkeypatch)["presets"] == 0
    assert ui_presets._state(panel)["bank_labels"][16:] == [f"{k} —" for k in range(17, 25)]


def test_a_far_slot_reads_its_number_and_name_and_has_the_slot_menu(rig, tmp_path):  # noqa: F811
    """Slots 9–24 on the page: a number and the preset's name ("9 TRACER",
    "11 —"), the loaded one lit. A click loads the slot and ⇧click saves
    into it — through the bank, for a far slot has no trigger of its own —
    and the right-click menu is the slot menu under `preset.select`'s own
    items: "put preset here…" and "clear slot"."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    proj = lib.project
    show = tmp_path / "projects" / "party.hyp.json"
    frame(panel, "presets")
    frame(panel)
    st = ui_presets._state(panel)
    assert st["bank_labels"][8] == "9 TRACER" and st["bank_labels"][10] == "11 —"
    assert "preset.load.8" not in reg and "preset.save.8" not in reg
    # a click loads slot 9
    _click(panel, st["rects"]["preset.8"])
    assert lib.current("presets") == "TRACER" and proj.active == 8
    assert reg["preset.select"].value == 8 and not show.exists()
    # an empty far slot: said, nothing loaded
    _click(panel, st["rects"]["preset.10"])
    assert lib.warning == "slot 11: an empty slot — hold its pad to save the live state into it"
    assert lib.current("presets") == "TRACER"
    # its menu: the slot's two items, "clear slot" disabled while it is empty
    _click(panel, st["rects"]["preset.10"], button=1)
    menu = st["slot_menu"]
    assert menu["slot"] == 10
    assert menu["items"] == [("put preset here…", True), ("free this pad (keeps the preset)", False)]
    _click(panel, menu["rects"]["put"])
    menu = st["slot_menu"]
    pick = menu["names"][2]
    _click(panel, menu["rects"][f"name.{pick}"])
    assert proj.bank[10] == pick and json.loads(show.read_text())["bank"][10] == pick
    assert lib.status == f"slot 11: {pick}"
    frame(panel)
    frame(panel)
    assert ui_presets._state(panel)["bank_labels"][10].startswith("11 ")
    assert ui_presets._state(panel)["bank_labels"][10] != "11 —"
    # clear slot on a filled far slot
    st.pop("slot_menu")
    _click(panel, st["rects"]["preset.8"], button=1)
    menu = st["slot_menu"]
    assert menu["slot"] == 8 and menu["items"][1] == ("free this pad (keeps the preset)", True)
    _click(panel, menu["rects"]["clear"])
    assert proj.bank[8] is None and lib.status.startswith("slot 9: cleared — TRACER")
    assert "TRACER" in lib.list("presets")
    frame(panel)
    assert ui_presets._state(panel)["bank_labels"][8] == "9 —"
    # ⇧click saves the live state into the slot
    io = imgui.get_io()
    io.add_key_event(imgui.Key.mod_shift, True)
    frame(panel)
    _click(panel, st["rects"]["preset.14"])
    io.add_key_event(imgui.Key.mod_shift, False)
    frame(panel)
    assert proj.bank[14] == "PRESET 15" == lib.current("presets") and proj.active == 14
    assert json.loads(show.read_text())["bank"][14] == "PRESET 15"
    # the hovers say where a slot is
    tip = ui_presets.slot_tip
    # (plan 24 C1: SAVE held and the pad tapped, on a filled and an empty slot)
    assert tip(11, "TRIP 3") == ("slot 12: TRIP 3 — the desk's row 4, pad 4. Click loads, "
                                 "⇧click saves the live state as it. On the desk, hold "
                                 "SAVE and tap the pad: a new preset here, TRIP 3 kept in "
                                 "the list. Right-click → free this pad (keeps the preset) "
                                 "to make room")
    assert tip(2, "TRIP").startswith("F3: TRIP — the desk's row 1, pad 3.")
    assert tip(11, None) == ("slot 12: empty — the desk's row 4, pad 4. Hold SAVE and tap "
                             "the pad, or hold the pad (or ⇧click), to save the live state "
                             "here, or right-click to put a preset here")
    assert tip(16, "A").startswith("slot 17: A — the desk's row 5, pad 1.")
    assert tip(23, "A").startswith("slot 24: A — the desk's row 5, pad 8.")
    assert tip(2, "FIELD") == ("F3: FIELD — the desk's row 1, pad 3. Click loads, ⇧click "
                               "saves the live state as it. On the desk, hold SAVE and tap "
                               "the pad: a new preset here, FIELD kept in the list. "
                               "Right-click → free this pad (keeps the preset) to make room")
    assert tip(2, None) == ("F3: empty — the desk's row 1, pad 3. Hold SAVE and tap the pad, "
                            "or hold the pad (or ⇧click), to save the live state here, or "
                            "right-click to put a preset here")


# ------------------------------------------- plan 19 WP5: the dot and the save label

def _dirty(r):
    """An edit the loaded preset does not hold: the presets group (and the
    view's) is dirty."""
    reg = r.reg
    reg["view.bright"].set(reg["view.bright"].value * 0.5 + 0.1)
    assert r.lib.is_dirty("presets")


def test_the_dot_is_a_twelve_pixel_disc_and_save_is_lit_while_dirty(rig, monkeypatch):  # noqa: F811
    """The dot reads from a step back: a filled red disc 12 px across
    (`ui.DOT_R`), centred on the name's line, where the "●" glyph left
    about 7 px of ink; while it shows the save chip is the lit one (solid
    red), and the loaded slot carries a white disc of radius 4. The row
    does not grow: with "more" open every module strip under it is where
    it was, and the page still fits."""
    from hyperspace import ui

    panel, lib = rig.panel, rig.lib
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    _open_more(monkeypatch)
    lib.project.load_slot(4)                                  # F5: TRIP, a factory preset
    assert lib.current("presets") == "TRIP" and lib.project.active == 4
    frame(panel, "presets")
    frame(panel)
    st = ui_presets._state(panel)
    clean = dict(st["rects"])
    assert "strip.presets.dot" not in clean and "preset.dot" not in clean
    assert st["save"]["strip.presets"] == ("save copy", False)
    _dirty(rig)
    frame(panel)
    frame(panel)
    rects = st["rects"]
    x0, y0, x1, y1 = rects["strip.presets.dot"]
    assert x1 - x0 == y1 - y0 == 2 * ui.DOT_R == 12
    name = rects["strip.presets.name"]
    assert abs((y0 + y1) / 2 - (name[1] + name[3]) / 2) < 0.5     # on the name's middle
    assert name[2] <= x0 and x1 <= rects["strip.presets.next"][0]  # between the name and ▶
    assert st["save"]["strip.presets"] == ("save copy", True)     # lit while dirty
    # the loaded slot's white disc, radius 4, inside its button at the right end
    d, slot = rects["preset.dot"], rects["preset.4"]
    assert d[2] - d[0] == 2 * ui_presets.SLOT_DOT_R == 8
    assert slot[0] < d[0] and d[2] <= slot[2] and slot[1] < d[1] and d[3] < slot[3]
    # no row grew: the strip's own items, and every strip under it, are where they were
    for key in ("strip.presets.name", "strip.presets.save", "strip.presets.as",
                *[k for k in clean if k.startswith("strip.") and not k.startswith("strip.presets")]):
        assert rects[key][1] == clean[key][1] and rects[key][3] == clean[key][3], key
    assert any(k.startswith("strip.camera.") for k in clean)       # "more" was open
    assert ui.RAIL_DOT_R == 5                                      # the rail's disc, from 3.5
    assert _page_scroll(rig, monkeypatch)["presets"] == 0
    # saved: the dot goes and the chip is quiet again — and reads "save" (yours now)
    lib.overwrite("presets")
    frame(panel, "presets")
    frame(panel)
    assert "strip.presets.dot" not in st["rects"] and "preset.dot" not in st["rects"]
    assert st["save"]["strip.presets"] == ("save", False)


def test_save_reads_save_copy_on_a_factory_preset(rig, tmp_path, monkeypatch):  # noqa: F811
    """"save copy" while the loaded preset is a factory one — the save
    writes your own copy, which takes its place in the list — and "save"
    on yours; the hover says which. Clicking it is `Library.overwrite`,
    unchanged: after it the chip reads "save" and TRIP is listed once. A
    module strip keeps "save" (and its reset) whatever is loaded."""
    panel, lib = rig.panel, rig.lib
    lib.load("presets", "TRIP")
    assert ui_presets.save_label(lib, "presets") == "save copy"
    assert ui_presets.save_tip(lib, "presets") == (
        "Save your own copy of TRIP: the factory one is kept and yours takes its place "
        "in the list")
    _dirty(rig)
    frame(panel, "presets")
    frame(panel)
    st = ui_presets._state(panel)
    assert st["save"]["strip.presets"] == ("save copy", True)
    assert not (tmp_path / "presets" / "trip.json").exists()
    _click(panel, st["rects"]["strip.presets.save"])
    assert (tmp_path / "presets" / "trip.json").is_file()
    assert not lib.is_factory("presets", "TRIP") and lib.list("presets").count("TRIP") == 1
    frame(panel)
    assert st["save"]["strip.presets"] == ("save", False)
    assert ui_presets.save_label(lib, "presets") == "save"
    assert ui_presets.save_tip(lib, "presets") == (
        "Write the settings over TRIP (the old file goes to the trash)")
    # nothing loaded: "save", disabled
    lib.reland("presets", (None, None, None))
    assert ui_presets.save_label(lib, "presets") == "save"
    # a module strip keeps "save" and its reset
    _open_more(monkeypatch)
    lib.load("band", "Balanced")
    assert lib.is_factory("band", "Balanced")
    frame(panel)
    frame(panel)
    assert st["save"]["strip.band"][0] == "save" and "strip.band.reset" in st["rects"]


def test_the_preset_strip_has_no_reset_and_does_not_overlap(rig, monkeypatch):  # noqa: F811
    """The preset strip drops `reset` (on a document kind `Library.reset`
    loads a preset called "default", and none ships) so "save copy" fits:
    at the control size, the longest factory name loaded and dirty, the
    strip's items clear one another and the page's edge. With "more" open
    every module strip (dot, save, as…, reset) clears too — measured, as
    the plan asked, with the new dot's width."""
    panel, lib = rig.panel, rig.lib
    assert lib.default_name("presets") is None                 # what reset would load: none
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    _open_more(monkeypatch)
    factory = [n for n in lib.list("presets") if lib.is_factory("presets", n)]
    longest = max(factory, key=lambda n: (len(n), n))
    lib.load("presets", longest)
    _dirty(rig)
    for group in ui_presets.groups(panel):                    # every module strip dirty too
        if not lib.is_dirty(group):
            p = next(p for p in rig.reg if p.group == group and p.persist)
            p.set_norm(0.5 if p.norm != 0.5 else 0.25)
    frame(panel, "presets")
    frame(panel)
    frame(panel)
    st = ui_presets._state(panel)
    rects = st["rects"]
    assert "strip.presets.reset" not in rects
    assert st["save"]["strip.presets"] == ("save copy", True)
    page_right = max(r[2] for k, r in rects.items() if k.startswith("preset."))
    strips: dict[str, dict] = {}
    for k, r in rects.items():
        if k.startswith("strip."):
            strips.setdefault(k.split(".")[1], {})[k] = r
    assert set(strips) >= {"presets", "view", "camera", "band"}
    # the preset strip: every item clear of every other, inside the page
    items = strips.pop("presets")
    keys = sorted(items)
    for i, a in enumerate(keys):
        assert items[a][2] <= page_right + 1, a
        for b in keys[i + 1:]:
            assert not _overlap(items[a], items[b]), (a, b)
    # a module strip under "more" (measured, as the plan asked): its row
    # starts at ui.LABEL_W, so ◀ name ▶ (192 px with the dot) and save ·
    # as… · reset (163 px) do not both fit its 258 px — the save chip sits
    # over the name button's right end with or without a dot, as it did
    # before this package (reported, not changed here). What the dot must
    # not do is make that worse: the disc clears the name and ▶, and the
    # three chips clear one another and the page's edge
    for group, items in strips.items():
        dot = items.get(f"strip.{group}.dot")
        if dot is not None:
            assert not _overlap(dot, items[f"strip.{group}.name"])
            assert not _overlap(dot, items[f"strip.{group}.next"])
        chips = [items[f"strip.{group}.{c}"] for c in ("save", "as", "reset")]
        assert chips[0][2] <= chips[1][0] and chips[1][2] <= chips[2][0], group
        assert chips[2][2] <= page_right + 1, group
    assert _page_scroll(rig, monkeypatch)["presets"] == 0


# ------------------------------------------- plan 19 WP4: the list, the trash, a slot gone

def _open_list(panel):
    """Click the preset strip's name: the list opens (real mouse events),
    at the control window's size."""
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    frame(panel, "presets")
    frame(panel)
    st = ui_presets._state(panel)
    _click(panel, st["rects"]["strip.presets.name"])
    frame(panel)
    assert st["list"]["group"] == "presets"
    return st


def _row(st, name):
    return next(r for r in st["list"]["rows"] if r[0] == name)


def test_the_list_has_a_cross_on_every_preset_and_rename_on_yours(rig, tmp_path):  # noqa: F811
    """The preset list, driven by real clicks over the real Panel: × on
    every preset, `rename` only on yours; "show hidden (n)" only while
    something is hidden, "trash (n) ▸" only while the trash holds
    something; the list scrolls in its own child past twelve rows and each
    row's chips clear its name. × on a factory preset hides it, "show
    hidden" brings it back struck through with `unhide`; `rename` turns the
    row into the name field and Enter renames."""
    panel, lib = rig.panel, rig.lib
    lib.load("presets", "TRIP")
    lib.save_as("presets", "A MINE")                         # yours, first in the list
    st = _open_list(panel)
    rows = st["list"]["rows"]
    assert len(rows) == len(lib.list("presets")) > ui_presets.LIST_ROWS
    for name, chips, hidden in rows:
        assert not hidden
        assert chips == (("rename", "×") if name == "A MINE" else ("×",)), name
    assert st["list"]["foot"] == []
    rects = st["list"]["rects"]
    box = rects["rows"]
    assert box[3] - box[1] <= ui_presets.LIST_ROWS * ui_presets.list_row_h() + 1
    assert box[3] <= CONTROL_SIZE[1]                          # the popup fits the window
    for name in ("A MINE", "ACID"):
        row = rects[f"row.{name}"]
        first = rects[f"rename.{name}"] if name == "A MINE" else rects[f"×.{name}"]
        assert row[0] + imgui.calc_text_size(name).x < first[0] and first[2] <= box[2]
    # × on a factory preset: hidden, written to hidden.json, nothing else
    _click(panel, rects["×.ACID"])
    frame(panel)
    assert lib.hidden() == {"party-acid"} and "ACID" not in lib.list("presets")
    assert lib.status == "hidden ACID — F6 still loads it"
    assert [r[0] for r in st["list"]["rows"]].count("ACID") == 0
    assert st["list"]["foot"] == ["show hidden (1)"]
    # show hidden: back, struck through, with unhide
    assert st["list"]["rects"]["show_hidden"][3] <= CONTROL_SIZE[1]
    _click(panel, st["list"]["rects"]["show_hidden"])
    frame(panel)
    assert _row(st, "ACID") == ("ACID", ("unhide",), True)
    _click(panel, st["list"]["rects"]["unhide.ACID"])
    frame(panel)
    assert lib.hidden() == frozenset() and _row(st, "ACID") == ("ACID", ("×",), False)
    assert st["list"]["foot"] == []
    # rename: the row becomes the name field; Enter renames the file
    _click(panel, st["list"]["rects"]["rename.A MINE"])
    frame(panel)
    assert _row(st, "A MINE")[1] == ("field",) and st["naming"] == "rename:A MINE"
    io = imgui.get_io()
    io.add_input_characters_utf8("A SUNRISE")                 # typed over the seeded name
    frame(panel)
    io.add_key_event(imgui.Key.enter, True)
    frame(panel)
    io.add_key_event(imgui.Key.enter, False)
    frame(panel)
    frame(panel)
    assert lib.current("presets") == "A SUNRISE" and (tmp_path / "presets" /
                                                       "a-sunrise.json").is_file()
    assert lib.status == "renamed A MINE → A SUNRISE (0 shows updated)"
    # × on yours: to the trash, and the foot says the trash holds something
    frame(panel)
    _click(panel, st["list"]["rects"]["×.A SUNRISE"])
    frame(panel)
    assert "A SUNRISE" not in lib.list("presets") and len(lib.trash()) == 2
    assert st["list"]["foot"] == ["trash (2) ▸"]
    # a refused rename shows on the warning line (the footer): factory presets have
    # no rename chip, and a taken name is refused
    lib.save_as("presets", "A MINE")
    frame(panel)
    frame(panel)
    ui_presets._rename(panel, "A MINE", "TRIP")
    assert lib.warning.startswith("library: TRIP: that name is taken")


def _trash_view(panel, st):
    _click(panel, st["list"]["rects"]["trash"])
    frame(panel)
    return st["trash_view"]


def test_empty_asks_once_and_disarms(rig, tmp_path):  # noqa: F811
    """"empty trash…" asks once, in place, no modal: one click arms it —
    "delete N files for good? — click again" — and empties nothing; a
    second click within four seconds empties. The time running out, any
    other click, or the popup closing disarms it. Real clicks on the trash
    popup, opened from the list's "trash (n) ▸"."""
    panel, lib = rig.panel, rig.lib
    io = imgui.get_io()

    def fill():
        lib.load("presets", "TRIP")
        lib.save_as("presets", "A MINE")
        lib.delete("presets", "A MINE")
        ui_presets.invalidate(panel, "presets")

    fill()
    st = _open_list(panel)
    view = _trash_view(panel, st)
    assert view["rows"] and view["empty"] == "empty trash…"
    files = [t.path for t in lib.trash()]
    _click(panel, view["rects"]["empty"])
    view = st["trash_view"]
    assert view["empty"] == "delete 1 file for good? — click again"
    assert all(p.exists() for p in files)                     # one click empties nothing
    # the time runs out
    io.delta_time = ui_presets.EMPTY_S + 0.5
    frame(panel)
    io.delta_time = 1 / 60
    frame(panel)
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
    frame(panel)
    io.add_key_event(imgui.Key.escape, False)
    frame(panel)
    _click(panel, (5, 5, 6, 6))                               # outside both popups
    frame(panel)
    assert st.get("empty_armed") is None
    st = _open_list(panel)
    view = _trash_view(panel, st)
    assert view["empty"] == "empty trash…"
    # two clicks within the time: emptied
    _click(panel, view["rects"]["empty"])
    _click(panel, st["trash_view"]["rects"]["empty"])
    assert not any(p.exists() for p in files) and lib.trash() == []
    assert lib.status == "trash: 1 file deleted for good"


def test_a_slot_whose_preset_is_gone_says_so(rig, monkeypatch):  # noqa: F811
    """× on a preset a slot names: the slot keeps the name (not cleared for
    you), drawn in the warning ink, its hover saying where to look; the
    footer said which slots still name it. A restore makes it whole."""
    panel, lib = rig.panel, rig.lib
    pr = lib.project
    lib.load("presets", "TRIP")
    lib.save_as("presets", "A MINE")
    pr.put_slot(9, "A MINE")
    frame(panel, "presets")
    frame(panel)
    st = ui_presets._state(panel)
    assert st["dangling"] == []
    lib.delete("presets", "A MINE")
    assert lib.warning == ("A MINE is in the trash — slot 10 still names it; restore it "
                           "from the trash, or clear the slot")
    ui_presets.invalidate(panel, "presets")
    tips: list[str] = []
    with monkeypatch.context() as m:
        m.setattr(imgui, "set_tooltip", tips.append)
        real = imgui.is_item_hovered
        m.setattr(imgui, "is_item_hovered", lambda *a: True)
        frame(panel)
        m.setattr(imgui, "is_item_hovered", real)
    assert st["dangling"] == [9] and pr.bank[9] == "A MINE"
    assert st["bank_labels"][9] == "10 A MINE"
    assert ("slot 10: A MINE — no such preset. It may be in the trash (preset list → trash). "
            "Right-click → free this pad (keeps the preset)") in tips
    # restored: whole again
    (item,) = lib.trash()
    lib.restore_trash(item)
    assert lib.warning == "" and lib.status == "restored A MINE"   # × said is no longer so
    ui_presets.invalidate(panel, "presets")
    frame(panel)
    assert st["dangling"] == []


def test_the_open_list_does_not_reread_the_library_every_frame(rig, monkeypatch):  # noqa: F811
    """The open preset list costs what is on the poll cadence, not a full
    pass over the library per row per frame: on the owner's 79-preset
    cloud library, `is_factory` per row re-globbed both roots and stat'ed
    every file each frame (~50 ms, 25 fps with the list open). Ten frames
    with the list open re-index the library at most a few times, however
    many rows it draws."""
    panel = rig.panel
    st = _open_list(panel)
    assert len(st["list"]["rows"]) > ui_presets.LIST_ROWS
    calls = []
    real = Library._index

    def counted(self, group):
        calls.append(group)
        return real(self, group)

    monkeypatch.setattr(Library, "_index", counted)
    for _ in range(10):
        frame(panel)
    assert st["list"]["group"] == "presets"                 # still open
    assert len(calls) <= 3, f"{len(calls)} library index passes in 10 frames"
