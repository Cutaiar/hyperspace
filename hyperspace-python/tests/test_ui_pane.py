"""Plan 49, stage 1: GRAPH's side pane is always on and holds folding
sections — selection, presets, lookback, faces, analyzer — each drawing
what its page draws, found by the panel driver by the ids its page uses;
the fold state is this Mac's, in ui.json beside the pane's width."""

import json

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace import ui_graph, ui_pane, ui_presets
from hyperspace.ui import PAGE_KEYS

WIDE = (1600, 900)      # a page wider than ui_graph.WIDE: the pane beside the canvas

# a control each section draws, by the id its page draws it under
SECTION_IDS = {
    "presets": "new##new",           # the preset strip's new chip (ui_presets.strip)
    "lookback": "dream.on",
    "faces": "view.faces",
    "analyzer": "scene.select",
}


@pytest.fixture()
def pane(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.desk = False                     # the panel the whole window
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        d = Driver(step=lambda: frame(r.panel, "graph"))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        yield r, d


def _st(r):
    return ui_graph._state(r.panel)


def _inside(rect, box) -> bool:
    (x, y), (w, _h) = box
    x0, y0, x1, _y1 = rect
    return x <= x0 and x1 <= x + w + 1 and y <= y0


def test_the_pane_is_on_with_nothing_selected_and_says_so(pane, monkeypatch):
    r, d = pane
    st = _st(r)
    assert r.panel.graph_selected is None
    assert st["details_rect"] is not None            # the pane, with nothing selected
    assert {"pane.selection", "pane.presets", "pane.lookback", "pane.faces",
            "pane.analyzer"} <= set(d.rects)
    said: list[str] = []
    real = imgui.text_wrapped
    monkeypatch.setattr(imgui, "text_wrapped", lambda s, *a: (said.append(s), real(s, *a)))
    d.run(d.wait(1))
    assert ui_pane.NOTHING in said
    assert st["pane_drawn"] == ["selection", "presets"]      # the defaults (rec)


@pytest.mark.parametrize("key", sorted(SECTION_IDS))
def test_each_section_opens_by_a_click_and_its_controls_are_found_by_id(pane, key):
    r, d = pane
    st = _st(r)
    pid = SECTION_IDS[key]
    if key == "presets":                             # open by default: fold it first
        d.run(d.click("pane.presets"), d.park())
        assert "presets" not in st["pane_drawn"]
    else:
        assert "pane." + key in d.rects and key not in st["pane_drawn"]
        with pytest.raises(KeyError):
            d.rect(pid)
    if key != "presets":
        d.run(d.click("pane.presets"), d.park())     # room for the one under test
    d.run(d.click("pane." + key), d.park(), d.wait(1))
    assert key in st["pane_drawn"]
    assert _inside(d.rect(pid), st["details_rect"])   # drawn in the pane, under its page's id


def test_a_click_in_a_section_moves_the_param_as_on_its_page(pane):
    r, d = pane
    d.run(d.click("pane.faces"), d.park(), d.wait(1))
    was = bool(r.reg["view.faces"].base)
    d.run(d.click("view.faces"), d.park())
    assert bool(r.reg["view.faces"].base) is (not was)
    # (the lookback section alone open: the dream's head, where its switch
    # is, is far enough down that a shared body scrolls it out of view)
    _only(_st(r), "lookback")
    d.step = _tall_driver(r, None).step     # (a pane tall enough for the whole section)
    d.run(d.wait(3))
    was = bool(r.reg["dream.on"].base)
    d.run(d.click("dream.on"), d.park())
    assert bool(r.reg["dream.on"].base) is (not was)


def test_a_selection_shows_in_the_selection_section(pane):
    r, d = pane
    st = _st(r)
    view = ui_graph.view_of(r.panel)
    node = next(n for n in view.nodes if n.kind != "modifier")
    r.panel.select_graph_node(node.id)
    d.run(d.wait(3))
    assert r.panel.graph_selected == node.id
    assert ui_graph._selection(st, st["view"])[1].id == node.id
    assert "selection" in st["pane_drawn"]


def test_a_new_selection_leaves_the_fold_alone_and_its_header_names_it(pane, monkeypatch):
    """Review fix 7: only a click unfolds a section; a folded selection's
    header says what is selected."""
    r, d = pane
    st = _st(r)
    d.run(d.click("pane.selection"), d.park())
    assert "selection" not in st["pane_drawn"]
    view = ui_graph.view_of(r.panel)
    node = next(n for n in view.nodes if n.label)
    r.panel.select_graph_node(node.id)
    d.run(d.wait(3))
    assert "selection" not in st["pane_drawn"]
    head = next(k for k in d.rects if k.endswith("##pane.selection"))
    assert ui_graph.sel_words(("node", node))[:4] in head


def test_the_fold_state_round_trips_through_this_macs_ui_json(pane):
    r, d = pane
    st = _st(r)
    machine = r.lib.machine
    d.run(d.click("pane.analyzer"), d.park(), d.click("pane.presets"), d.park())
    assert not (machine / ui_pane.UI_FILE).exists()      # not yet: a click is written later
    assert ui_pane.flush(st, force=True)
    doc = json.loads((machine / ui_pane.UI_FILE).read_text())
    assert doc["pane"]["open"]["analyzer"] is True and doc["pane"]["open"]["presets"] is False
    assert ui_pane.read_open(machine) == dict(ui_pane.DEFAULT_OPEN, analyzer=True,
                                              presets=False)
    # a fresh page state (a relaunch) reads it back
    st.pop("pane_open")
    d.run(d.wait(2))
    assert st["pane_drawn"] == ["selection", "analyzer"]
    # the width beside it is kept by a drag's write, and the fold by a click's
    ui_graph.write_side(machine, 400.0)
    doc = json.loads((machine / ui_pane.UI_FILE).read_text())
    assert doc["graph"]["side_w"] == 400.0 and doc["pane"]["open"]["analyzer"] is True
    ui_pane.write_open(machine, ui_pane.read_open(machine))
    assert ui_graph.read_side(machine) == 400.0


def test_a_bad_ui_json_costs_only_the_memory(tmp_path):
    assert ui_pane.read_open(tmp_path) == ui_pane.DEFAULT_OPEN          # no file
    (tmp_path / ui_pane.UI_FILE).write_text("[1, 2]")
    assert ui_pane.read_open(tmp_path) == ui_pane.DEFAULT_OPEN          # not an object
    (tmp_path / ui_pane.UI_FILE).write_text(
        '{"pane": {"open": {"faces": true, "analyzer": "yes", "nope": true}}, "x": 1}')
    got = ui_pane.read_open(tmp_path)
    assert got["faces"] is True and got["analyzer"] is False and "nope" not in got
    ui_pane.write_open(tmp_path, got)
    assert json.loads((tmp_path / ui_pane.UI_FILE).read_text())["x"] == 1   # the rest kept
    ui_pane.write_open(tmp_path / "missing" / "dir", got)                # no raise
    assert ui_pane.read_open(None) == ui_pane.DEFAULT_OPEN


def test_open_bodies_share_the_pane():
    assert ui_pane.body_height(600.0, 2) == 300.0
    assert ui_pane.body_height(200.0, 3) == ui_pane.MIN_BODY_H
    assert ui_pane.body_height(600.0, 0) == 0.0


def test_every_section_open_draws_with_no_conflicting_ids(pane, monkeypatch):
    """All five open at once: each widget its own imgui id (the label
    hashed under the id stack), though the sections reuse their pages'
    labels and two of them draw preset strips."""
    r, _d = pane
    st = _st(r)
    ui_pane.opened(st).update(dict.fromkeys(ui_pane.KEYS, True))
    view = ui_graph.view_of(r.panel)
    r.panel.select_graph_node(view.nodes[0].id)

    def tall() -> None:                 # a window tall enough for every body unscrolled
        imgui.get_io().display_size = imgui.ImVec2(1600, 2400)
        imgui.new_frame()
        imgui.set_window_size("CONTROLS", imgui.ImVec2(1576, 2376))
        r.panel.draw(1 / 60, 60.0)
        imgui.end_frame()
    for _ in range(3):
        tall()
    assert st["pane_drawn"] == list(ui_pane.KEYS)
    ids: list[tuple[int, str]] = []
    for fn in ("button", "checkbox", "slider_float", "slider_int", "combo",
               "invisible_button", "small_button", "selectable"):
        real = getattr(imgui, fn)

        def rec(label, *a, _real=real, **k):
            ids.append((imgui.get_id(label), label))
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    tall()
    seen = [i for i, _ in ids]
    dup = {lb for i, lb in ids if seen.count(i) > 1}
    assert not dup, f"conflicting ids {sorted(dup)}"


def test_the_pages_still_draw_their_bodies(pane):
    """The rail and the pages are untouched: each page whose body a
    section shares still draws it, at full height."""
    r, _d = pane
    for key in ("presets", "lookback", "faces", "analyzer"):
        frame(r.panel, key)
        frame(r.panel, key)
        assert PAGE_KEYS[r.panel.page] == key
    frame(r.panel, "graph")


def test_a_fold_is_written_after_the_last_click_and_on_close(tmp_path):
    """Review fix 7: no write on the click's frame; one `WRITE_AFTER_S`
    after the last change, or at once when the page closes."""
    st = {"machine": tmp_path}
    ui_pane.set_open(st, "faces", True, now=10.0)
    assert not ui_pane.flush(st, now=10.0 + ui_pane.WRITE_AFTER_S / 2)
    ui_pane.set_open(st, "analyzer", True, now=10.3)          # a second click: the clock again
    assert not ui_pane.flush(st, now=10.0 + ui_pane.WRITE_AFTER_S)
    assert ui_pane.flush(st, now=10.3 + ui_pane.WRITE_AFTER_S)
    assert ui_pane.read_open(tmp_path)["analyzer"] is True
    assert not ui_pane.flush(st, force=True)                   # nothing left
    ui_pane.set_open(st, "faces", False, now=20.0)
    assert ui_pane.flush(st, force=True)
    assert ui_pane.read_open(tmp_path)["faces"] is False


def test_a_library_attached_late_has_its_fold_read_then(tmp_path, monkeypatch):
    """Review fix 4: GRAPH drawn before the library is attached shows the
    defaults, then reads this Mac's file the first frame the machine is
    known."""
    with build_rig(tmp_path) as r:
        machine = r.lib.machine
        ui_pane.write_open(machine, dict(ui_pane.DEFAULT_OPEN, faces=True))
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        lib, r.panel.library = r.panel.library, None
        for _ in range(2):
            frame(r.panel, "graph")
        st = _st(r)
        assert st["machine"] is None and "faces" not in st["pane_drawn"]
        ui_pane.set_open(st, "analyzer", True)       # a click before the library is there
        r.panel.library = lib
        for _ in range(2):
            frame(r.panel, "graph")
        assert st["machine"] == machine
        # the file's fold and the click both kept (review round 2); (plan 49
        # stage 2: with twelve headers the analyzer's body may be scrolled
        # out of the pane's view, so its fold is read, not its draw)
        assert "faces" in st["pane_drawn"]
        assert ui_pane.opened(st)["faces"] and ui_pane.opened(st)["analyzer"]
        assert ui_pane.flush(st, force=True)
        got = ui_pane.read_open(machine)
        assert got["faces"] is True and got["analyzer"] is True


def test_the_grip_holds_its_edge_while_the_pane_scrolls(pane):
    """Review fix 1: with every section open the column scrolls; its range
    stays put frame after frame (the grip adds no content), and a drag on
    the edge still resizes it, scrolled or not."""
    r, d = pane
    st = _st(r)
    ui_pane.opened(st).update(dict.fromkeys(ui_pane.KEYS, True))
    d.run(d.wait(3))
    win = imgui.internal.find_window_by_name(st["pane_window"])
    assert win.scroll_max.y > 0
    first = win.scroll_max.y
    win.scroll.y = win.scroll_max.y
    d.run(d.wait(5))
    assert win.scroll_max.y == first
    (x, y), (_w, h) = st["details_rect"]
    io = imgui.get_io()
    side = st["side_w"]
    io.add_mouse_pos_event(x + ui_graph.GRIP_W / 2, y + h / 2)
    d.run(d.wait(1))
    io.add_mouse_button_event(0, True)
    d.run(d.wait(1))
    io.add_mouse_pos_event(x + ui_graph.GRIP_W / 2 - 40.0, y + h / 2)
    d.run(d.wait(1))
    assert st["side_drag"] and abs(st["side_w"] - (side + 40.0)) < 1e-6
    io.add_mouse_button_event(0, False)
    d.run(d.wait(2))
    assert not st["side_drag"] and ui_graph.read_side(r.lib.machine) == side + 40.0


def test_the_narrow_band_opens_selection_alone_and_one_section_takes_it_all(
        tmp_path, monkeypatch):
    """Review fix 2: on the control window's narrow page the pane is the
    band under the canvas, with its own fold state — selection alone at
    first — the headers one row, and an open section the band's height."""
    with build_rig(tmp_path) as r:
        d = Driver(step=lambda: frame(r.panel, "graph"))    # the rig's 820 px window
        d.record(monkeypatch.setattr)
        d.run(d.wait(3))
        st = _st(r)
        _pos, (_w, h) = st["details_rect"]
        assert h == ui_graph.BELOW_H
        assert st["pane_drawn"] == ["selection"]
        heads = [d.rect("pane." + k) for k in ui_pane.KEYS]
        # (plan 49 stage 2: twelve chips wrap to rows, each inside the band)
        (bx, _by), (bw, _bh) = st["details_rect"]
        assert all(bx <= rc[0] and rc[2] <= bx + bw + 1 for rc in heads)
        rows = sorted({round(rc[1]) for rc in heads})
        assert 1 < len(rows) <= 3
        assert [round(rc[1]) for rc in heads] == sorted(round(rc[1]) for rc in heads)
        d.run(d.click("pane.selection"), d.park(), d.click("pane.presets"), d.park())
        assert st["pane_drawn"] == ["presets"]
        assert ui_pane.opened(st, "open") == ui_pane.DEFAULT_OPEN    # beside: untouched
        ui_pane.flush(st, force=True)
        assert ui_pane.read_open(r.lib.machine, "below")["presets"] is True


def test_the_strip_budgets_the_devices_missing_chip(tmp_path):
    """Review fix 5: the name gives way to the chip after ▶."""
    with build_rig(tmp_path):
        imgui.new_frame()
        chips = ("new", "save", "as…")
        full = ui_presets.strip_name_w(1000.0, chips, False)
        assert full == ui_presets.name_w()
        narrow = ui_presets.strip_name_w(300.0, chips, False)
        assert ui_presets.strip_name_w(300.0, chips, False, 60.0) == max(
            ui_presets.NAME_MIN, narrow - 60.0)
        imgui.end_frame()


def test_the_projector_inset_keeps_clear_of_the_pane(tmp_path, monkeypatch):
    """Review round 2: the held projector's inset is laid in the canvas
    left of the pane beside it, and above the band under it on a narrow
    page — never over the pane."""
    pic = (1920, 1080)
    (x, y), (x1, y1) = ui_graph.monitor_rect((0.0, 0.0), (800.0, 100.0), pic)
    assert y1 <= 100.0 - 8.0 + 1e-6 and abs((y1 - y) / (x1 - x) - 1080 / 1920) < 1e-6
    with build_rig(tmp_path) as r:                  # the rig's 820 px window: narrow
        got = []
        monkeypatch.setattr(ui_graph, "_monitor", lambda panel, o, a: got.append((o, a)))
        for _ in range(2):
            frame(r.panel, "graph")
        st = _st(r)
        (px, py), (_pw, _ph) = st["details_rect"]
        (ox, oy), (aw, ah) = got[-1]
        assert oy + ah <= py + 1e-6                  # the inset's room stops at the band
        _a, b = ui_graph.monitor_rect((ox, oy), (aw, ah), pic)
        assert b[1] <= py
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        imgui.new_frame()
        imgui.set_window_size("CONTROLS", imgui.ImVec2(WIDE[0] - 24, WIDE[1] - 24))
        r.panel.draw(1 / 60, 60.0)
        imgui.end_frame()
        (px, py), (_pw, _ph) = st["details_rect"]
        (ox, oy), (aw, ah) = got[-1]
        assert ox + aw <= px + 1e-6                  # wide: left of the column


# ---------------------------------------------------------------- stage 2 (U2)

# a control each stage-2 section draws, by the id its page draws it under
STAGE2_IDS = {
    "fx": "fx.on",
    "media": "media.a.rate",
    "lfo": "tempo.bpm",
    "seq": "chip.seq.run",
    "audio": "audio.mic",
    "camera": "camera.zoom",
    "output": "output.fullscreen",
}


def _with_seq(r):
    """The sequencer and its envelopes, as app.py gives the panel them
    (the shell's rig has the clock and the LFOs, not these)."""
    from hyperspace import envelope, sequencer
    envs, seq = envelope.Envelopes(), sequencer.Sequencer()
    envelope.register(r.reg, envs, r.panel.clock)
    sequencer.register(r.reg, seq, r.panel.clock)
    r.panel.envs, r.panel.seq = envs, seq


def _only(st, key, layout="open"):
    ui_pane.opened(st, layout).update({k: k == key for k in ui_pane.KEYS})


def _spills(d, st) -> list[tuple[str, float]]:
    """The controls drawn in the pane last frame whose right edge passes
    the pane's: (id, by how many px)."""
    (x, y), (w, h) = st["details_rect"]
    out = []
    for k, (x0, y0, x1, _y1) in d.rects.items():
        if x0 >= x - 1 and y - 1 <= y0 <= y + h and x1 > x + w + 1:
            out.append((k, round(x1 - (x + w), 1)))
    return out


def _tall_driver(r, monkeypatch, size=(1600, 2400)):
    def tall() -> None:
        imgui.get_io().display_size = imgui.ImVec2(*size)
        imgui.new_frame()
        imgui.set_window_size("CONTROLS", imgui.ImVec2(size[0] - 24, size[1] - 24))
        r.panel.draw(1 / 60, 60.0)
        imgui.end_frame()
    d = Driver(step=tall)
    if monkeypatch is not None:
        d.record(monkeypatch.setattr)
    return d


@pytest.mark.parametrize("key", sorted(STAGE2_IDS))
@pytest.mark.parametrize("width", ["min", "default"])
def test_each_stage2_section_draws_in_the_pane_and_nothing_passes_its_edge(
        tmp_path, monkeypatch, key, width):
    """Every section stage 2 added, alone open, at the pane's narrowest
    (`SIDE_MIN`) and at its default width: its page's control found by
    its page's id inside the pane, and no control past the pane's right
    edge (a row that would spill wraps, the grids lay out for the room)."""
    with build_rig(tmp_path) as r:
        _with_seq(r)
        r.panel.desk = False
        r.panel.page = PAGE_KEYS.index("graph")
        d = _tall_driver(r, monkeypatch)
        d.run(d.wait(2))
        st = _st(r)
        st["side_w"] = ui_graph.SIDE_MIN if width == "min" else ui_graph.SIDE_W
        _only(st, key)
        d.run(d.wait(3))
        assert st["pane_drawn"] == [key]
        assert _inside(d.rect(STAGE2_IDS[key]), st["details_rect"])
        spills = _spills(d, st)
        assert not spills, sorted(spills)


def test_the_redrawn_lookback_section_keeps_inside_the_narrowest_pane(tmp_path, monkeypatch):
    """The LOOKBACK section as its two picture nodes at `SIDE_MIN`: every
    control inside the pane, the cells one to a row there."""
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        r.panel.page = PAGE_KEYS.index("graph")
        d = _tall_driver(r, monkeypatch)
        d.run(d.wait(2))
        st = _st(r)
        st["side_w"] = ui_graph.SIDE_MIN
        _only(st, "lookback")
        d.run(d.wait(3))
        assert _spills(d, st) == []
        fade, gap = d.rect("dream.fade"), d.rect("dream.gap")
        assert fade[1] < gap[1]                              # one to a row
        on, mix = d.rect("dream.on"), d.rect("dream.mix")
        assert d.rect("dream.occlude")[1] < on[1] < mix[1]   # the look-back's, then the dream's


def test_the_media_grid_goes_four_to_a_row_and_the_seq_grid_thins_in_the_pane(
        tmp_path, monkeypatch):
    """Plan 49 stage 2's two hard ones, at `SIDE_MIN`: MEDIA's eight
    channels A–D over E–H, each bin's cells inside the pane; SEQ's eight
    steps still across, no thinner than `ui_seq.CELL_MIN`."""
    from hyperspace import ui_media, ui_seq
    with build_rig(tmp_path) as r:
        _with_seq(r)
        r.panel.desk = False
        r.panel.page = PAGE_KEYS.index("graph")
        d = _tall_driver(r, monkeypatch)
        d.run(d.wait(2))
        st = _st(r)
        st["side_w"] = ui_graph.SIDE_MIN
        _only(st, "media")
        d.run(d.wait(3))
        cells = ui_media._state(r.panel)["rects"]
        a, e, d_ = cells[("cell", "a", 0)], cells[("cell", "e", 0)], cells[("cell", "d", 0)]
        assert e[1] > a[3] and abs(e[0] - a[0]) < 1 and d_[1] == a[1]   # E under A, D beside
        _only(st, "seq")
        d.run(d.wait(3))
        one, eight = d.rect("seq.1.1"), d.rect("seq.1.8")
        assert one[1] == eight[1]                              # the eight across
        assert one[2] - one[0] >= ui_seq.CELL_MIN - 0.5
        assert _spills(d, st) == []


def test_the_fx_page_is_retired_into_the_fx_section(pane):
    """The rail has no FX pill; `ui.page` set to FX — a key row, an old
    show — opens GRAPH with the fx section unfolded and drawn, and the
    index every other page holds is what it was."""
    from hyperspace.ui import PAGES, RETIRED
    r, d = pane
    st = _st(r)
    fx = PAGE_KEYS.index("fx")
    assert "fx" in RETIRED and PAGES[fx][0] == "fx"           # the slot kept
    assert f"page{fx}" not in d.rects and f"page{PAGE_KEYS.index('graph')}" in d.rects
    assert "fx" not in st["pane_drawn"]
    r.panel.page = PAGE_KEYS.index("view")
    r.reg["ui.page"].set(fx)
    assert PAGE_KEYS[r.panel.page] == "graph"
    d.run(d.wait(2))
    assert ui_pane.opened(st)["fx"] and "fx" in st["pane_drawn"]
    assert _inside(d.rect("fx.on"), st["details_rect"])
    assert ui_pane.flush(st, force=True)                       # an unfold, kept as a click's
    assert ui_pane.read_open(r.lib.machine)["fx"] is True
    # set straight, not through the param (⌘[ / ⌘]'s history): the same
    r.panel.page = fx
    d.run(d.wait(1))
    assert PAGE_KEYS[r.panel.page] == "graph"


def test_focus_unfolds_in_the_layout_last_drawn():
    st = {"machine": None, "pane_layout": "below"}
    ui_pane.focus(st, "seq")
    assert ui_pane.opened(st, "below")["seq"] and not ui_pane.opened(st, "open")["seq"]
    assert st["pane_focus"] == "seq"


def test_the_system_page_says_what_each_open_section_costs(pane, monkeypatch):
    r, _d = pane
    st = _st(r)
    assert set(st["pane_ms"]) >= {"selection", "presets"}
    line = ui_pane.timing_line(r.panel, st)
    assert line.startswith("side pane: ") and "presets" in line and line.endswith(" ms")
    assert ui_pane.timing_line(r.panel, None) == ""
    said: list[str] = []
    real = imgui.text_disabled
    monkeypatch.setattr(imgui, "text_disabled", lambda s, *a: (said.append(s), real(s, *a)))
    frame(r.panel, "system")
    assert any(s.startswith("side pane: ") for s in said)
    frame(r.panel, "graph")
