"""The ROUTING page (moved out of test_ui_bands.py, audit D5): the matrix
over test_ui_shell's headless rig — routes, a live lane, edits landing in
bindings.json, the referee's refusals, the Replace / Keep prompt, the
macro scales, the preset strip through the library.
"""

import json
from dataclasses import replace

import pytest
from imgui_bundle import imgui
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import routing, ui_presets, ui_routing
from hyperspace.bands import CEIL
from hyperspace.library import LibraryError
from hyperspace.params import Kind
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.ui import PAGE_KEYS


@pytest.fixture()
def rig(shell_rig):  # noqa: F811 — pytest hands the shell's rig through under its name
    return shell_rig


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
    assert panel.ghosts == 1                    # the live bar's red hairline
    panel.audio.on = False
    assert ui_routing._live(panel, router, router.table.routes()[-1]) is None
    reg.apply()
    frame(panel)
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
    monkeypatch.setattr(imgui, "slider_float",
                        lambda label, v, lo, hi, fmt="%.3f", *a: (
                            fmts.append(fmt), real(label, v, lo, hi, fmt, *a))[1])
    frame(panel, "routing")
    assert panel.ghosts == 0 and "100 %" in fmts and "100 % → 60 %" not in fmts
    router.modulate()
    reg.apply()
    macro = reg["macro.2"]
    assert macro.modulated and macro.text() == "100 %" and panel._eff_text(macro) == "60 %"
    fmts.clear()
    frame(panel)
    assert "100 % → 60 %" in fmts                  # the strip's slider, under a performer
    assert panel.ghosts == 2                       # its ghost bar + the row's live hairline
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
    assert len(ids) > 8 * 1 + 13 * 4              # eight knobs, four-plus widgets a row
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
              {"source": "note:0:82", "target": "view.points", "op": "toggle",
               "feedback": "led"},
              {"source": "cc:0:7", "target": "view.bright", "op": "abs"}],   # a fader: dropped
        macros={"macro.1": {"label": "Heat", "subs": [
                    {"base": "view.depth4", "from": 0.2, "to": 0.8},
                    {"depth": {"source": "hand:7", "target": "view.bright"},
                     "from": 0.0, "to": 1.0}]},
                "macro.2": {"subs": [{"base": "view.depth4", "from": 1.0, "to": 0.0}]}})
    lib.load("presets", "SHOW")
    panel.learn = Learn(reg, table)
    panel.learn.refuse("track fader 3 is invariant (the session's) — not learned")
    texts, previews = _drawn(monkeypatch)
    frame(panel, "routing")
    frame(panel)
    # the head
    assert "SHOW" in texts and "LAYER PRESET" in texts and "●" not in texts
    assert "learn: track fader 3 is invariant (the session's) — not learned" in texts
    assert any(t.startswith("desk: dropped cc:0:7 → view.bright") and "invariant" in t
               for t in texts)
    assert "bindings" not in lib.kinds                         # no routing-preset strip
    # the routes, with the macro's chip
    assert "view.bright" in previews and "× macro.1" in texts
    # the desk: its rows by glyph (plan 14 WP7: D1 is device knob 1, G1·9
    # scene launch 1), and the controls it leaves dark
    assert {"DESK  ·  PRESET LAYER", "D1", "G1·9"} <= set(texts)
    assert "device knob 1" not in texts                        # Akai's name: the tooltip
    assert {"view.speed", "view.points"} <= set(previews)
    assert "K1" in texts and "unmapped — dark" in texts
    dark = [f.source for f in ui_routing.unmapped(table)]
    assert "cc:0:48" in dark and "cc:*:16" not in dark and "cc:0:7" not in dark
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
    assert "●" in texts                                         # the head's dot
    assert (path.read_text(), path.stat().st_mtime_ns) == before   # no file written
    # SHIFT latched: the head says so
    table.set_layer("global")
    texts.clear()
    frame(panel)
    assert "LAYER GLOBAL" in texts


def test_route_a_lane_here_jumps_to_the_page(rig, tmp_path):
    panel, reg = rig.panel, rig.reg
    _with_router(rig, tmp_path)
    frame(panel, "view")
    p = reg["band.sel.atk"]                     # an alias: the route goes to the real param
    real = panel._real(p)
    ui_routing.add_route(panel, real.id)
    reg["ui.page"].set(PAGE_KEYS.index("routing"))
    assert panel.router.table.routes_to("band.0.atk")
    frame(panel)
    assert panel.page == PAGE_KEYS.index("routing")


def test_the_old_routing_presets_step_load_save_as_presets(rig, tmp_path):
    """Was test_routing_presets_step_load_save: the routing presets' kind is
    gone (plan 13 WP5) and what it held is presets — stepped, loaded, saved
    and deleted on the one preset strip's library group, the routes with
    the rest of the preset."""
    panel, lib = rig.panel, rig.panel.library
    router = rig.router                             # the one the rig's Presets loads into
    frame(panel, "routing")
    assert lib.kinds == ("presets",)
    listing = lib.list("presets")
    assert {"legacy6", "lfo-breathe", "hands-fx", "hands-pinch", "hands-play"} <= set(listing)
    assert lib.load("presets", "lfo-breathe") == []
    assert rig.reg["lfo.1.sync"].value == 3         # lfo-breathe lands its bases: 1 bar
    assert lib.next("presets") == listing[listing.index("lfo-breathe") + 1]
    lib.load("presets", "legacy6")
    assert rig.view.pattern_mod[0] == 0.0           # legacy6 lands its bases
    assert not lib.is_dirty("presets")
    frame(panel)
    # an edit dirties; save as writes the whole preset to the user folder
    router.table.add(Binding("lane:2", "view.bright", "push", 0.3))
    assert lib.is_dirty("presets")
    frame(panel)
    path = lib.save_as("presets", "My Routes")
    assert path == tmp_path / "presets" / "my-routes.json"
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.preset/2" and len(doc["routes"]) == 13
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
    frame(panel, "routing")
    texts.clear()
    frame(panel)                                    # one frame: one mark, on one row
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
