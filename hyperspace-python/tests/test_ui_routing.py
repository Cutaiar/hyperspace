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
from hyperspace.library import Library, LibraryError
from hyperspace.params import Kind
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.ui import PAGE_KEYS


@pytest.fixture()
def rig(shell_rig):  # noqa: F811 — pytest hands the shell's rig through under its name
    return shell_rig


def _with_router(rig, tmp_path):
    table = Bindings.factory(path=routing.bindings_path(tmp_path))
    rig.panel.router = Router(rig.reg, table)
    return rig.panel.router


def test_routing_page_draws_routes(rig, tmp_path):
    panel = rig.panel
    frame(panel, "routing")                     # no router: says so
    router = _with_router(rig, tmp_path)
    assert len(router.table.routes()) == 12
    frame(panel)
    frame(panel)
    assert panel.library.current("bindings") is None      # the strip: nothing loaded
    assert not panel.library.is_dirty("bindings")


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


def test_routing_page_edits_land_in_bindings_json(rig, tmp_path):
    """A route deleted on the page stays deleted: the page writes the table
    once it changes, not only when a learn happens to."""
    panel = rig.panel
    router = _with_router(rig, tmp_path)
    frame(panel, "routing")
    for b in list(router.table.routes()):
        router.table.remove(b)
    frame(panel)
    assert _on_disk(tmp_path).routes() == []
    b = ui_routing.add_route(panel, "view.bright")   # the context menu's add, page unseen
    assert [x.target for x in _on_disk(tmp_path).routes()] == ["view.bright"]
    b.value = -0.25
    frame(panel)
    assert _on_disk(tmp_path).routes()[0].value == -0.25


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
    assert [x.target for x in _on_disk(tmp_path).routes()] == [
        "view.bright", "view.speed", "view.depth4"]
    # the row's checkbox goes through the referee too: waking a row onto
    # a taken target leaves it off and says why
    off = router.table.add(Binding("hand:3", "view.speed", "push", 0.2, enabled=False))
    with pytest.raises(routing.Owned):
        router.table.enable(off)
    assert not off.enabled
    frame(panel)


def test_the_replace_prompt_swaps_the_owner_or_leaves_the_table(rig, tmp_path, monkeypatch):
    """Plan 09 WP5, exit criterion 3 without the mouse: a second performer
    on a target is a question, not an error. *Replace* swaps the owner and
    writes the file; *Keep* leaves the table untouched. The same modal
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
    # add: Replace swaps and writes
    assert ui_routing.add_route(panel, "view.bright", source="lfo:0", depth=0.5) is None
    old, new = ui_routing.prompt(panel)
    assert old is owner and router.describe(new) == "LFO 1 pushes +0.5"
    frame(panel)                                                       # the view page: the modal is up
    assert ui_routing._state(panel)["modal"]
    assert table.owner("view.bright") is owner                         # untouched while it asks
    ui_routing.answer(panel, True)
    assert table.owner("view.bright").source == "lfo:0" and owner not in table.bindings
    assert _on_disk(tmp_path).owner("view.bright").source == "lfo:0"
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
    assert writes == [1]                                               # once (audit R9): the learn's
    assert ui_routing._state(panel)["saved"] == ui_routing._sig(router)  # …and the page knows
    got = table.owner("view.bright")
    assert got.source == "hand:1" and cur not in table.bindings
    assert not table.routes_to("view.speed")                           # one axis, one param
    assert _on_disk(tmp_path).owner("view.bright").source == "hand:1"
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
    assert ui_routing._state(panel)["saved"] == ui_routing._sig(router)  # on disk already…
    before = routing.bindings_path(tmp_path).stat().st_mtime_ns
    frame(panel, "routing")
    assert routing.bindings_path(tmp_path).stat().st_mtime_ns == before  # …so no second write
    mover = table.add(Binding("hand:2", "view.speed", "position"))
    ui_routing.ask(panel, asleep, replace(mover, target="view.bright"),
                   lambda: ui_routing._retarget(router, mover, "view.bright"))
    ui_routing.answer(panel, True)
    assert mover.target == "view.bright" and table.owner("view.bright") is mover
    assert asleep not in table.bindings and _on_disk(tmp_path).owner("view.bright").source == "hand:2"
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


def test_the_macros_lead_the_scale_choices_and_show_their_owner(rig, tmp_path, monkeypatch):
    """Plan 09 decision 7: the eight macro knobs come first in every row's
    scale combo (then the other continuous params, master.gain among them),
    are targets like any other, and draw in a strip over the rows as the
    panel's own sliders — a hand that positions one shows as the usual
    `base → effective` readout and a ghost."""
    panel, reg = rig.panel, rig.reg
    ids = [p.id for p in ui_routing._scales(panel)]
    assert ids[:8] == [f"macro.{k}" for k in range(1, 9)]
    assert "master.gain" in ids[8:] and not any(i.startswith("macro.") for i in ids[8:])
    assert all(p.kind is Kind.CONTINUOUS and not p.alias for p in ui_routing._scales(panel))
    assert {p.id for p in ui_routing._targets(panel)} >= set(ids[:8])
    # never the row's own target (a self-scaled push strobes); any other macro, yes
    own = [p.id for p in ui_routing._scales(panel, "macro.2")]
    assert "macro.2" not in own and own[:7] == [f"macro.{k}" for k in (1, 3, 4, 5, 6, 7, 8)]
    assert "view.bright" not in {p.id for p in ui_routing._scales(panel, "view.bright")}
    router = panel.router = Router(reg, Bindings([
        Binding("lane:0", "view.bright", "push", 0.5, scale="macro.2"),
        Binding("hand:0", "macro.2", "position"),
    ]))
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


def test_routing_presets_step_load_save(rig, tmp_path):
    """The ROUTING page's strip is the library's (audit L1): the page
    registers the bindings kind on first sight and every button is a
    library call — list, prev / next, load, save as, delete, reset."""
    panel, lib = rig.panel, rig.panel.library
    router = _with_router(rig, tmp_path)
    frame(panel, "routing")
    assert "bindings" in lib.kinds
    listing = lib.list("bindings")
    assert listing == ["default", "hands-fx", "hands-pinch", "hands-play", "legacy6",
                       "lfo-breathe"]                       # the factory exports
    # next from nothing: the first; prev wraps to the last
    assert lib.next("bindings") == "default"
    assert lib.current("bindings") == "default"
    assert not lib.is_dirty("bindings")
    frame(panel)
    assert lib.prev("bindings") == "lfo-breathe"
    assert rig.reg["lfo.1.sync"].value == 3     # lfo-breathe lands its bases: 1 bar
    assert lib.prev("bindings") == "legacy6"
    assert rig.view.pattern_mod[0] == 0.0       # legacy6 lands its bases
    frame(panel)
    # an edit dirties; save-as writes the routes to the user folder and cleans
    router.table.add(Binding("lane:2", "view.bright", "push", 0.3))
    assert lib.is_dirty("bindings")
    frame(panel)
    path = lib.save_as("bindings", "My Routes")
    assert path == tmp_path / "bindings" / "my-routes.json"
    doc = json.loads(path.read_text())
    assert doc["schema"] == routing.SCHEMA and len(doc["bindings"]) == 13
    assert doc["name"] == "My Routes"
    assert all(b["op"] in routing.MOD_OPS for b in doc["bindings"])
    assert lib.current("bindings") == "My Routes"
    assert not lib.is_dirty("bindings")
    assert lib.list("bindings") == [
        "default", "hands-fx", "hands-pinch", "hands-play", "legacy6", "lfo-breathe", "My Routes"]
    assert not lib.is_factory("bindings", "My Routes")
    frame(panel)
    # load a factory preset back: the user route goes, the inputs stay
    inputs = ("key", "pad", "hat", *routing.MIDI_SCHEMES)
    n_inputs = len(router.table.of(*inputs))
    lib.load("bindings", "default")
    assert not router.table.routes_to("view.bright")
    assert len(router.table.of(*inputs)) == n_inputs
    # and the user file round-trips
    lib.load("bindings", "My Routes")
    assert router.table.routes_to("view.bright")[0].value == 0.3
    frame(panel)
    # a bad name shows in the strip, never raises
    with pytest.raises(LibraryError):
        lib.load("bindings", "no-such")
    lib.error = "library: bindings: no preset 'no-such'"    # what the strip's guard records
    frame(panel)
    # the page's reset chip: the factory default
    lib.reset("bindings")
    assert lib.current("bindings") == "default" and not lib.is_dirty("bindings")


def test_routing_strip_name_field_draws(rig, tmp_path):

    panel = rig.panel
    router = _with_router(rig, tmp_path)
    frame(panel, "routing")
    ui_presets._begin_naming(panel, ui_routing.KEY, "seed")
    frame(panel)
    ui_presets._state(panel)["naming"] = None
    frame(panel)
    assert not panel.library.is_dirty("bindings") and router is panel.router


def test_router_preset_documents_and_a_library_over_them(tmp_path):
    """routing.py's side: `Router.apply_doc` / `preset_doc` / `signature`
    are the bindings kind's hooks; `Router.load_preset` is the same road
    through a Library over `home`, for tests and tools."""
    from test_routing import rig as routing_rig

    r = routing_rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings.factory())
    lib = Library(tmp_path)
    lib.routing(router)
    assert lib.list("bindings") == [
        "default", "hands-fx", "hands-pinch", "hands-play", "legacy6", "lfo-breathe"]
    assert lib.is_factory("bindings", "legacy6")
    router.table.add(Binding("lane:0", "view.bright", "push", 0.5, enabled=False))
    r.reg["macro.2"].set_value(0.3)                  # routing-layer state: saved with the routes
    path = lib.save_as("bindings", "Show A")
    assert path == tmp_path / "bindings" / "show-a.json"
    saved = Bindings.from_json(json.loads(path.read_text()))
    assert len(saved.bindings) == 13 and not saved.bindings[-1].enabled
    assert saved.values == {f"macro.{k}": (0.3 if k == 2 else 1.0) for k in range(1, 9)}
    assert router.load_preset("legacy6", tmp_path) == []
    assert len(router.table.routes()) == 12
    r.reg["macro.2"].set_value(0.9)
    assert router.load_preset("show-a", tmp_path) == []
    assert len(router.table.routes()) == 13 and r.reg["macro.2"].value == pytest.approx(0.3)
    assert router.signature() == [b.to_json() for b in router.table.routes()]
    with pytest.raises(LibraryError):
        router.load_preset("nope", tmp_path)
    assert imgui.get_version()
