"""Plan 49, stage 1: GRAPH's side pane is always on and holds folding
sections — selection, presets, lookback, faces, analyzer — each drawing
what its page draws, found by the panel driver by the ids its page uses;
the fold state is this Mac's, in ui.json beside the pane's width."""

import itertools
import json

import pytest
from imgui_bundle import imgui, implot
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace import ui, ui_bands, ui_graph, ui_pane, ui_presets
from hyperspace.analyzer import N_MAX
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
        frame(r.panel, "graph")                  # nothing focused; a test may focus
        d = Driver(step=lambda: frame(r.panel))
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
    """All of them open at once: each widget its own imgui id (the label
    hashed under the id stack), though the sections reuse their pages'
    labels and two of them draw preset strips."""
    r, _d = pane
    st = _st(r)
    ui_pane.opened(st).update(dict.fromkeys(ui_pane.KEYS, True))
    view = ui_graph.view_of(r.panel)
    r.panel.select_graph_node(view.nodes[0].id)

    def tall() -> None:                 # a window tall enough for every body unscrolled
        imgui.get_io().display_size = imgui.ImVec2(1600, 4000)
        imgui.new_frame()
        imgui.set_window_size("CONTROLS", imgui.ImVec2(1576, 3976))
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


def test_ui_page_on_fx_focuses_the_fx_section_and_every_slot_keeps_its_index(pane):
    """The FX page went with stage 2; its slot stays, so a key row or an old
    show that names it lands on the effects: `ui.page` set to FX focuses
    the fx section. The slots are the ones every saved binding names."""
    r, d = pane
    st = _st(r)
    assert PAGE_KEYS == [
        "output", "view", "faces", "media", "camera", "lookback", "fx", "audio", "analyzer",
        "routing", "graph", "lfo", "seq", "hands", "presets", "system", "players"]
    fx = PAGE_KEYS.index("fx")
    assert "fx" not in st["pane_drawn"]
    r.reg["ui.page"].set(fx)
    assert PAGE_KEYS[r.panel.page] == "fx"
    d.run(d.wait(3))
    assert ui_pane.focused(r.panel) == "fx" and "fx" in st["pane_drawn"]
    assert _inside(d.rect("fx.on"), st["details_rect"])
    # set straight, not through the param (⌘[ / ⌘]'s history): the same
    r.panel.page = PAGE_KEYS.index("lfo")
    d.run(d.wait(3))
    assert ui_pane.focused(r.panel) == "lfo" and "lfo" in st["pane_drawn"]
    assert "fx" not in st["pane_drawn"]


def test_every_page_slot_but_graph_is_a_section():
    """No page is left to switch to: the table `ui.page` indexes names a
    section in every slot, GRAPH's being the canvas that is always drawn."""
    assert ui_pane.section_of("graph") is None
    assert {k for k in PAGE_KEYS if ui_pane.section_of(k) is None} == {"graph"}
    assert set(ui_pane.KEYS) - set(PAGE_KEYS) == {"selection"}


def test_focus_unfolds_only_while_it_holds_and_never_touches_the_fold(pane):
    """The focused section shows however it is folded and folds back when
    the focus moves on or lets go; nothing is written: a walk through the
    sections leaves no pile of open ones, on screen or in ui.json."""
    r, d = pane
    st = _st(r)
    before = dict(ui_pane.opened(st))
    for key in ("lfo", "seq", "audio"):
        r.reg["ui.page"].set(PAGE_KEYS.index(key))
        d.run(d.wait(3))
        assert key in st["pane_drawn"], key
    assert "lfo" not in st["pane_drawn"] and "seq" not in st["pane_drawn"]
    assert ui_pane.opened(st) == before and not st.get("pane_dirty")
    r.reg["ui.page"].set(PAGE_KEYS.index("graph"))
    d.run(d.wait(2))
    assert ui_pane.focused(r.panel) is None and st["pane_drawn"] == ["selection", "presets"]


def test_a_click_on_the_focused_header_lets_go_and_on_another_leaves_it(pane):
    r, d = pane
    st = _st(r)
    r.reg["ui.page"].set(PAGE_KEYS.index("lfo"))
    d.run(d.wait(3))
    d.run(d.click("pane.camera"), d.park())
    assert ui_pane.focused(r.panel) == "lfo" and ui_pane.opened(st)["camera"]
    d.run(d.wait(2))
    d.run(d.click("pane.lfo"), d.park())
    assert ui_pane.focused(r.panel) is None and "lfo" not in st["pane_drawn"]
    assert ui_pane.opened(st)["camera"]                       # a click's: kept


def test_setting_the_same_slot_again_brings_the_section_back(pane):
    """A key row pressed twice, the section folded by a click between: the
    second press focuses it again."""
    r, d = pane
    st = _st(r)
    k = PAGE_KEYS.index("seq")
    r.reg["ui.page"].set(k)
    d.run(d.wait(3))
    d.run(d.click("pane.seq"), d.park())
    assert ui_pane.focused(r.panel) is None
    r.reg["ui.page"].set(k)
    d.run(d.wait(3))
    assert ui_pane.focused(r.panel) == "seq" and "seq" in st["pane_drawn"]


def test_the_focused_section_lands_at_the_top_of_the_pane_with_room(tmp_path, monkeypatch):
    """Selection and presets open above it, the pane shorter than the lot:
    the focused header scrolls to the pane's top, its body runs down to the
    headers after it, and those stay in view."""
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        r.reg["ui.page"].set(PAGE_KEYS.index("view"))
        d.run(d.wait(4))
        st = _st(r)
        (_x, y), (_w, h) = st["details_rect"]
        head = d.rect("pane.view")
        assert y <= head[1] <= y + 24                         # at the top of the pane
        assert d.rect("pane.system")[3] <= y + h              # the last header still in view
        assert d.rect("pane.fx")[1] - head[3] >= ui_pane.MIN_BODY_H   # the body's room


def test_the_band_grows_for_the_focused_section_and_only_it_draws(tmp_path, monkeypatch):
    """The desk's narrow panel: the band under the canvas holds the focused
    section alone, all but `CANVAS_MIN` of the page, the chips above it; a
    click on a chip lets go and the band is `BELOW_H` again. The column
    beside the canvas keeps its folds."""
    with build_rig(tmp_path) as r:              # the rig's 820 px window: the band
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        r.reg["ui.page"].set(PAGE_KEYS.index("graph"))
        d.run(d.wait(2))
        st = _st(r)
        assert st["details_rect"][1][1] == ui_graph.BELOW_H
        r.reg["ui.page"].set(PAGE_KEYS.index("fx"))
        d.run(d.wait(3))
        assert st["details_rect"][1][1] > ui_graph.BELOW_H
        assert st["pane_drawn"] == ["fx"]
        assert _inside(d.rect("fx.on"), st["details_rect"])
        assert not ui_pane.opened(st, "below")["fx"]
        d.run(d.click("pane.seq"), d.park())
        assert ui_pane.focused(r.panel) is None
        assert st["details_rect"][1][1] == ui_graph.BELOW_H
        assert ui_pane.opened(st, "below")["seq"]


def test_the_rail_is_gone_and_graph_is_live_on_every_frame(pane):
    """No page pill anywhere; `graph_selected` follows the canvas with any
    section focused, not "as of the last frame GRAPH drew"."""
    r, d = pane
    assert not [k for k in d.rects if k.startswith("page") and k[4:].isdigit()]
    view = ui_graph.view_of(r.panel)
    nid = view.nodes[0].id
    r.reg["ui.page"].set(PAGE_KEYS.index("system"))
    d.run(d.wait(2))
    assert r.panel.graph_selected is None
    ui_graph._state(r.panel)["select_node"] = nid       # the canvas's selection, no page moved
    d.run(d.wait(3))
    assert r.panel.graph_selected == nid
    assert PAGE_KEYS[r.panel.page] == "system"


def test_every_section_draws_without_a_router(tmp_path, monkeypatch):
    """A panel with no router has no canvas to draw; the sections all the
    same."""
    with build_rig(tmp_path) as r:
        r.panel.router = None
        for key in ("view", "system", "lfo"):
            for _ in range(2):
                frame(r.panel, key)
            assert key in _st(r)["pane_drawn"]


def test_the_system_page_says_what_each_open_section_costs(pane, monkeypatch):
    r, _d = pane
    st = _st(r)
    assert set(st["pane_ms"]) >= {"selection", "presets"}
    line = ui_pane.timing_line(r.panel)
    assert line.startswith("side pane: ") and "presets" in line and line.endswith(" ms")
    from types import SimpleNamespace
    assert ui_pane.timing_line(SimpleNamespace()) == ""         # GRAPH never drew
    said: list[str] = []
    real = imgui.text_disabled
    monkeypatch.setattr(imgui, "text_disabled", lambda s, *a: (said.append(s), real(s, *a)))
    for _ in range(3):                  # focused, scrolled to, drawn
        frame(r.panel, "system")
    assert any(s.startswith("side pane: ") for s in said)
    frame(r.panel, "graph")


def test_a_node_heads_hover_is_the_whole_band(tmp_path, monkeypatch):
    """Review fix 2: the look-back's and the dream's heads say what they
    are, and the dream where its worker is set up, wherever on the band
    the mouse is — not only over the word at its right."""
    from hyperspace import ui, ui_lookback
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        r.panel.page = PAGE_KEYS.index("graph")
        d = _tall_driver(r, monkeypatch)
        d.run(d.wait(2))
        st = _st(r)
        _only(st, "lookback")
        d.run(d.wait(3))
        said: list[str] = []
        real = ui.tooltip
        monkeypatch.setattr(ui, "tooltip", lambda text: (said.append(text), real(text)))
        x0, y0, x1, y1 = d.rect("dream.on")        # the dream's head: just right of its tick
        d.run(d.move((x1 + 30, (y0 + y1) / 2)), d.wait(1))
        assert any(t.startswith("dream: " + ui_lookback.PORTS["dream"]) and "[dream]" in t
                   for t in said)
        said.clear()
        x0, y0, _x1, y1 = d.rect("dream.on")
        d.run(d.move(((x0 + _x1) / 2, (y0 + y1) / 2)), d.wait(1))   # over the tick itself
        assert not any(t.startswith("dream: ") for t in said)


def test_the_lookback_asks_the_graph_its_names_once_per_graph(tmp_path, monkeypatch):
    """Review fix 6: `learn.drawn_of` walks the wires; the page asks it
    once for each graph loaded, not every frame."""
    from hyperspace import learn, ui_lookback
    asked = []
    real = learn.drawn_of
    monkeypatch.setattr(learn, "drawn_of", lambda spec: (asked.append(spec), real(spec))[1])
    with build_rig(tmp_path) as r:
        for _ in range(4):
            frame(r.panel, "lookback")
        assert len(asked) == 1
        spec = ui_lookback._spec(r.panel)
        assert ui_lookback._drawn(r.panel, spec) is ui_lookback._drawn(r.panel, spec)


def test_the_track_readout_is_measured_as_printed(tmp_path, monkeypatch):
    """Review fix 3: a track past 100 minutes ("102:05 / 140:00") is
    measured as it is printed, so its readout wraps rather than passing
    the pane's edge."""
    from hyperspace import ui as ui_mod
    widths = []
    real = ui_mod._readout_width
    monkeypatch.setattr(ui_mod, "_readout_width", lambda t: (widths.append(t), real(t))[1])
    # (the rig's stand-in audio has no transport params: its buttons stubbed)
    monkeypatch.setattr(ui_mod.Panel, "_button", lambda self, *a, **k: False)
    with build_rig(tmp_path) as r:
        r.panel.audio.__dict__.update(mode="file", on=False, playing=True,
                                      position=lambda: 6125.0, duration=lambda: 8400.0)
        frame(r.panel, "audio")
        assert "102:05 / 140:00" in widths



def test_focus_lands_on_a_fold_from_before_stage_2(tmp_path, monkeypatch):
    """Review round 2: a ui.json written by stage 1 names five sections,
    and a page state from before a hot reload may hold only those; landing
    on FX still unfolds and draws the fx section."""
    with build_rig(tmp_path) as r:
        old = {k: k in ("selection", "presets") for k in
               ("selection", "presets", "lookback", "faces", "analyzer")}
        (r.lib.machine / ui_pane.UI_FILE).write_text(json.dumps({"pane": {"open": old}}))
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        for _ in range(2):
            frame(r.panel, "graph")
        st = _st(r)
        st["pane_open"]["open"] = dict(old)          # the stage-1 state, no fx key at all
        r.reg["ui.page"].set(PAGE_KEYS.index("fx"))
        for _ in range(2):
            frame(r.panel)
        assert ui_pane.focused(r.panel) == "fx" and "fx" in st["pane_drawn"]


# ---- stage 3 (U3): the rail goes, every page a section

STAGE3_IDS = {
    "view": "view.bright",
    "routing": "macro.1",
    "hands": "ghost.on",
    "system": "ui.cheatsheet",
}


@pytest.mark.parametrize("key", sorted(STAGE3_IDS))
@pytest.mark.parametrize("width", ["min", "default"])
def test_each_stage3_section_draws_in_the_pane_and_nothing_passes_its_edge(
        tmp_path, monkeypatch, key, width):
    """The four pages stage 2 left, alone open, at the pane's narrowest and
    at its default width: the page's control found by its id inside the
    pane, and no control past the pane's right edge."""
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        r.panel.page = PAGE_KEYS.index("graph")
        d = _tall_driver(r, monkeypatch)
        d.run(d.wait(2))
        st = _st(r)
        st["side_w"] = ui_graph.SIDE_MIN if width == "min" else ui_graph.SIDE_W
        _only(st, key)
        d.run(d.wait(3))
        assert st["pane_drawn"] == [key]
        assert _inside(d.rect(STAGE3_IDS[key]), st["details_rect"])
        spills = _spills(d, st)
        assert not spills, sorted(spills)


def _focus_rig(r, monkeypatch, layout):
    """The real route at a real window: "band" the desk's narrow panel,
    "min" / "default" the column beside the canvas at its two widths."""
    r.panel.desk = layout == "band"
    size = (960, 900) if layout == "band" else WIDE
    imgui.get_io().display_size = imgui.ImVec2(*size)
    d = Driver(step=lambda: frame(r.panel))
    d.record(monkeypatch.setattr)
    d.run(d.wait(2))
    if layout != "band":
        _st(r)["side_w"] = ui_graph.SIDE_MIN if layout == "min" else ui_graph.SIDE_W
    return d


@pytest.mark.parametrize("layout", ["band", "min", "default"])
@pytest.mark.parametrize("key", [k for k in ui_pane.KEYS if k != "selection"])
def test_every_section_focused_lands_in_view_and_inside_the_pane(tmp_path, monkeypatch,
                                                                 key, layout):
    """What replaced "every page fits the window": a section focused in the
    real layout draws in the pane, with room, and no control passes the
    pane's right edge."""
    with build_rig(tmp_path) as r:
        _with_seq(r)
        d = _focus_rig(r, monkeypatch, layout)
        r.reg["ui.page"].set(PAGE_KEYS.index(key))
        d.run(d.wait(4))
        st = _st(r)
        assert key in st["pane_drawn"]
        (_x, y), (_w, h) = st["details_rect"]
        head = d.rect(f"pane.{key}")
        assert y <= head[1] and head[3] <= y + h, (head, st["details_rect"])
        spills = _spills(d, st)
        assert not spills, sorted(spills)


def test_a_fresh_launch_has_no_scrollbar_on_the_pane(pane):
    """Selection and presets open, nothing focused: the sections fit the
    pane exactly, with the spacing after each open body counted."""
    r, _d = pane
    win = imgui.internal.find_window_by_name(_st(r)["pane_window"])
    assert win.scroll_max.y == 0


def test_a_chip_hidden_by_the_focus_opens_what_it_asks_for(tmp_path, monkeypatch):
    """In the band a section open in the fold but hidden by the focus is not
    lit, and a click on it shows it: the band never ends up empty."""
    with build_rig(tmp_path) as r:
        d = _focus_rig(r, monkeypatch, "band")
        st = _st(r)
        assert ui_pane.opened(st, "below")["selection"]
        r.reg["ui.page"].set(PAGE_KEYS.index("fx"))
        d.run(d.wait(3))
        assert st["pane_drawn"] == ["fx"]
        d.run(d.click("pane.selection"), d.park(), d.wait(1))
        assert ui_pane.focused(r.panel) is None
        assert st["pane_drawn"] == ["selection"] and ui_pane.opened(st, "below")["selection"]


def test_the_band_scrolls_on_a_focus(tmp_path, monkeypatch):
    """`scroll_to` promises a scroll in either layout."""
    with build_rig(tmp_path) as r:
        d = _focus_rig(r, monkeypatch, "band")
        asked: list[float] = []
        real = imgui.set_scroll_y
        monkeypatch.setattr(imgui, "set_scroll_y", lambda y: (asked.append(y), real(y))[1])
        r.reg["ui.page"].set(PAGE_KEYS.index("fx"))
        d.run(d.wait(1))
        assert asked == [0.0]


def test_letting_go_by_a_click_moves_the_one_owner_of_the_focus(pane):
    """A click on the focused header: `ui.page` and `Panel.page` say so too,
    and the pane is not scrolled away from where the click was."""
    r, d = pane
    st = _st(r)
    r.reg["ui.page"].set(PAGE_KEYS.index("fx"))
    d.run(d.wait(3))
    assert r.reg["ui.page"].value == PAGE_KEYS.index("fx")
    d.run(d.click("pane.fx"), d.park())
    assert ui_pane.focused(r.panel) is None and PAGE_KEYS[r.panel.page] == "graph"
    assert r.reg["ui.page"].value == PAGE_KEYS.index("graph")
    assert "pane_scroll" not in st


def test_selecting_a_node_does_not_move_the_focus(pane):
    """FX's SHOW chip, OUTPUT's "open on GRAPH", a controller: the canvas is
    always drawn, so the section being worked in stays."""
    r, d = pane
    r.reg["ui.page"].set(PAGE_KEYS.index("output"))
    d.run(d.wait(2))
    ui_graph.select_node(r.panel, "output.all")
    d.run(d.wait(2))
    assert ui_pane.focused(r.panel) == "output" and "output" in _st(r)["pane_drawn"]


def test_the_picked_words_ask_what_is_on_screen_not_the_focus(tmp_path, monkeypatch):
    """ROUTING's body drawn is what "its line is framed" means: unfolded by a
    click with the focus elsewhere it counts; focused, then folded, it does
    not."""
    from test_ui_shell import _control, _learn_over

    from hyperspace import ui_desk
    with build_rig(tmp_path) as r:
        d = _focus_rig(r, monkeypatch, "default")
        st = _st(r)
        lrn = _learn_over(r)
        c = _control("D3")
        lrn.pick(c.source)
        table = r.router.table
        d.run(d.wait(1))
        assert "framed" not in ui_desk.pick_line(r.panel, table, c)[0]
        d.run(d.click("pane.routing"), d.park(), d.wait(1))       # a click: the page elsewhere
        assert PAGE_KEYS[r.panel.page] != "routing" and "routing" in st["pane_drawn"]
        assert "framed" in ui_desk.pick_line(r.panel, table, c)[0]
        d.run(d.click("pane.routing"), d.park(), d.wait(1))
        r.reg["ui.page"].set(PAGE_KEYS.index("routing"))
        d.run(d.wait(2))
        assert "framed" in ui_desk.pick_line(r.panel, table, c)[0]
        d.run(d.click("pane.routing"), d.park(), d.wait(1))       # its own header: lets go
        assert "framed" not in ui_desk.pick_line(r.panel, table, c)[0]


def test_a_macro_rows_chips_stay_beside_the_knob_where_it_fits(tmp_path, monkeypatch):
    """Eight macro rows are one line each at the default width beside a
    roomy body, not two: the slider's room is counted once."""
    with build_rig(tmp_path) as r:
        d = _focus_rig(r, monkeypatch, "default")
        _st(r)["side_w"] = 480.0
        r.reg["ui.page"].set(PAGE_KEYS.index("routing"))
        d.run(d.wait(3))
        knob, one = d.rect("macro.1"), d.rects["+ base"]
        assert one[0] >= knob[2] - 1


# ---------------------------------------------------------------- the paper cuts (row 731)

def _analyzer_at(r, monkeypatch, width):
    r.panel.desk = False
    r.panel.page = PAGE_KEYS.index("graph")
    d = _tall_driver(r, monkeypatch)
    d.run(d.wait(2))
    st = _st(r)
    st["side_w"] = width
    _only(st, "analyzer")
    return d, st


def test_save_as_patch_and_update_patch_keep_inside_the_narrowest_pane(tmp_path, monkeypatch):
    """#364's 19 px: the two chips one row where they fit, and two where not."""
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        r.lib.load("presets", "party-noita")
        r.lib.presets.groups = []
        frame(r.panel, "graph")
        entry = ui_graph.group_nodes(r.panel, ["render:warp", "render:doublevision"])
        entry["patch"] = "noita-core"
        d = _tall_driver(r, monkeypatch)
        d.run(d.wait(2))
        st = _st(r)
        st["select_group"] = entry["id"]
        for width, across in ((ui_graph.SIDE_MIN, False), (ui_graph.SIDE_MIN + 200, True)):
            st["side_w"] = width
            d.run(d.wait(3))
            save = d.rect("save as patch…##graph.group")
            update = d.rect("update patch##graph.group")
            assert (update[1] == save[1]) is across
            assert not _spills(d, st), sorted(_spills(d, st))


@pytest.mark.parametrize("width", [ui_graph.SIDE_MIN, ui_graph.SIDE_W])
def test_the_analyzers_scene_combo_keeps_its_room_and_nothing_collides(tmp_path, monkeypatch,
                                                                       width):
    """AZ's report at 240 px: the combo collapsed to nothing beside its label
    and Reset all; the AUTO chip and the transfer row drew over each other."""
    with build_rig(tmp_path) as r:
        d, st = _analyzer_at(r, monkeypatch, width)
        d.run(d.wait(3))
        assert not _spills(d, st), sorted(_spills(d, st))
        scene = d.rect("scene.select")
        assert scene[2] - scene[0] >= ui.SCENE_COMBO_MIN
        reset = d.rect(next(k for k in d.rects if k.endswith("##scene.reset_all")))
        fn, curve = d.rect("band.sel.fn"), d.rect("band.sel.curve")
        norm = d.rect(next(k for k in d.rects if k.endswith("##norm")))
        for a, b in ((scene, reset), (norm, fn), (fn, curve), (norm, curve)):
            apart = a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
            assert apart, (a, b)


def test_the_analyzers_title_stays_clear_of_its_chips_at_every_width(tmp_path, monkeypatch):
    drawn: list[tuple[str, tuple[float, float, float, float]]] = []
    real = imgui.text_disabled

    def noted(s, *a):
        real(s, *a)
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        drawn.append((s, (lo.x, lo.y, hi.x, hi.y)))
    monkeypatch.setattr(imgui, "text_disabled", noted)
    with build_rig(tmp_path) as r:
        d, st = _analyzer_at(r, monkeypatch, ui_graph.SIDE_MIN)
        for width in (ui_graph.SIDE_MIN, ui_graph.SIDE_W, 500.0):
            st["side_w"] = width
            d.run(d.wait(3))
            hz = next(rect for s, rect in reversed(drawn) if s.endswith(" Hz"))
            norm = d.rect(next(k for k in d.rects if k.endswith("##norm")))
            assert hz[2] <= norm[0] or hz[3] <= norm[1], (width, hz, norm)
            (x, _y), (w, _h) = st["details_rect"]
            assert hz[2] <= x + w


def test_the_meter_tags_do_not_touch_at_the_narrowest_pane(tmp_path, monkeypatch):
    tags: dict[str, tuple[float, float]] = {}
    real = imgui.text_colored

    def noted(color, s, *a):
        real(color, s, *a)
        tags[s] = (imgui.get_item_rect_min().x, imgui.get_item_rect_max().x)
    monkeypatch.setattr(imgui, "text_colored", noted)
    with build_rig(tmp_path) as r:
        d, _ = _analyzer_at(r, monkeypatch, ui_graph.SIDE_MIN)
        d.run(d.wait(3))
        spans = sorted(tags[n] for n in r.chain.band_names)
        assert all(a[1] < b[0] for a, b in itertools.pairwise(spans)), spans


def test_the_size_of_a_tag_and_the_hint_a_plot_shows():
    assert ui.tag_px(lambda px: 2 * px, 40.0) == ui.FONT_MICRO     # room: as it was
    assert ui.tag_px(lambda px: 2 * px, 22.0) == ui.TAG_SIZES[1]
    assert ui.tag_px(lambda px: 30.0 if px > 10 else 20.0, 25.0) == ui.TAG_SIZES[-1]   # measured
    assert ui.tag_px(lambda px: 99.0, 10.0) == ui.TAG_SIZES[-1]
    long, short = ui_bands.HINT, ui_bands.HINT_SHORT
    assert ui_bands.hint_for(len(long), len) == long
    assert ui_bands.hint_for(len(long) - 1, len) == short
    assert ui_bands.hint_for(len(short) - 1, len) == ""


def test_every_tag_shows_at_six_bands_and_none_touch_at_the_most(tmp_path, monkeypatch):
    """The six at the narrowest all read; at sixteen (`N_MAX`) a tag that
    would still touch is left out, and the selected band's never is."""
    tags: dict[str, tuple[float, float]] = {}
    real = imgui.text_colored

    def noted(color, s, *a):
        real(color, s, *a)
        tags[s] = (imgui.get_item_rect_min().x, imgui.get_item_rect_max().x)
    monkeypatch.setattr(imgui, "text_colored", noted)
    with build_rig(tmp_path) as r:
        d, _ = _analyzer_at(r, monkeypatch, ui_graph.SIDE_MIN)
        d.run(d.wait(3))
        assert set(r.chain.band_names) <= set(tags)
        while r.chain.n < N_MAX:
            r.panel.control.add_band()
        r.panel.control.selb = 7
        tags.clear()
        d.run(d.wait(1))
        tags.clear()
        d.step()
        shown = sorted(tags[n] for n in r.chain.band_names if n in tags)
        assert r.chain.band_names[7] in tags and 1 < len(shown) < N_MAX
        assert all(a[1] < b[0] for a, b in itertools.pairwise(shown)), shown


def test_tags_shown_keeps_the_first_and_never_a_touching_pair():
    spans = [(float(k), k + 2.5) for k in range(0, 12, 2)]
    assert ui.tags_shown(spans, 3, 0.0) == [0, 3, 5]
    assert ui.tags_shown([(0.0, 1.0), (2.0, 3.0)], 1, 0.5) == [0, 1]
    assert ui.tags_shown([], 0) == []


class _Plot:
    """A plot's draw list, noting the text drawn on it."""

    def __init__(self, real, said):
        self.real, self.said = real, said

    def add_text(self, pos, color, text, *a):
        self.said.append(text)
        self.real.add_text(pos, color, text, *a)

    def __getattr__(self, name):
        return getattr(self.real, name)


def _hint_rig(monkeypatch):
    """What the plot's list is told, and where the plot is."""
    said, at, tips = [], [], []
    real_list, real_pos = implot.get_plot_draw_list, implot.get_plot_pos
    monkeypatch.setattr(implot, "get_plot_draw_list", lambda: _Plot(real_list(), said))

    def pos():
        p = real_pos()
        at[:] = [(p.x, p.y)]
        return p
    monkeypatch.setattr(implot, "get_plot_pos", pos)
    monkeypatch.setattr(ui, "tooltip", tips.append)
    return said, at, tips


def test_the_spectrogram_says_the_hint_that_fits_at_each_width(tmp_path, monkeypatch):
    said, _at, _tips = _hint_rig(monkeypatch)
    with build_rig(tmp_path) as r:
        d, st = _analyzer_at(r, monkeypatch, ui_graph.SIDE_MIN)
        d.run(d.wait(3))
        assert ui_bands.HINT_SHORT in said and ui_bands.HINT not in said
        st["side_w"] = 500.0
        d.run(d.wait(3))
        said.clear()
        d.run(d.wait(1))
        assert ui_bands.HINT in said and ui_bands.HINT_SHORT not in said


def test_the_short_hints_tooltip_only_over_a_plot_nothing_covers(tmp_path, monkeypatch):
    """Hovered it says the long form; not during a drag on the plot, and not
    through an open list drawn over it."""
    _said, at, tips = _hint_rig(monkeypatch)
    with build_rig(tmp_path) as r:
        d, _ = _analyzer_at(r, monkeypatch, ui_graph.SIDE_MIN)
        d.run(d.wait(3))
        over = (at[0][0] + 12, at[0][1] + 6)
        d.run(d.move(over), d.wait(2))
        assert ui_bands.HINT in tips
        tips.clear()
        d.run(d.press(True), d.wait(2))
        assert ui_bands.HINT not in tips
        d.run(d.press(False), d.park())
        d.run(d.click("scene.select"), d.wait(2))    # its list opens down over the plot
        tips.clear()
        d.run(d.move(over), d.wait(2))
        assert ui_bands.HINT not in tips
