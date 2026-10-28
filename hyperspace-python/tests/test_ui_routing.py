"""The ROUTING page (moved out of test_ui_bands.py, audit D5): the matrix
over test_ui_shell's headless rig — routes, a live lane, edits landing in
bindings.json, the referee's refusals, the Replace / Keep prompt, the
macro scales, the preset strip through the library.

Plan 28 N7: the routes and the modifiers are the GRAPH page's now —
ROUTING draws a pointer line there in their place, and its desk, macros,
session and sinks as before. The route rows are ROUTING's own function
still (`ui_routing._row`), drawn by GRAPH's side pane (`ui_graph.route_rows`);
the tests of a row's widgets draw them there (`rows`).
"""

import json
from dataclasses import replace

import pytest
from imgui_bundle import imgui
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import routing, ui_graph, ui_presets, ui_routing
from hyperspace.bands import CEIL
from hyperspace.library import LibraryError
from hyperspace.params import Kind
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.ui import PAGE_KEYS


@pytest.fixture()
def rig(shell_rig):  # noqa: F811 — pytest hands the shell's rig through under its name
    return shell_rig


def rows(panel) -> None:
    """One frame of the route rows as GRAPH's side pane draws them
    (`ui_graph.route_rows`: ROUTING's `_row` per route, the one table),
    the panel's ghost count started afresh as `Panel.draw` does."""
    panel.ghosts = 0
    imgui.new_frame()
    imgui.begin("rows")
    ui_graph.route_rows(panel, ui_routing.router_of(panel).table.routes())
    imgui.end()
    imgui.end_frame()


def _with_router(rig, tmp_path):
    table = Bindings.factory(path=routing.bindings_path(tmp_path))
    table.set_routes(routing.legacy6_routes())     # a house preset's performer rows
    rig.panel.router = Router(rig.reg, table)
    return rig.panel.router


def test_routing_page_draws_routes(rig, tmp_path):
    panel = rig.panel
    frame(panel, "routing")                     # no router: says so
    router = _with_router(rig, tmp_path)
    assert len(router.table.routes()) == 12
    frame(panel)
    frame(panel)
    assert "bindings" not in panel.library.kinds           # no routing-preset strip here
    assert panel.library.current("presets") is None        # the head: nothing loaded
    assert not panel.library.is_dirty("presets")


def test_routing_page_live_lane_draws_ghost_and_bar(rig, tmp_path):
    panel, reg, chain = rig.panel, rig.reg, rig.chain
    # one route only: the factory table's push rows on the rotation rates
    # would each draw a ghost bar under a live lane; one row keeps the count
    # about this row
    router = panel.router = Router(reg, Bindings([Binding("lane:1", "view.bright", "push", 0.5)]))
    panel.audio.on = True
    chain.out[:] = 0.0
    chain.out[1] = CEIL * 0.5
    router.modulate(chain)
    reg.apply()
    bright = reg["view.bright"]
    assert bright.modulated
    assert ui_routing._live(panel, router, router.table.routes()[-1]) == pytest.approx(0.5)
    frame(panel, "routing")
    assert panel.ghosts == 0                    # N7: ROUTING draws no route row now
    rows(panel)                                 # the row, as GRAPH's side pane draws it
    assert panel.ghosts == 1                    # the live bar's red hairline
    panel.audio.on = False
    assert ui_routing._live(panel, router, router.table.routes()[-1]) is None
    reg.apply()
    rows(panel)
    assert panel.ghosts == 0


def test_routing_add_and_delete(rig, tmp_path):
    panel, reg = rig.panel, rig.reg
    router = _with_router(rig, tmp_path)
    frame(panel, "routing")
    b = ui_routing.add_route(panel, "view.bright")
    assert b.source == "lane:0" and b.op == "push" and b.value == 0.5
    assert router.table.routes_to("view.bright") == [b]
    frame(panel)
    reg["band.select"].set(3)
    b2 = ui_routing.add_route(panel, "camera.zoom", depth=-0.25)
    assert b2.source == "lane:3" and b2.value == -0.25
    frame(panel)
    router.table.remove(b)
    assert not router.table.routes_to("view.bright") and b2 in router.table.routes()
    frame(panel)


def _on_disk(tmp_path):
    return Bindings.load(routing.bindings_path(tmp_path), legacy_midi=None)


def test_routing_page_edits_change_the_preset_not_bindings_json(rig, tmp_path):
    """Plan 13 §3.3: a route deleted, added or edited on the page (or from
    the context menu) is the loaded preset's — the table changes, the
    preset's dirty dot moves, and bindings.json is never written."""
    panel, lib = rig.panel, rig.panel.library
    router = rig.router                             # the one the rig's Presets loads into
    router.table.write()
    path = routing.bindings_path(tmp_path)
    assert router.table.path == path
    before = (path.read_text(), path.stat().st_mtime_ns)
    lib.load("presets", "BIG BLUE WAVE")
    frame(panel, "routing")
    assert not lib.is_dirty("presets")
    for b in list(router.table.routes()):
        router.table.remove(b)
    frame(panel)
    assert router.table.routes() == [] and lib.is_dirty("presets")
    b = ui_routing.add_route(panel, "view.bright")   # the context menu's add, page unseen
    assert [x.target for x in router.table.routes()] == ["view.bright"]
    b.value = -0.25
    frame(panel)
    frame(panel)
    assert (path.read_text(), path.stat().st_mtime_ns) == before
    assert _on_disk(tmp_path).routes() == []        # the file never holds a route (WP5)


def test_the_routing_page_shows_the_referees_refusals(rig, tmp_path):
    """One performer per target: a preset's second owner is listed as
    dropped until the next edit; adding a route on an owned target raises
    the prompt and leaves the table alone until it is answered; a new
    push row has no rest of its own (it rests where its source does); one
    that has shows an "auto" chip."""
    panel = rig.panel
    router = _with_router(rig, tmp_path)
    router.table.set_routes([Binding("hand:7", "view.bright", "position"),
                             Binding("hand:1", "view.bright", "push", 0.5)])
    router.feed("hand", [0.5] * 20)
    router.labels["hand"] = [f"ax{i}" for i in range(12)]
    router.rests["hand"] = [0.5, 0.0] * 6 + [0.0] * 8
    router.gates["hand"] = [(14, "L ind")]
    frame(panel, "routing")
    assert [b.source for b, _ in router.table.dropped] == ["hand:1"]
    assert ui_routing.add_route(panel, "view.bright") is None            # owned: the prompt
    old, new = ui_routing.prompt(panel)
    assert (old.source, new.source, new.target) == ("hand:7", "lane:0", "view.bright")
    assert ui_routing._state(panel)["error"] == ""
    assert [b.source for b in router.table.routes_to("view.bright")] == ["hand:7"]
    frame(panel)                                                           # the notice, the modal
    ui_routing.answer(panel, False)                                        # Keep
    assert ui_routing.prompt(panel) is None
    assert [b.source for b in router.table.routes_to("view.bright")] == ["hand:7"]
    b = ui_routing.add_route(panel, "view.speed", source="hand:2")        # free: added
    assert (b.op, b.rest) == ("push", None) and router.table.dropped == []  # an edit clears
    assert router.rest_of(b.source) == 0.5                                 # what the row uses
    assert ui_routing.add_route(panel, "view.depth4", source="hand:1").rest is None
    b.rest = 0.1                                                           # the row's own: "auto" shows
    frame(panel)
    frame(panel)
    assert [x.target for x in router.table.routes()] == [
        "view.bright", "view.speed", "view.depth4"]
    assert not routing.bindings_path(tmp_path).exists()                   # the preset's, no file
    # the row's checkbox goes through the referee too: waking a row onto
    # a taken target leaves it off and says why
    off = router.table.add(Binding("hand:3", "view.speed", "push", 0.2, enabled=False))
    with pytest.raises(routing.Owned):
        router.table.enable(off)
    assert not off.enabled
    frame(panel)


def test_the_replace_prompt_swaps_the_owner_or_leaves_the_table(rig, tmp_path, monkeypatch):
    """Plan 09 WP5, exit criterion 3 without the mouse: a second performer
    on a target is a question, not an error. *Replace* swaps the owner (in
    the loaded preset — no file is written, plan 13 §3.3); *Keep* leaves
    the table untouched. The same modal
    serves the page's own edits (add, a retarget, a row waking up) and a
    hand learn the shared `Learn` is holding in `pending` — no MIDI adapter
    anywhere (audit B3) — and it draws on whatever page is open. The owner
    is named as its adapter names it."""
    from hyperspace.learn import Learn

    panel, reg = rig.panel, rig.reg
    router = _with_router(rig, tmp_path)
    table = router.table
    table.set_routes([Binding("hand:7", "view.bright", "position", when="hand:18")])
    router.labels["hand"] = ["L x", "L height"] + ["?"] * 5 + ["R height"] + ["?"] * 11
    router.gates["hand"] = [(18, "R ind")]
    router.labels["lfo"] = ["LFO 1", "LFO 2", "LFO 3", "LFO 4"]
    owner = table.owner("view.bright")
    assert router.describe(owner) == "R height positions while R ind"
    assert owner.describe() == "hand 7 positions while hand:18"       # the row's own words
    frame(panel, "view")                                               # nothing asked: no modal
    assert not ui_routing._state(panel)["modal"] and ui_routing.prompt(panel) is None
    # add: Replace swaps
    assert ui_routing.add_route(panel, "view.bright", source="lfo:0", depth=0.5) is None
    old, new = ui_routing.prompt(panel)
    assert old is owner and router.describe(new) == "LFO 1 pushes +0.5"
    frame(panel)                                                       # the view page: the modal is up
    assert ui_routing._state(panel)["modal"]
    assert table.owner("view.bright") is owner                         # untouched while it asks
    ui_routing.answer(panel, True)
    assert table.owner("view.bright").source == "lfo:0" and owner not in table.bindings
    assert not routing.bindings_path(tmp_path).exists()                # no file
    frame(panel)
    assert ui_routing.prompt(panel) is None
    # a retarget onto an owned target asks; Keep leaves both rows where they were
    speed = table.add(Binding("hand:1", "view.speed", "position"))
    cur = table.owner("view.bright")
    ui_routing.ask(panel, cur, replace(speed, target="view.bright"),
                   lambda: (table.remove(cur), setattr(speed, "target", "view.bright")))
    frame(panel, "routing")
    ui_routing.answer(panel, False)
    assert speed.target == "view.speed" and table.owner("view.bright") is cur
    # a hand learn the Learn object holds is the same question, answered through it
    lrn = panel.learn = Learn(reg, table)
    lrn.arm("view.bright")
    lrn.learn_source("hand:1", when="hand:18")
    assert lrn.pending is not None
    old, new = ui_routing.prompt(panel)
    assert old is cur and (new.source, new.when) == ("hand:1", "hand:18")
    assert router.describe(new) == "L height positions while R ind"
    frame(panel)
    assert ui_routing._state(panel)["modal"]
    ui_routing.answer(panel, False)                                    # Keep
    assert lrn.pending is None and table.owner("view.bright") is cur and "kept" in lrn.last
    lrn.arm("view.bright")
    lrn.learn_source("hand:1")
    writes, real_write = [], table.write
    monkeypatch.setattr(table, "write", lambda: (writes.append(1), real_write()))
    ui_routing.answer(panel, True)                                     # Replace: the axis moves
    assert writes == []                                                # the preset's: no file
    got = table.owner("view.bright")
    assert got.source == "hand:1" and cur not in table.bindings
    assert not table.routes_to("view.speed")                           # one axis, one param
    frame(panel)
    assert ui_routing.prompt(panel) is None and not ui_routing._state(panel)["modal"]
    # the tooltip names the performer the same way
    reg["view.bright"].modulate(0.1)
    reg.apply()
    assert panel._performer(reg["view.bright"]) == "performed by L height positions"
    # nothing pending: answering is a no-op
    ui_routing.answer(panel, True)
    assert table.owner("view.bright") is got
    # the page's two in-place commits, and the race: a second performer
    # lands on the target while the question is held — Replace removes
    # whoever holds it then, and exactly one owner remains
    asleep = table.add(Binding("lfo:1", "view.bright", "push", 0.2, enabled=False))
    with pytest.raises(routing.Owned):
        table.enable(asleep)
    ui_routing.ask(panel, got, asleep, lambda: ui_routing._wake(router, asleep))
    table.remove(got)
    landed = table.add(Binding("lane:3", "view.bright", "push", 0.3))   # while the prompt was up
    ui_routing.answer(panel, True)
    assert asleep.enabled and table.owner("view.bright") is asleep and landed not in table.bindings
    assert [b for b in table.bindings if b.is_performer and b.target == "view.bright"] == [asleep]
    frame(panel, "routing")
    mover = table.add(Binding("hand:2", "view.speed", "position"))
    ui_routing.ask(panel, asleep, replace(mover, target="view.bright"),
                   lambda: ui_routing._retarget(router, mover, "view.bright"))
    ui_routing.answer(panel, True)
    assert mover.target == "view.bright" and table.owner("view.bright") is mover
    assert asleep not in table.bindings
    # the held learn's Replace goes through the same door: the row that
    # took the target meanwhile goes, not the one the question named
    lrn.arm("view.bright")
    lrn.learn_source("hand:3")
    assert lrn.pending[1] is mover
    table.remove(mover)
    meanwhile = table.add(Binding("lane:4", "view.bright", "push", 0.3))
    ui_routing.answer(panel, True)
    assert table.owner("view.bright").source == "hand:3" and meanwhile not in table.bindings
    assert len(table.routes_to("view.bright")) == 1
    # the modal shows with the panel hidden, and a question withdrawn
    # while it was up (a new learn armed) takes the popup down with it
    lrn.arm("view.bright")
    lrn.learn_source("hand:5")
    assert lrn.pending is not None
    panel.open = False
    frame(panel)
    assert ui_routing._state(panel)["modal"]
    lrn.arm("view.speed")                                           # forgets the held learn
    assert lrn.pending is None
    frame(panel)
    frame(panel)
    assert not ui_routing._state(panel)["modal"]
    lrn.arm("view.bright")                                          # and a new question opens again
    lrn.learn_source("hand:5")
    frame(panel)
    assert ui_routing._state(panel)["modal"]
    ui_routing.answer(panel, False)
    panel.open = True


def test_the_conflict_sheet_asks_per_row_preselected_to_the_patch(rig):
    """Plan 40 T3 (D3, D9): a spawn whose K1 collides (acid-wash into
    party-trip, where K1 is view.bright) puts up the conflict sheet in the
    same modal, ahead of any Replace / Keep question: its title, one row
    per conflict in words, every row on the patch; **keep all existing**
    flips them, **take all** back; the wants the rig lacks beneath. While it
    is up the hands learn nothing (the armed learn waits). **keep all
    existing** + Spawn lands the patch with K1 left on brightness — the
    patch's row not in the table, kept by the group and said; Cancel on a
    second spawn lands nothing, not even an undo step."""
    from test_graph_groups import state, watch, with_patch

    from hyperspace import graphview, undo
    from hyperspace.learn import Learn

    panel, reg = rig.panel, rig.reg
    table = rig.router.table
    with_patch(rig)
    rig.lib.load("presets", "party-trip")
    frame(panel, "graph")
    lrn = panel.learn = Learn(reg, table)
    lrn.arm("view.speed")
    assert ui_graph.spawn(panel, "acid-wash", (0.0, 0.0)) is None
    landing, choices = ui_routing.sheet(panel)
    assert choices == {0: "patch"}                                     # D9: the patch's
    assert ui_routing.conflict_words(landing.conflicts[0]) == ("K1", "fx.acid.speed",
                                                               "view.bright")
    assert ui_routing.sheet_title(panel, landing) == "spawn acid wash into TRIP"   # (its name)
    assert ui_routing.sheet_wants(panel, landing) == [
        "apc40 (not in this rig): K1", "leap (not in this rig): right hand y"]
    frame(panel)
    st = ui_routing._state(panel)
    assert st["modal"] and st["sheet"]
    # the hands learn nothing while it is up: the learn stays armed, no row lands
    assert lrn.held and not lrn.accepts("hand:right.x")
    lrn.learn_source("hand:right.x")
    assert lrn.learning == "view.speed" and table.owner("view.speed") is None
    ui_routing.keep_all(panel)
    assert ui_routing.sheet(panel)[1] == {0: "preset"}
    ui_routing.keep_all(panel, "patch")                                # take all
    assert ui_routing.sheet(panel)[1] == {0: "patch"}
    ui_routing.choose(panel, 0, "preset")
    assert ui_routing.sheet(panel)[1] == {0: "preset"}
    u = watch(rig)
    try:
        n = len(u.stack)
        assert ui_routing.settle_sheet(panel, True) is None             # Spawn
        assert ui_routing.sheet(panel) is None and len(u.stack) == n + 1
        assert not lrn.held and lrn.accepts("hand:right.x")
        assert [b.target for b in table.desk() if b.source == "cc:0:48"] == ["view.bright"]
        assert not [b for b in table.bindings if b.target == "fx.acid.speed" and b.is_midi]
        (g,) = rig.lib.presets.groups
        (kept,) = g["kept_by_host"]
        assert graphview.kept_words(kept) == "K1 kept by the preset"
        assert "1 row kept by the preset" in ui_graph._state(panel)["said"]
        frame(panel)
        assert not ui_routing._state(panel)["modal"]
        # a second spawn, cancelled: nothing lands, no step
        before = state(rig)
        assert ui_graph.spawn(panel, "acid-wash", (0.0, 300.0)) is None
        frame(panel)
        assert ui_routing._state(panel)["sheet"]
        assert ui_routing.settle_sheet(panel, False) is None
        assert state(rig) == before and len(u.stack) == n + 1
        assert ui_graph._state(panel)["said"] == "spawn of acid wash cancelled: nothing landed"
    finally:
        undo.install(None)


def test_the_sheet_is_drawn_ahead_of_a_replace_question_up_with_it(rig, monkeypatch):
    """Plan 40 T3 (D3): a Replace / Keep question and a spawn's conflict
    sheet up together — the modal draws the sheet (its **Spawn**, not
    **Replace**); once the sheet is answered the question comes next, in
    the same modal, still unanswered."""
    from test_graph_groups import with_patch

    from hyperspace import ui
    panel, table = rig.panel, rig.router.table
    with_patch(rig)
    rig.lib.load("presets", "party-trip")
    frame(panel, "graph")
    old = Binding("lfo:0", "view.speed", "push", 0.5)
    new = Binding("lfo:1", "view.speed", "push", 0.5)
    ui_routing.ask(panel, old, new, lambda: None)
    assert ui_graph.spawn(panel, "acid-wash", (0.0, 0.0)) is None
    drawn, real_chip = [], ui.chip
    monkeypatch.setattr(ui_routing.ui, "chip", lambda label, *a, **k: (
        drawn.append(label), real_chip(label, *a, **k))[1])
    frame(panel)
    st = ui_routing._state(panel)
    assert st["modal"] and st["sheet"]
    assert "Spawn##sheet" in drawn and "Replace" not in drawn
    assert ui_routing.prompt(panel) is not None                        # still asking
    ui_routing.settle_sheet(panel, False)
    drawn.clear()
    frame(panel)
    assert st["modal"] and not st["sheet"]
    assert "Replace" in drawn and "Spawn##sheet" not in drawn
    ui_routing.answer(panel, False)
    assert table.owner("view.speed") is None


def test_the_scale_choices_leave_out_the_macros_and_a_macro_shows_its_owner(
        rig, tmp_path, monkeypatch):
    """Plan 13 §2.4: a macro scales a route as its depth subscriber, so the
    row's scale combo offers every other continuous param (master.gain
    among them) and no macro, and the row shows the macro as a read-only
    "× macro.N" chip. The macros are still targets like any other, and draw
    in a strip over the rows as the panel's own sliders — a hand that
    positions one shows as the usual `base → effective` readout and a ghost."""
    panel, reg = rig.panel, rig.reg
    ids = [p.id for p in ui_routing._scales(panel)]
    assert "master.gain" in ids and not any(i.startswith("macro.") for i in ids)
    assert all(p.kind is Kind.CONTINUOUS and not p.alias for p in ui_routing._scales(panel))
    assert {p.id for p in ui_routing._targets(panel)} >= {f"macro.{k}" for k in range(1, 9)}
    # never the row's own target (a self-scaled push strobes)
    assert "view.bright" not in {p.id for p in ui_routing._scales(panel, "view.bright")}
    table = Bindings([
        Binding("lane:0", "view.bright", "push", 0.5),
        Binding("hand:0", "macro.2", "position"),
    ])
    table.set_macros({"macro.2": {"subs": [
        {"depth": {"source": "lane:0", "target": "view.bright"}, "from": 0.0, "to": 1.0}]}})
    router = panel.router = Router(reg, table)
    assert ui_routing._depth_chips(router, table.bindings[0]) == ["× macro.2"]
    router.feed("hand", [0.6])
    router.labels["hand"] = ["R height"]
    fmts: list[str] = []
    real = imgui.slider_float
    # what the slider shows: imgui reads the readout as a printf format,
    # so the panel hands it "%%" for each "%" it is to print
    monkeypatch.setattr(imgui, "slider_float",
                        lambda label, v, lo, hi, fmt="%.3f", *a: (
                            fmts.append(fmt.replace("%%", "%")),
                            real(label, v, lo, hi, fmt, *a))[1])
    frame(panel, "routing")
    assert panel.ghosts == 0 and "100 %" in fmts and "100 % → 60 %" not in fmts
    router.modulate()
    reg.apply()
    macro = reg["macro.2"]
    assert macro.modulated and macro.text() == "100 %" and panel._eff_text(macro) == "60 %"
    fmts.clear()
    frame(panel)
    assert "100 % → 60 %" in fmts                  # the strip's slider, under a performer
    assert panel.ghosts == 1                       # its ghost bar (N7: no route row here) …
    rows(panel)
    assert panel.ghosts == 1                       # … and the row's live hairline, on GRAPH's pane
    router.feed("hand", None)
    router.modulate()
    reg.apply()
    frame(panel)
    assert not macro.modulated and panel.ghosts == 0


def test_the_routing_page_has_no_conflicting_ids(rig, tmp_path, monkeypatch):
    """Every widget on the ROUTING page has its own imgui id, the macro
    strip's included — the rows are under push_id(k), so the ids are
    resolved through the stack (get_id) rather than compared as labels."""
    panel = rig.panel
    router = _with_router(rig, tmp_path)
    router.table.add(Binding("hand:0", "macro.2", "position"))
    router.table.set_macros({                       # the subscriber lines too (plan 13 WP4)
        "macro.1": {"subs": [{"base": "view.depth4"}, {"base": "view.speed"},
                             {"depth": {"source": "hand:0", "target": "macro.2"}}]},
        "macro.2": {"subs": [{"base": "view.depth4"}]}})
    router.feed("hand", [0.5] * 20)
    router.labels["hand"] = [f"ax{i}" for i in range(12)]
    router.gates["hand"] = [(14, "L ind")]
    ids: list[int] = []
    for fn in ("button", "checkbox", "slider_float", "slider_int", "combo", "begin_combo",
               "invisible_button", "arrow_button"):
        real = getattr(imgui, fn)

        def rec(label, *a, _real=real, **k):
            ids.append(imgui.get_id(label))
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    frame(panel, "routing")
    ids.clear()
    frame(panel)
    assert len(ids) > 8 * 1                       # eight knobs (N7: the rows are GRAPH's)
    dup = {i for i in ids if ids.count(i) > 1}
    assert not dup, f"conflicting ids {sorted(dup)}"
    ids.clear()
    rows(panel)                                   # the rows, as GRAPH's side pane lists them
    assert len(ids) > 13 * 4                      # four-plus widgets a row
    dup = {i for i in ids if ids.count(i) > 1}
    assert not dup, f"conflicting ids {sorted(dup)}"


def _drawn(monkeypatch) -> tuple[list[str], list[str]]:
    """Record every text the page draws, and every combo's preview."""
    texts: list[str] = []
    previews: list[str] = []
    real = {f: getattr(imgui, f) for f in ("text", "text_disabled", "text_wrapped",
                                            "text_colored", "begin_combo")}
    monkeypatch.setattr(imgui, "text", lambda s: (texts.append(s), real["text"](s))[1])
    monkeypatch.setattr(imgui, "text_disabled",
                        lambda s: (texts.append(s), real["text_disabled"](s))[1])
    monkeypatch.setattr(imgui, "text_wrapped",
                        lambda s: (texts.append(s), real["text_wrapped"](s))[1])
    monkeypatch.setattr(imgui, "text_colored",
                        lambda c, s: (texts.append(s), real["text_colored"](c, s))[1])
    monkeypatch.setattr(imgui, "begin_combo",
                        lambda label, preview, *a: (previews.append(preview),
                                                    real["begin_combo"](label, preview, *a))[1])
    return texts, previews


def test_the_routing_page_is_one_page_over_the_loaded_preset(rig, tmp_path, monkeypatch):
    """Plan 13 decision 13: the page is the loaded preset — the head names
    it (its dot, the layer, the last learn — a refusal among them — and the
    desk rows its load dropped), then its routes, its desk (each row, and
    each preset control it leaves dark), its macros with their subscribers
    (a param two macros set marked), and the session's rows read-only. An
    edit on the page marks the preset dirty and writes no file."""
    from test_presets import put

    from hyperspace.learn import Learn

    panel, lib, reg, table = rig.panel, rig.lib, rig.reg, rig.router.table
    table.write()
    path = routing.bindings_path(tmp_path)
    before = (path.read_text(), path.stat().st_mtime_ns)
    put(tmp_path, "SHOW",
        routes=[{"source": "hand:7", "target": "view.bright", "op": "position"}],
        desk=[{"source": "cc:*:16", "target": "view.speed", "op": "abs", "feedback": "ring"},
              # (scene launch 5: 1–4 are the invariant render toggles, plan 24 C1)
              {"source": "note:0:86", "target": "view.points", "op": "toggle",
               "feedback": "led"},
              {"source": "cc:0:14", "target": "view.bright", "op": "abs"}],  # MASTER: dropped
        macros={"macro.1": {"label": "Heat", "subs": [
                    {"base": "view.depth4", "from": 0.2, "to": 0.8},
                    {"depth": {"source": "hand:7", "target": "view.bright"},
                     "from": 0.0, "to": 1.0}]},
                "macro.2": {"subs": [{"base": "view.depth4", "from": 1.0, "to": 0.0}]}})
    lib.load("presets", "SHOW")
    panel.learn = Learn(reg, table)
    panel.learn.refuse("MASTER fader is invariant (the session's) — not learned")
    texts, previews = _drawn(monkeypatch)
    frame(panel, "routing")
    frame(panel)
    # the head
    assert "SHOW" in texts and "DESK LAYER: PRESET" in texts and "●" not in texts
    assert "learn: MASTER fader is invariant (the session's) — not learned" in texts
    assert any(t.startswith("desk: dropped cc:0:14 → view.bright") and "invariant" in t
               for t in texts)
    assert "bindings" not in lib.kinds                         # no routing-preset strip
    # the routes: a pointer to GRAPH (plan 28 N7), where each row is drawn —
    # with the macro's chip
    assert ui_routing.POINTER in texts and "× macro.1" not in texts
    rows(panel)
    assert "view.bright" in previews and "× macro.1" in texts
    # the desk: its rows by glyph (plan 14 WP7: D1 is device knob 1, G5·9
    # scene launch 5), and the controls it leaves dark
    assert {"DESK  ·  PRESET LAYER", "D1", "G5·9"} <= set(texts)
    assert "device knob 1" not in texts                        # Akai's name: the tooltip
    assert {"view.speed", "view.points"} <= set(previews)
    assert "K1" in texts and "unmapped — dark" in texts
    dark = [f.source for f in ui_routing.unmapped(table)]
    assert "cc:0:48" in dark and "cc:*:16" not in dark and "cc:0:14" not in dark
    assert "cc:0:7" in dark          # S1: the preset's since plan 24 C2, and this one maps none
    # the macros: both subscribers, the shared param marked on both lines
    assert "view.depth4" in previews and any(p.endswith("→ view.bright") for p in previews)
    assert texts.count("shared") >= 2
    assert ui_routing.shared_bases(table) == {"view.depth4": ["macro.1", "macro.2"]}
    # the session, read-only
    assert "the session's — edit bindings.json" in texts
    assert {"S1", "band.0.post", "⇧", "desk.shift", "band.sel.trim"} <= set(texts)
    assert not lib.is_dirty("presets")
    # an edit on the page: a subscriber's `to` dragged
    real = imgui.slider_float
    hit = []

    def drag(label, v, lo, hi, fmt="%.3f", *a):
        if label == "##to" and not hit:
            hit.append(label)
            real(label, v, lo, hi, fmt, *a)
            return True, 0.9
        return real(label, v, lo, hi, fmt, *a)
    monkeypatch.setattr(imgui, "slider_float", drag)
    frame(panel)
    assert table.macros["macro.1"].subs[0].hi == pytest.approx(0.9)
    assert lib.is_dirty("presets")
    texts.clear()
    frame(panel)
    # the head's dot: a disc since plan 19 WP5, no longer the "●" glyph
    assert "head.dot" in ui_presets._state(panel)["rects"]
    assert (path.read_text(), path.stat().st_mtime_ns) == before   # no file written
    # SHIFT latched: the head says so
    table.set_layer("global")
    texts.clear()
    frame(panel)
    assert "DESK LAYER: GLOBAL" in texts


def test_route_a_lane_here_jumps_to_the_page(rig, tmp_path):
    panel, reg = rig.panel, rig.reg
    _with_router(rig, tmp_path)
    frame(panel, "view")
    p = reg["band.sel.atk"]                     # an alias: the route goes to the real param
    real = panel._real(p)
    ui_routing.add_route(panel, real.id)
    reg["ui.page"].set(PAGE_KEYS.index("graph"))      # plan 28 N7: the routes' page
    assert panel.router.table.routes_to("band.0.atk")
    frame(panel)
    assert panel.page == PAGE_KEYS.index("graph")


def test_the_old_routing_presets_step_load_save_as_presets(rig, tmp_path):
    """Was test_routing_presets_step_load_save: the routing presets' kind is
    gone (plan 13 WP5) and what it held is presets — stepped, loaded, saved
    and deleted on the one preset strip's library group, the routes with
    the rest of the preset."""
    panel, lib = rig.panel, rig.panel.library
    router = rig.router                             # the one the rig's Presets loads into
    frame(panel, "routing")
    assert lib.kinds == ("patches", "presets")     # plan 40 T1: patches are spawned
    listing = lib.list("presets")
    assert {"legacy6", "lfo-breathe", "hands-fx", "hands-pinch", "hands-play"} <= set(listing)
    assert [k for k in lib.load("presets", "lfo-breathe")
            if not k.startswith(("env.", "seq."))] == []  # (plan 36 T3: the `/7`'s envelope ids, this rig has none)
    assert rig.reg["lfo.1.sync"].value == 3         # lfo-breathe lands its bases: 1 bar
    assert lib.next("presets") == listing[listing.index("lfo-breathe") + 1]
    lib.load("presets", "legacy6")
    assert rig.view.pattern_mod[0] == 1.0           # legacy6 lands its bases (1: plan 22 B3)
    assert not lib.is_dirty("presets")
    frame(panel)
    # an edit dirties; save as writes the whole preset to the user folder
    router.table.add(Binding("lane:2", "view.bright", "push", 0.3))
    assert lib.is_dirty("presets")
    frame(panel)
    path = lib.save_as("presets", "My Routes")
    assert path == tmp_path / "presets" / "my-routes.json"
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.preset/7" and len(doc["routes"]) == 13
    assert lib.current("presets") == "My Routes" and not lib.is_dirty("presets")
    frame(panel)
    # another preset back: the user route goes, the inputs stay
    inputs = ("key", "pad", "hat", *routing.MIDI_SCHEMES)
    n_inputs = len(router.table.of(*inputs))
    lib.load("presets", "hands-play")
    assert not [b for b in router.table.routes_to("view.bright") if b.source == "lane:2"]
    assert len(router.table.of(*inputs)) == n_inputs
    lib.load("presets", "My Routes")
    assert [b.value for b in router.table.routes_to("view.bright")] == [0.3]
    frame(panel)
    with pytest.raises(LibraryError):
        lib.load("presets", "no-such")
    lib.error = "library: presets: no preset 'no-such'"     # what the strip's guard records
    frame(panel)
    assert lib.delete("presets", "My Routes")


def test_a_route_on_a_session_param_is_marked_session(rig, monkeypatch):
    """Decision register row 19 (a): a preset's route may perform a session
    param — TUMBLE's left height pushes the drive (`master.gain`) — and the
    load keeps it; the page marks that row with a dim "session" and no other."""
    panel, lib, router = rig.panel, rig.panel.library, rig.router
    lib.load("presets", "TUMBLE")
    drive = [b for b in router.table.routes() if b.target == "master.gain"]
    assert [(b.source, b.op) for b in drive] == [("hand:left.y", "push")]
    assert ui_routing.is_session_target(panel, drive[0])
    assert not any(ui_routing.is_session_target(panel, b) for b in router.table.routes()
                   if b is not drive[0])
    texts, _ = _drawn(monkeypatch)
    rows(panel)
    texts.clear()
    rows(panel)                                     # one frame: one mark, on one row
    assert texts.count(ui_routing.SESSION_MARK) == 1
    assert "never changed" in ui_routing.SESSION_TIP


def test_the_base_picker_offers_performance_params_only(rig):
    """D9, review of PR #67: a macro's "+ base" picker offers persisted,
    non-alias performance params — never a session one (the BPM, the
    drive, a band), an alias or a macro — and "+ base" adds one of those."""
    from hyperspace.params import part_of

    panel, reg = rig.panel, rig.reg
    offered = ui_routing.base_targets(panel)
    ids = {q.id for q in offered}
    assert "view.bright" in ids and "fx.mix" in ids
    assert not ids & {"tempo.bpm", "master.gain", "band.sel.trim", "band.0.trim"}
    assert all(part_of(q) == "performance" and q.persist and not q.alias for q in offered)
    assert not any(q.group == "macro" for q in offered)
    assert all(routing.base_refusal(q.id, reg) is None for q in offered)


def test_the_routing_heads_name_field_draws(rig):
    """The head's save as… is the preset strip's name field, over the
    loaded preset (ui_presets._name_field under its own key)."""
    panel, lib = rig.panel, rig.panel.library
    lib.load("presets", "TRIP")
    frame(panel, "routing")
    ui_presets._begin_naming(panel, ui_routing.NAMING, "seed")
    frame(panel)
    ui_routing._save_as(panel, "Mine")                    # what its ok / Enter commits
    ui_presets._state(panel)["naming"] = None
    frame(panel)
    assert lib.current("presets") == "Mine" and not lib.is_dirty("presets")
    assert (rig.lib.home / "presets" / "mine.json").exists()


# ------------------------------------------------------ plan 15 WP1: undo

def test_a_route_delete_and_a_replace_are_undo_steps(rig, tmp_path, monkeypatch):
    """The page's replacing actions each push one undo step before they
    change the table: a route's × (its depth subscribers go with it, and
    come back with it), a desk row's ×, a macro subscriber's ×, and
    Replace in the Replace / Keep prompt — once, also when it lands a held
    learn. Keep is no step."""
    from hyperspace import ui, undo
    from hyperspace.learn import Learn

    panel, reg = rig.panel, rig.reg
    router = _with_router(rig, tmp_path)
    table = router.table
    victim = table.routes()[0]
    table.set_macros({"macro.1": {"label": "amt", "subs": [
        {"depth": {"source": victim.source, "target": victim.target}, "from": 0.0, "to": 1.0},
        {"base": "view.bright", "from": 0.2, "to": 0.8}]}}, reg)
    router.follow_macros()
    u = undo.Undo(reg, table, on_restore=router.sync_macros)
    undo.install(u)
    clock = [0.0]

    def quiet():                                        # a tick, then a second of nothing
        for _ in range(2):
            clock[0] += 1.0
            u.tick(clock[0])

    def state():
        return ([b.to_json() for b in table.routes()], [b.to_json() for b in table.desk()],
                table.macros_doc())

    def click(what):
        """One frame of the page with the first × of `what` pressed."""
        go = [what]
        row, sub, cell, chip = (ui_routing._row, ui_routing._sub, ui_routing._control_cell,
                                ui.chip)
        in_desk = []
        with monkeypatch.context() as m:
            m.setattr(ui_routing, "_row", lambda *a: bool(
                row(*a) or (go == ["route"] and a[2] is victim and not go.clear())))
            m.setattr(ui_routing, "_sub", lambda *a: bool(
                sub(*a) or (go == ["sub"] and not go.clear())))
            m.setattr(ui_routing, "_control_cell",
                      lambda *a, **k: (in_desk.append(1), cell(*a, **k))[1])
            m.setattr(ui, "chip", lambda label, *a, **k: bool(
                chip(label, *a, **k) or (label == "×" and in_desk and go == ["desk"]
                                         and not go.clear())))
            for _ in range(4):
                if go:                      # N7: a route's × is on GRAPH's side pane
                    rows(panel) if what == "route" else frame(panel, "routing")
        assert not go, f"the page never drew a {what} ×"
        quiet()

    quiet()
    u.clear()
    was = state()
    click("route")
    assert victim not in table.routes() and state()[2] != was[2]    # its subscriber went too
    assert [s.label for s in u.stack] == [f"delete route {victim.source} → {victim.target}"]
    assert u.undo() and state() == was
    quiet()
    first = table.desk()[0]
    click("desk")
    assert len(table.desk()) == len(was[1]) - 1
    assert [s.label for s in u.stack] == [f"unmap {ui_routing.control_glyph(table, first)}"]
    assert u.undo() and state() == was
    quiet()
    click("sub")
    assert len(table.macros["macro.1"].subs) == 1
    assert [s.label for s in u.stack] == ["delete subscriber of amt"]
    assert u.undo() and state() == was
    quiet()
    # Replace: one step; the owner comes back with an undo. Keep: none.
    owner = table.routes()[1]
    assert ui_routing.add_route(panel, owner.target, source="lfo:0", depth=0.5) is None
    ui_routing.answer(panel, False)
    quiet()
    assert u.stack == [] and state() == was
    assert ui_routing.add_route(panel, owner.target, source="lfo:0", depth=0.5) is None
    ui_routing.answer(panel, True)
    quiet()
    assert [s.label for s in u.stack] == [f"replace {owner.target}"]
    assert table.owner(owner.target).source == "lfo:0"
    assert u.undo() and state() == was
    quiet()
    # a held hand learn answered by the prompt: Replace's step, not two
    lrn = panel.learn = Learn(reg, table)
    lrn.arm(owner.target)
    lrn.learn_source("hand:1")
    assert lrn.pending is not None
    ui_routing.answer(panel, True)
    quiet()
    assert [s.label for s in u.stack] == [f"replace {owner.target}"]
    assert table.owner(owner.target).source == "hand:1"
    assert u.undo() and state() == was


# ------------------------------------------------ plan 17 WP5: the filter

def test_the_filter_matches_glyph_param_and_source(rig):
    """`matches`: lower-case, every typed word a substring of what the line
    says — a desk line by its glyph ("d3"), Akai's name, its source, its
    param or the param's label; a route by its sentence in its adapter's
    words ("r height", "lfo 1"), its source and its target; a macro by its
    id, its label and its subscribers. A dark line says no target."""
    panel, router, table = rig.panel, rig.router, rig.router.table
    m = ui_routing.matches
    assert m(panel, router, "", "anything") and m(panel, router, "   ")
    assert m(panel, router, "a b", "xa", "by") and not m(panel, router, "a z", "xa", "by")
    assert not m(panel, router, "ab", "a", "b")           # a word never spans two strings
    rig.lib.load("presets", "TRIP")
    router.labels["hand"] = ["R x", "R height", "R z"]
    router.labels["lfo"] = ["LFO 1", "LFO 2"]
    table.set_routes([Binding("hand:1", "view.bright", "position"),
                      Binding("lfo:0", "camera.zoom", "push", 0.08)])
    hand, lfo1 = table.routes()
    d3 = next(b for b in table.desk() if ui_routing.control_glyph(table, b) == "D3")
    assert d3.source == "cc:*:18" and d3.target == "fx.kaleido.segments"

    def route(text, b):
        return m(panel, router, text, *ui_routing.route_hay(panel, router, b))

    def line(text, b, mapped=True):
        return m(panel, router, text, *ui_routing.control_hay(panel, router, b, mapped))
    # the glyph, Akai's name, the source, the param, its label
    for text in ("d3", "D3", "device knob 3", "cc:*:18", "kaleido", "fx.kaleido.seg",
                 "Kaleidoscope SEGMENTS", "d3 kaleido"):
        assert line(text, d3), text
    assert not line("d4", d3) and not line("d3 bright", d3)
    others = [b for b in table.desk() if line("d3", b)]
    assert others == [d3]
    # a route: the param and its label, the adapter's words, the address
    for text in ("bright", "view.bright", "Brightness", "r height", "R HEIGHT",
                 "hand:1", "positions", "height bright"):
        assert route(text, hand), text
    assert not route("lfo 1", hand) and not route("d3", hand)
    for text in ("lfo 1", "LFO 1", "lfo:0", "zoom", "lfo 1 zoom", "pushes"):
        assert route(text, lfo1), text
    assert not route("lfo 2", lfo1) and not route("r height", lfo1)
    # a dark line is its control only: the factory row's target is not the preset's
    dark = ui_routing.unmapped(table)[0]
    assert line(ui_routing.control_glyph(table, dark).lower(), dark, mapped=False)
    assert line(dark.target, dark) and not line(dark.target, dark, mapped=False)
    # a macro: id, label, a base subscriber's param and label, a depth one's route
    table.set_macros({"macro.2": {"label": "Heat", "subs": [
        {"base": "fx.kaleido.zoom", "from": 0.0, "to": 1.0},
        {"depth": {"source": "hand:1", "target": "view.bright"}, "from": 0.0, "to": 1.0}]}})
    m1, m2 = rig.reg["macro.1"], rig.reg["macro.2"]

    def macro(text, p):
        return m(panel, router, text, *ui_routing.macro_hay(panel, router, p))
    for text in ("macro.2", "heat", "kaleido", "Kaleidoscope zoom", "view.bright",
                 "r height", "heat kaleido"):
        assert macro(text, m2), text
    assert macro("macro", m1) and not macro("heat", m1) and not macro("kaleido", m1)


def test_a_filtered_page_draws_only_matching_lines_and_keeps_its_ids(rig, monkeypatch):
    """TRIP with "kaleido" typed: the two desk lines (D3, D4) and the one
    macro that subscribes one are all the page draws, under the section
    titles; the session, which has none, says so; the counts read "3 of N
    rows" (plan 28 N7: the two kaleidoscope routes are GRAPH's now, and no
    route row is drawn here, filtered or not). No two widgets share an
    imgui id, and a × on a filtered line removes the row it is on."""
    from hyperspace import ui

    panel, router, table = rig.panel, rig.router, rig.router.table
    rig.lib.load("presets", "TRIP")
    table.set_macros({"macro.3": {"label": "Heat", "subs": [
        {"base": "fx.kaleido.zoom", "from": 0.0, "to": 1.0}]},
        "macro.5": {"label": "Cool", "subs": [{"base": "view.bright"}]}})
    routes = table.routes()
    want = [b for b in routes if "kaleido" in b.target]
    assert len(want) == 2 and len(routes) > 10
    frame(panel, "routing")
    _, total = ui_routing.found(panel, router)
    assert ui_routing.found(panel, router) == (total, total) and total > 100
    ui_routing._state(panel)["find"] = "Kaleido"
    assert ui_routing.found(panel, router) == (3, total)

    drawn: list[tuple[Binding, int]] = []
    knobs: list[str] = []
    ids: list[int] = []
    row, slider = ui_routing._row, panel._slider
    kill: list[Binding] = []

    def rec_row(panel_, router_, b, k):
        drawn.append((b, k))
        out = row(panel_, router_, b, k)
        return out or (kill == [b] and not kill.clear())
    monkeypatch.setattr(ui_routing, "_row", rec_row)
    monkeypatch.setattr(panel, "_slider", lambda pid, *a, **k: (knobs.append(pid),
                                                               slider(pid, *a, **k))[1])
    for fn in ("button", "checkbox", "slider_float", "slider_int", "combo", "begin_combo",
               "invisible_button", "arrow_button", "input_text_with_hint"):
        real = getattr(imgui, fn)

        def rec(label, *a, _real=real, **k):
            ids.append(imgui.get_id(label))
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    texts, previews = _drawn(monkeypatch)
    for lst in (drawn, knobs, ids, texts, previews):
        lst.clear()
    frame(panel)
    # the routes: none here (N7: GRAPH's)
    assert drawn == []
    # the desk: D3 and D4 and nothing else, no dark line
    assert {"D3", "D4"} <= set(texts) and "D1" not in texts and "D5" not in texts
    assert "unmapped — dark" not in texts
    assert {"fx.kaleido.segments", "fx.kaleido.zoom"} == {   # (swirl: a route's, GRAPH's)
        p for p in previews if p.startswith("fx.")}
    # the macros: the one that subscribes a kaleidoscope param, drawn whole
    assert knobs == ["macro.3"]
    # the titles stay; the session has no such row and says so, once
    assert {"DESK  ·  PRESET LAYER", "MACROS", "SESSION"} <= set(texts)
    assert "ROUTES" not in texts and "MODIFIERS" not in texts
    assert texts.count(ui_routing.NO_MATCH) == 1
    assert "invariant · both layers" not in texts
    assert f"3 of {total} rows" in texts
    assert ui_routing.POINTER not in texts                   # the unfiltered line is gone
    dup = {i for i in ids if ids.count(i) > 1}
    assert len(ids) > 12 and not dup, f"conflicting ids {sorted(dup)}"
    # × on a filtered desk line (D4): that row goes, D3 stays
    d3, d4 = (next(b for b in table.desk() if ui_routing.control_glyph(table, b) == g)
              for g in ("D3", "D4"))
    n_desk = len(table.desk())
    cell, chip = ui_routing._control_cell, ui.chip
    on: list[Binding] = []
    go = [d4]
    with monkeypatch.context() as mp:
        mp.setattr(ui_routing, "_control_cell",
                   lambda t, b, *a, **k: (on.append(b), cell(t, b, *a, **k))[1])
        mp.setattr(ui, "chip", lambda label, *a, **k: bool(
            chip(label, *a, **k) or (label == "×" and on and on[-1] is d4 and go
                                     and not go.clear())))
        frame(panel)
    assert not go and d4 not in table.desk() and d3 in table.desk()
    assert len(table.desk()) == n_desk - 1
    # a filter nothing matches: every section says so and no line is drawn
    ui_routing._state(panel)["find"] = "no such thing anywhere"
    for lst in (drawn, knobs, texts):
        lst.clear()
    frame(panel)
    assert not drawn and not knobs and texts.count(ui_routing.NO_MATCH) == 3
    assert f"0 of {total} rows" in texts         # D4 is a dark line now
    # the × chip beside the field is the clear: every row is back
    with monkeypatch.context() as mp:
        mp.setattr(ui, "chip", lambda label, *a, **k: bool(
            chip(label, *a, **k) or label == "×##find"))
        frame(panel)
    assert ui_routing._state(panel)["find"] == ""
    for lst in (drawn, knobs, texts):
        lst.clear()
    frame(panel)
    assert drawn == [] and len(knobs) == 8 and len(table.routes()) == len(routes)
    assert ui_routing.NO_MATCH not in texts and ui_routing.POINTER in texts


def test_the_filter_is_ui_state(rig, tmp_path):
    """The filter's text lives in the page's state on the panel and nowhere
    else: no param holds it, a snapshot and a saved preset do not carry it,
    typing it is no undo step and no dirty dot, a preset load leaves it,
    and one state write — what `goto` (WP4) does — clears it. A new panel
    starts with none, and a state dict from before a hot reload gains the
    key."""
    from types import SimpleNamespace

    from hyperspace import undo

    panel, lib, reg, router = rig.panel, rig.lib, rig.reg, rig.router
    lib.load("presets", "TRIP")
    frame(panel, "routing")
    ids = [p.id for p in reg]
    before = (json.dumps(reg.snapshot(), sort_keys=True, default=str),
              json.dumps(lib.document("presets", "X"), sort_keys=True, default=str))
    u = undo.Undo(reg, router.table, on_restore=router.sync_macros)
    undo.install(u)
    clock = [0.0]

    def quiet():
        for _ in range(3):
            clock[0] += 1.0
            u.tick(clock[0])
    quiet()
    u.clear()
    st = ui_routing._state(panel)
    assert st["find"] == "" and st["filter"] == ""        # two fields, two keys
    for text in ("k", "ka", "kaleido zzfind"):            # typed, a frame a letter
        st["find"] = text
        frame(panel)
        quiet()
    assert [p.id for p in reg] == ids
    assert not any("zzfind" in str(p.base) for p in reg if p.kind is Kind.TEXT)
    after = (json.dumps(reg.snapshot(), sort_keys=True, default=str),
             json.dumps(lib.document("presets", "X"), sort_keys=True, default=str))
    assert after == before and "zzfind" not in "".join(after)
    assert u.stack == [] and not lib.is_dirty("presets")
    path = lib.save_as("presets", "Mine")
    assert "zzfind" not in path.read_text()
    assert not [f for f in tmp_path.rglob("*") if f.is_file() and f.suffix in (".json", ".toml")
                and "zzfind" in f.read_text()]
    # the param combo's own find field is another key: it does not filter the page
    st["filter"] = "nothing"
    assert ui_routing.found(panel, router)[0] == 0
    st["find"] = "kaleido"
    assert ui_routing.found(panel, router)[0] == 2      # (N7: TRIP's two kaleido routes are GRAPH's)
    st["filter"] = ""
    # a preset load leaves it (fork 9 (a))
    lib.load("presets", "MANDALA")
    frame(panel)
    assert st["find"] == "kaleido" and ui_routing._state(panel) is st
    n, m = ui_routing.found(panel, router)
    assert 0 < n < m
    # what a desk click does (`goto`, WP4): the filter cleared, every row back
    ui_routing.goto(panel, "cc:*:18")
    frame(panel)
    assert ui_routing.found(panel, router) == (m, m)
    # gone at restart; a state from before a hot reload gains the key
    assert ui_routing._state(SimpleNamespace())["find"] == ""
    old = SimpleNamespace(_routing_state={"error": "", "filter": "", "prompt": None})
    assert ui_routing._state(old)["find"] == ""


def test_typing_in_the_filter_is_imguis_keyboard_not_the_apps(rig, monkeypatch):
    """With the field focused imgui wants the keyboard — what the loop
    copies into `Keys.typing` each frame (app.py: `keys.typing =
    io.want_capture_keyboard`), so a letter typed in the control window
    reaches the field and is no app key (`Keys._down` then reads only the
    render window: test_app_boundary's
    test_keys_fire_on_the_edge_from_either_window_unless_imgui_is_typing)."""
    from hyperspace import app

    panel = rig.panel
    io = imgui.get_io()
    frame(panel, "routing")
    frame(panel)
    assert not io.want_capture_keyboard
    real = imgui.input_text_with_hint
    focus = [True]

    def field(label, *a, **k):
        if label == "##rows" and focus:
            imgui.set_keyboard_focus_here()               # a click in the field
        return real(label, *a, **k)
    monkeypatch.setattr(imgui, "input_text_with_hint", field)
    for _ in range(3):
        frame(panel)
    focus.clear()
    assert io.want_capture_keyboard and io.want_text_input
    for ch in "d3":
        io.add_input_character(ord(ch))
        frame(panel)
    assert ui_routing._state(panel)["find"] == "d3"
    assert not ui_routing._state(panel)["hold"]           # typing here holds no line
    assert ui_routing.found(panel, rig.router)[0] >= 1
    # the app's side: the same key held in the control window is not down
    g = app.glfw
    monkeypatch.setattr(g, "get_key", lambda win, key: g.PRESS if win == "ctrl" else g.RELEASE)
    keys = app.Keys("render", "ctrl")
    keys.typing = io.want_capture_keyboard
    assert not keys.pressed(g.KEY_D) and not keys.down(g.KEY_3)
    keys.typing = False
    assert keys.pressed(g.KEY_D)


def test_a_line_in_use_is_not_filtered_away_under_the_hand(rig, monkeypatch):
    """A filter that found a macro by its label: retyping the label (a
    widget in use) leaves the macro drawn though it no longer matches, and
    it goes once the widget is let go. Spaces alone filter nothing: no red
    count, no × chip."""
    from hyperspace import ui

    panel, table = rig.panel, rig.router.table
    rig.lib.load("presets", "TRIP")
    table.set_macros({"macro.3": {"label": "Heat", "subs": []}})
    knobs: list[str] = []
    slider = panel._slider
    monkeypatch.setattr(panel, "_slider", lambda pid, *a, **k: (knobs.append(pid),
                                                               slider(pid, *a, **k))[1])
    st = ui_routing._state(panel)
    st["find"] = "heat"
    frame(panel, "routing")
    knobs.clear()
    frame(panel)
    assert knobs == ["macro.3"] and not st["hold"]
    with monkeypatch.context() as mp:                    # the label field has the keyboard
        mp.setattr(imgui, "is_any_item_active", lambda: True)
        table.macros["macro.3"].label = "Hea"
        for _ in range(3):
            knobs.clear()
            frame(panel)
            assert knobs == ["macro.3"] and st["hold"]
    knobs.clear()
    frame(panel)                                          # let go: it no longer matches
    assert knobs == [] and not st["hold"]
    # spaces alone: the page is unfiltered and says so
    st["find"] = "  "
    chips: list[str] = []
    chip = ui.chip
    monkeypatch.setattr(ui, "chip", lambda label, *a, **k: (chips.append(label),
                                                            chip(label, *a, **k))[1])
    texts, _ = _drawn(monkeypatch)
    knobs.clear()
    frame(panel)
    assert len(knobs) == 8 and "×##find" not in chips and "+ route" not in chips  # (N7)
    assert not any(t.endswith(" rows") for t in texts)
    assert ui_routing.POINTER in texts                  # N7: the unfiltered line


# ------------------------------------------- plan 17 WP4: the picked control's line

def _many_routes(rig, n=30) -> None:
    """Enough routes that the desk and session sections start under the fold."""
    reg, table = rig.reg, rig.router.table
    for p in reg:
        if len(table.routes()) >= n:
            break
        if p.kind is Kind.CONTINUOUS and p.modulatable and table.owner(p.id) is None:
            try:
                table.add(Binding("lfo:1", p.id, "push", 0.1))
            except routing.Owned:
                continue
    assert len(table.routes()) >= n


def _routing_probe(monkeypatch) -> dict:
    """What the ROUTING page did on its last draw: the page's own scroll,
    the rows child's, and each framed line's rect against the child's."""
    from hyperspace.ui import Panel

    out: dict = {"lines": []}
    page, session, mark = Panel._page_routing, ui_routing.session, ui_routing._mark_line

    def page_(self, dt):
        out["lines"] = []
        page(self, dt)
        out["page"] = (imgui.get_scroll_y(), imgui.get_scroll_max_y())

    def session_(panel, router):
        session(panel, router)
        out["child"] = (imgui.get_scroll_y(), imgui.get_scroll_max_y())

    def mark_(panel, table, b, section, y0):
        before = ui_routing._state(panel).get("marked", 0)
        mark(panel, table, b, section, y0)
        if ui_routing._state(panel).get("marked", 0) > before:
            top = imgui.get_window_pos().y
            out["lines"].append((b, section, y0, top, top + imgui.get_window_height()))
    monkeypatch.setattr(Panel, "_page_routing", page_)
    monkeypatch.setattr(ui_routing, "session", session_)
    monkeypatch.setattr(ui_routing, "_mark_line", mark_)
    return out


def _seen(got) -> bool:
    """Is the one framed line inside the rows child's own rect?"""
    (_, _, y0, top, bottom), = got["lines"]
    return top <= y0 <= bottom - 16


def test_goto_scrolls_the_rows_child_to_the_controls_line(rig, monkeypatch):
    """`goto` (fork 2): the rows' child scrolls to the picked control's
    line — its row on the layer that is up, its "unmapped — dark" line, an
    invariant row in the session section — and frames it for as long as
    it is picked; the page itself never scrolls and is never changed. If
    ROUTING is not open the scroll waits until it is, while the control is
    still picked. A control dark on the global layer has no line. The
    filter is cleared — also under a field that has the keyboard."""
    from test_ui_shell import _click, _learn_over

    from hyperspace import apc40, ui_desk
    from hyperspace.app import CONTROL_SIZE

    panel, table = rig.panel, rig.router.table
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    lrn = _learn_over(rig)
    rig.lib.load("presets", "TRIP")
    _many_routes(rig)
    got = _routing_probe(monkeypatch)
    st = ui_routing._state(panel)

    def control(glyph):
        return next(c for c in apc40.LAYOUT if c.glyph == glyph)

    def draw(n=3, page=None):
        for _ in range(n):
            frame(panel, page)
    draw(3, "routing")
    assert got["child"][1] > 0 and got["child"][0] == 0 and got["page"] == (0, 0)
    assert got["lines"] == [] and st["marked"] == 0
    # ROUTING open: it scrolls on the next draws, and the line is framed
    st["find"] = "kaleido"
    lrn.pick("cc:*:18")                                       # D3: a row of TRIP's desk
    ui_routing.goto(panel, "cc:*:18")
    assert st["find"] == ""
    draw(2)
    assert got["child"][0] > 0 and got["page"] == (0, 0)
    assert st["goto"] is None and st["marked"] == 1
    (b, section, *_), = got["lines"]
    assert (b.source, b.layer, section) == ("cc:*:18", "preset", "desk") and _seen(got)
    at = got["child"][0]
    draw(3)
    assert got["child"][0] == at and st["marked"] == 1       # once: it does not keep pulling
    # an invariant control: its row in the session section, further down
    s3 = control("SM")                     # MASTER (S1–S8 are layered since plan 24 C2)
    lrn.pick(s3.source)
    ui_routing.goto(panel, s3.source)
    draw(2)
    (b, section, *_), = got["lines"]
    assert (b.source, b.layer, section) == (s3.source, None, "session") and _seen(got)
    assert got["child"][0] > at and got["page"] == (0, 0)
    # a dark preset control: its "unmapped — dark" line
    dark = ui_routing.unmapped(table)[0]
    lrn.pick(dark.source)
    ui_routing.goto(panel, dark.source)
    draw(2)
    (b, section, *_), = got["lines"]
    assert b.source == dark.source and section == "desk" and _seen(got)
    assert not any(x.overlaps(dark) for x in table.desk())
    # the global layer up: a global row's line; a control dark on it has none
    table.set_layer("global")
    lrn.pick("cc:*:18")
    ui_routing.goto(panel, "cc:*:18")
    draw(2)
    (b, section, *_), = got["lines"]
    assert (b.layer, section) == ("global", "session") and _seen(got)
    k6 = control("K6")
    assert k6.glyph not in ui_desk.lit(table)
    at = got["child"][0]
    lrn.pick(k6.source)
    ui_routing.goto(panel, k6.source)
    draw(2)
    assert got["lines"] == [] and st["goto"] is None and got["child"][0] == at
    table.set_layer("preset")
    # let go: no frame
    lrn.pick(None)
    draw(1)
    assert got["lines"] == [] and st["marked"] == 0
    # another page open: a real click on the desk does not change the page;
    # the scroll waits for ROUTING, while the control is still picked
    draw(3, "view")
    st["find"] = "kaleido"
    _click(panel, ui_desk.rect(panel, control("D3")))
    assert lrn.control == "cc:*:18" and st["goto"] == "cc:*:18" and st["find"] == ""
    assert PAGE_KEYS[panel.page] == "view"
    draw(2)
    assert st["goto"] == "cc:*:18"
    got["lines"] = []
    draw(2, "routing")
    assert st["goto"] is None and _seen(got) and got["page"] == (0, 0)
    # …and not at all once it is let go first
    draw(2, "view")
    _click(panel, ui_desk.rect(panel, control("SM")))
    assert st["goto"] == control("SM").source
    ui_desk.let_go(panel)
    at = got["child"][0]
    draw(2, "routing")
    assert st["goto"] is None and got["lines"] == [] and got["child"][0] == at


def test_a_desk_click_clears_a_filter_that_has_the_keyboard(rig, monkeypatch):
    """Fork 9: a desk click clears the ROUTING filter even while its field
    has the keyboard — imgui writes a focused field's edit buffer back
    over a state write, so the clear holds until the field has let go.
    Real typing, a real click."""
    from test_ui_shell import _click, _learn_over

    from hyperspace import apc40, ui_desk
    from hyperspace.app import CONTROL_SIZE

    panel = rig.panel
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(*CONTROL_SIZE)
    lrn = _learn_over(rig)
    rig.lib.load("presets", "TRIP")
    for _ in range(3):
        frame(panel, "routing")
    real = imgui.input_text_with_hint
    focus = [True]

    def field(label, *a, **k):
        if label == "##rows" and focus:
            imgui.set_keyboard_focus_here()                   # a click in the field
        return real(label, *a, **k)
    monkeypatch.setattr(imgui, "input_text_with_hint", field)
    for _ in range(3):
        frame(panel)
    focus.clear()
    for ch in "kaleido":
        io.add_input_character(ord(ch))
        frame(panel)
    st = ui_routing._state(panel)
    assert st["find"] == "kaleido" and io.want_text_input
    n, m = ui_routing.found(panel, rig.router)
    assert 0 < n < m
    d6 = next(c for c in apc40.LAYOUT if c.glyph == "D6")
    _click(panel, ui_desk.rect(panel, d6))
    assert lrn.control == d6.source
    for _ in range(4):
        frame(panel)
        assert st["find"] == ""
    assert not st["unfind"] and not io.want_text_input
    assert ui_routing.found(panel, rig.router) == (m, m)
    assert st["marked"] == 1                                  # its line is drawn, and framed


def test_the_head_has_the_same_dot_and_label(rig, tmp_path):
    """Plan 19 WP5: ROUTING's head is the preset strip's save over the
    same preset — the same 12 px disc beside the name, the save chip lit
    while dirty and saying "save copy" on a factory preset, "save" on
    yours. Clicking it is `Library.overwrite`, as before."""
    from test_ui_shell import _click

    from hyperspace import ui

    panel, lib, reg = rig.panel, rig.lib, rig.reg
    lib.load("presets", "TRIP")
    frame(panel, "routing")
    frame(panel)
    st = ui_presets._state(panel)
    assert "head.dot" not in st["rects"] and st["save"]["head"] == ("save copy", False)
    reg["view.bright"].set(reg["view.bright"].value * 0.5 + 0.1)
    frame(panel)
    frame(panel)
    x0, y0, x1, y1 = st["rects"]["head.dot"]
    assert x1 - x0 == y1 - y0 == 2 * ui.DOT_R
    assert st["save"]["head"] == ("save copy", True)
    assert not (tmp_path / "presets" / "trip.json").exists()
    _click(panel, st["rects"]["head.save"])
    assert (tmp_path / "presets" / "trip.json").is_file() and not lib.is_dirty("presets")
    frame(panel)
    assert "head.dot" not in st["rects"] and st["save"]["head"] == ("save", False)


def test_a_routes_own_feel_draws_its_line_with_its_own_ids(rig, tmp_path, monkeypatch):
    """A row with a feel of its own (motion.py) draws a third line — attack
    and release, or Hz and damping — and every widget keeps its own id."""
    from hyperspace.motion import Motion
    panel = rig.panel
    router = _with_router(rig, tmp_path)
    routes = router.table.routes()
    routes[0].motion = Motion("follow", 0.02, 0.4)
    routes[1].motion = Motion("spring", hz=2.0, damp=0.5)
    routes[2].motion = Motion("off")
    seen: list[str] = []
    ids: list[int] = []
    real = imgui.slider_float

    def rec(label, *a, **k):
        seen.append(label)
        ids.append(imgui.get_id(label))
        return real(label, *a, **k)
    monkeypatch.setattr(imgui, "slider_float", rec)
    rows(panel)                                 # N7: the rows are GRAPH's side pane's
    seen.clear()
    ids.clear()
    rows(panel)
    assert {"##atk", "##rel", "##hz", "##damp"} <= set(seen)
    assert seen.count("##atk") == 1 and seen.count("##hz") == 1   # only the rows with their own
    assert len(ids) == len(set(ids))


def test_the_system_page_shows_the_sticks_feel(rig, tmp_path, monkeypatch):
    """The gamepad section: the feel, then only the two knobs its mode reads."""
    panel = rig.panel
    _with_router(rig, tmp_path)                    # a table: the desk's params, the pad's feel
    drawn: list[str] = []
    real = panel._row

    def rec(pid, *a, **k):
        drawn.append(pid)
        return real(pid, *a, **k)
    monkeypatch.setattr(panel, "_row", rec)
    frame(panel, "system")
    assert "desk.pad.feel" in drawn and "desk.pad.attack" not in drawn   # off: no knobs
    panel.reg["desk.pad.feel"].set(2)                                      # spring
    drawn.clear()
    frame(panel)
    assert "desk.pad.hz" in drawn and "desk.pad.damp" in drawn
    assert "desk.pad.release" not in drawn


def test_neither_shift_nor_save_is_a_desk_target(rig, tmp_path):
    """`desk_target`: the one rule for the desk rows' target combo, "Learn
    desk" and "Learn pad". SHIFT's param is not one, and neither is the
    desk's SAVE (plan 24 C1, review of PR #175): a learned toggle or key on
    `desk.save` would latch it, and every bank pad's tap would then make a
    new preset."""
    router = _with_router(rig, tmp_path)
    routing.register_desk(rig.reg, router.table)
    reg = rig.reg
    assert not ui_routing.desk_target(reg[routing.SHIFT_PARAM])
    assert not ui_routing.desk_target(reg[routing.SAVE_PARAM])
    assert ui_routing.desk_target(reg["view.points"])
    targets = {p.id for p in ui_routing._desk_targets(rig.panel)}
    assert routing.SAVE_PARAM not in targets and routing.SHIFT_PARAM not in targets
    assert not rig.panel._desk_target(reg[routing.SAVE_PARAM])


def test_the_routing_page_lists_the_sink_rows_with_the_others(rig, tmp_path, monkeypatch):
    """Plan 27 B3: a sink row appears as the others do — a line in the
    page's own `sinks` section (the session's), its words the router's,
    found by the filter, an off row dimmed but listed."""
    router = _with_router(rig, tmp_path)
    router.table.add(Binding("param:view.bright", "bridge:2", routing.SINK_OP))
    router.table.add(Binding("lane:*", "bridge:0", routing.SINK_OP, enabled=False))
    texts, _ = _drawn(monkeypatch)
    frame(rig.panel, "routing")
    frame(rig.panel)
    assert "param view.bright → bridge:2" in texts and "every lane → bridge:0" in texts
    ui_routing._state(rig.panel)["find"] = "bridge:2"
    n, m = ui_routing.found(rig.panel, router)
    assert m >= 2 and n >= 1


# ------------------------------- review: the page's cost a frame (35 fps → full rate)

def test_the_routing_page_builds_its_source_list_once_a_draw(rig, monkeypatch):
    """The source combo's list is the same for every route row: the list of
    rows (GRAPH's side pane since plan 28 N7, `ui_graph.route_rows`) builds
    it once a draw, not once a row (21 rows × every binding per scheme was
    5 ms a frame on the rig)."""
    _many_routes(rig, 12)
    calls = []
    real = ui_routing._sources

    def counted(panel, router):
        calls.append(1)
        return real(panel, router)
    monkeypatch.setattr(ui_routing, "_sources", counted)
    rows(rig.panel)
    rows(rig.panel)
    assert len(rig.router.table.routes()) >= 12
    assert len(calls) == 2


def test_the_dark_controls_are_worked_out_again_only_when_the_table_changes(
        rig, tmp_path, monkeypatch):
    """`unmapped` (the desk's dark lines) is a pairwise scan of the table:
    9.5 ms a frame on ROUTING. It is remembered against what decides it —
    the profile and each row's source, layer, enabled flag (and target) —
    so two draws of an unchanged table work it out once, and a Learn, a
    flipped row, a preset load or another profile each work it out again,
    with the same answer as a fresh scan."""
    from test_presets import put

    from hyperspace import apc40
    from hyperspace.learn import Learn

    panel, lib, table = rig.panel, rig.lib, rig.router.table
    real = ui_routing.preset_controls
    calls = []

    def counted(t):
        calls.append(1)
        return real(t)
    monkeypatch.setattr(ui_routing, "_DARK", {})           # nothing remembered yet
    monkeypatch.setattr(ui_routing, "preset_controls", counted)

    def fresh() -> list[str]:
        rows = table.desk()
        return [f.source for f in real(table) if not any(b.overlaps(f) for b in rows)]

    def dark() -> list[str]:
        return [f.source for f in ui_routing.unmapped(table)]

    frame(panel, "routing")
    frame(panel)
    assert len(calls) == 1 and dark() == fresh() and len(calls) == 1
    # the same rows as new objects: nothing to work out again
    table.bindings = [replace(b) for b in table.bindings]
    frame(panel)
    assert len(calls) == 1
    # (a) a Learn lands a desk row on a dark control
    first = dark()[0]
    lrn = panel.learn = Learn(rig.reg, table)
    lrn.arm("view.depth4", "desk")
    assert lrn.learn_control(first, apc40)
    frame(panel)
    assert len(calls) == 2 and first not in dark() and dark() == fresh()
    # (b) a session row on a dark control makes it invariant; its enabled
    # flag flipped off gives the control back to the preset
    ctl = dark()[0]
    row = table.add(Binding(ctl, "view.bright", "abs"))
    frame(panel)
    assert len(calls) == 3 and ctl not in dark() and dark() == fresh()
    table.enable(row, False)
    frame(panel)
    assert len(calls) == 4 and ctl in dark() and dark() == fresh()
    # (c) a preset load replaces the desk
    nxt = next(c for c in dark() if c != ctl)
    put(tmp_path, "SHOW", desk=[{"source": nxt, "target": "view.speed", "op": "abs"}])
    lib.load("presets", "SHOW")
    frame(panel)
    assert len(calls) == 5 and nxt not in dark() and first in dark()
    assert dark() == fresh()
    # (d) another profile: no factory map, nothing dark
    table.profile = "none"
    frame(panel)
    assert len(calls) == 6 and dark() == fresh() == []


def test_the_routing_head_names_a_loop_the_patch_keeps_off(rig, tmp_path, monkeypatch):
    """Plan 28 N0: a loop no delay breaks is named on ROUTING's head, in
    words, while it stands; the routes it cuts stay listed."""
    panel = rig.panel
    router = _with_router(rig, tmp_path)
    router.table.set_routes([Binding("lfo:0", "lfo.2.rate", "push", 0.5),
                             Binding("lfo:1", "lfo.1.depth", "push", 0.5)])
    texts, _ = _drawn(monkeypatch)
    frame(panel, "routing")
    note = ("loop: lfo:0 → lfo.2.rate → lfo:1 → lfo.1.depth → lfo:0 needs a delay — "
            "lfo:1 → lfo.1.depth is off until it has one")
    assert note in texts
    assert [b.target for b in router.table.routes()] == ["lfo.2.rate", "lfo.1.depth"]
    router.table.set_routes([Binding("lfo:0", "lfo.2.rate", "push", 0.5)])
    texts.clear()
    frame(panel)
    assert not any(t.startswith("loop:") for t in texts)
